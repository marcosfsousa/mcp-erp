"""The composition root — the only module importing all three layers.

Layers 1 and 3 reference each other nowhere. This file is what pairs them: it
gives layer 3's handler the store it needs, hands layer 1 a registration holding
layer 3's schemas and its ``Action``, and hangs the gate chain off the one route
that needs it.

This module sits at the package root rather than inside a sub-package so that
neither ``.importlinter`` contract needs an exception clause for it — it is out
of scope by construction rather than by a carve-out someone has to justify.

Ejecting layer 3 means deleting :mod:`mcp_erp.purchase_to_pay` and editing this
file. That is the whole procedure: remove the import, remove the store, remove
the one registration. Layer 1 then serves an empty tool set with an empty
``scopes_supported``, which is ADR-0012's own falsifier for the scope scheme
being a pattern rather than a naming convention.

**A factory rather than a module-level application.** ``create_app()`` is what
uvicorn runs, so importing this module reads no environment and opens no socket
— which is what keeps the *Every package imports* check in continuous
integration a statement about the package tree rather than about a machine's
environment.
"""

import contextlib
from collections.abc import AsyncIterator

import httpx2
from fastapi import FastAPI
from mcp.server.streamable_http_manager import (
    StreamableHTTPASGIApp,
    StreamableHTTPSessionManager,
)
from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool
from starlette.middleware import Middleware
from starlette.routing import Route

from mcp_erp import authorization, purchase_to_pay, transport
from mcp_erp.transport.keys import DEFAULT_TIMEOUT_SECONDS

__all__ = ["authorization", "create_app", "purchase_to_pay", "transport"]


def create_app(configuration: transport.Configuration | None = None) -> FastAPI:
    """Build the application: three layers wired, and the gate chain around one route.

    Args:
        configuration: The three strings the server runs on, read from the
            environment when absent. A parameter so that the composition root
            can be built without a process environment.

    Returns:
        The ASGI application uvicorn serves.
    """
    settings = configuration or transport.from_environment()

    # Both of these are created unopened and entered by the lifespan below.
    # Building the application therefore depends on neither the authorization
    # server nor the database being up: a Compose ordering accident fails a
    # request rather than a boot.
    outbound = httpx2.AsyncClient(timeout=DEFAULT_TIMEOUT_SECONDS)
    pool: AsyncConnectionPool[AsyncConnection[TupleRow]] = AsyncConnectionPool(
        settings.database_url, open=False
    )

    registry = transport.Registry(
        [
            transport.ToolRegistration(
                name=purchase_to_pay.requisition.NAME,
                title=purchase_to_pay.requisition.TITLE,
                description=purchase_to_pay.requisition.DESCRIPTION,
                input_schema=purchase_to_pay.requisition.INPUT_SCHEMA,
                output_schema=purchase_to_pay.requisition.OUTPUT_SCHEMA,
                action=purchase_to_pay.LIST_REQUISITIONS,
                handler=purchase_to_pay.handlers.list_requisitions(
                    purchase_to_pay.PostgresRequisitions(pool)
                ),
            )
        ]
    )

    sessions = StreamableHTTPSessionManager(
        app=transport.dispatch.build(registry),
        # Map constraint `#5`. The flag touches the **legacy leg alone** —
        # requests are routed on the version header before it is read — and it
        # gives legacy callers throwaway per-request sessions with no session
        # identifier issued and nothing remembered between requests. Two
        # replicas behind no sticky routing is what makes that falsifiable
        # rather than asserted.
        stateless=True,
        # **Every POST is answered `application/json`.** ADR-0002 took its own
        # option 5 and cut the SSE response mode, so this flag is not a
        # temporary setting standing in for a per-call decision — it is the
        # whole of the response-mode policy, and there is one wire shape to
        # have. The normative register's *No streamed response mode*
        # interpretation states the reading: the `MUST` naming both modes
        # binds a client's ability to read them, never a server's obligation
        # to produce one.
        #
        # It does not reach the legacy `GET` stream, which the package serves
        # from its own handler and which ADR-0009 authorises as inherited.
        json_response=True,
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Open what the request path needs, in the order it needs it.

        The session manager's own task group is the load-bearing one: a nested
        application's lifespan is never run by its parent, and there is no quiet
        degradation to catch later — every request answers ``500`` until it is
        wired (ADR-0013, executed at #32).
        """
        async with outbound, pool, sessions.run():
            yield

    application = FastAPI(
        lifespan=lifespan,
        # Every path other than the two below is a `404`, and these three are
        # why that sentence needs saying: FastAPI serves its own schema and two
        # documentation pages by default, unauthenticated. They would be the
        # only paths on this server answering a stranger with content, and the
        # metadata document is supposed to be the only one.
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
        routes=[
            # Outside the token gate **structurally**, as a sibling rather than
            # by a path allow-list on a gate. The preference is for an attack to
            # be impossible over defended-against.
            transport.metadata.route(settings, registry.scopes_supported),
            # `Route`, not `Mount`. Starlette compiles `Mount("/mcp", …)` to a
            # pattern that never matches the bare `/mcp` an MCP client posts to;
            # the router then falls through to its trailing-slash redirect and
            # answers `307` **without running a single route-level middleware**.
            # The gate chain is not bypassed — a redirect processes nothing —
            # but the endpoint is wrong and every call pays a round trip. #32
            # found that by execution.
            Route(
                settings.endpoint_path,
                # A non-function callable, deliberately: Starlette wraps an
                # `async def` endpoint as a request/response handler and calls
                # it with a `Request`, so a bare ASGI function would `500` here
                # where a class instance works.
                endpoint=StreamableHTTPASGIApp(sessions),
                # ADR-0006's chain, in its order. Read top to bottom: shape,
                # then token and the principal resolution behind it, then scope.
                middleware=[
                    Middleware(transport.ShapeGate),
                    Middleware(
                        transport.TokenGate,
                        key_set=transport.KeySet(settings.issuer, client=outbound),
                        directory=authorization.shipped_directory(),
                        audience=settings.resource,
                        metadata_url=settings.metadata_url,
                        scopes_supported=registry.scopes_supported,
                    ),
                    Middleware(
                        transport.ScopeGate,
                        registry=registry,
                        metadata_url=settings.metadata_url,
                    ),
                ],
            ),
        ],
    )

    # Gate 1, on every path — including the metadata document, which is exactly
    # as reachable from a browser as the tool endpoint is.
    application.add_middleware(transport.OriginGate)

    return application

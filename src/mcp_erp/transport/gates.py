"""The gate chain, as ASGI middleware, in the order that is itself the security property.

::

    1. Origin invalid                        -> 403                     every path
    2. required headers missing / mismatched -> 400 + -32020            the tool endpoint
    3. method is server/discover?            -> skip 4                  the tool endpoint
       (directory resolution)                                           the tool endpoint
    4. token absent or invalid               -> 401 + challenge         the tool endpoint
    5. scope insufficient                    -> 403 + insufficient_scope the tool endpoint
    6. domain rule                           -> -31010 or tool result   at dispatch

**Why the order and not the more literal reading.** The specification says
servers *"MUST validate access tokens before processing the request"*, which
reads as *token first*. Step 3's exemption cuts across it: something must
establish **which method this is** before the token check can decide whether to
run, and the method arrives in a caller-controlled header. Taken naively that is
an authentication bypass — send ``Mcp-Method: server/discover`` with
``tools/call`` in the body, and if the exemption is granted on the header before
header and body are compared, the token check never runs on a tool call. The fix
is ordering rather than a special case: prove header and body agree **first**,
and the attack becomes structurally impossible. The normative register's *Validate
before processing* interpretation records that reading, and
``auth_bypass_via_method_header_mismatch`` is its falsifier.

**Middleware rather than a dependency, and route-level rather than mount-level.**
Layer 1's substrate supplies its own ASGI application, and a mounted ASGI app is
not a route — dependency solving happens inside a route handler a mount never
enters. #32 executed both halves: a ``FastAPI(dependencies=[…])`` global fires
for an ``APIRoute`` and does not fire for a ``Route`` holding an ASGI app, and
the chain below runs in the order drawn.

**The unauthenticated endpoint sits outside this chain structurally**, as a
sibling route rather than by a path allow-list — the same preference for
impossible over defended-against.
"""

import json
from collections.abc import MutableMapping
from typing import Any, Final

from mcp.shared.inbound import (
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_PROTOCOL_VERSION_HEADER,
    NAME_BEARING_METHODS,
    decode_header_value,
)
from mcp_types.jsonrpc import HEADER_MISMATCH
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mcp_erp.authorization import DIRECTORY_MISS, PrincipalDirectory, permits_scope
from mcp_erp.transport import refusals
from mcp_erp.transport.keys import KeySet
from mcp_erp.transport.registry import Registry
from mcp_erp.transport.tokens import TokenRefusal, validate

DISCOVER_METHOD: Final = "server/discover"
"""The one method that answers strangers.

Answered without a token because **era detection happens before authorization**:
a modern client's path works by probing this method, and putting that probe
behind a ``401`` would rest the exhibit's third-party evidence on recovery
behaviour nobody has tested (ADR-0006).
"""

PROVEN_METHOD_STATE: Final = "mcp_proven_method"
"""The method gate 2 **proved**, which only the modern leg can have.

Gate 3 branches on this and on nothing else. A legacy request never sets it, so
the ``server/discover`` exemption is unavailable on that leg by construction
rather than by a rule — which is what ``legacy_discover_exemption_unavailable``
asserts.
"""

CALLED_TOOL_STATE: Final = "mcp_called_tool"
"""The tool name from the **body**, on either leg, for gate 5.

Read from the body rather than from the ``Mcp-Name`` header deliberately, and it
is not the same choice gate 3 makes. Dispatch acts on the body, so a gate that
authorized the header would authorize a different call from the one that runs —
the exact substitution ADR-0006's ordering exists to prevent, arriving through
the other door. On the modern leg gate 2 has already proved the two equal; on the
legacy leg there is no header to disagree with, and gate 5 still has to run
because ADR-0006's amendment says the legacy leg is carried by steps 4, 5 and 6.
"""

REQUEST_ID_STATE: Final = "mcp_request_id"
"""The body's JSON-RPC identifier, so a gate's error response can carry it."""

PRINCIPAL_STATE: Final = "principal"
"""Where the resolution step leaves the principal.

Read at dispatch as ``request.state.principal``.
"""

TOKEN_STATE: Final = "token"
"""The validated token, for the one thing dispatch needs that a principal does not carry."""

BEARER: Final = "bearer "


class OriginGate:
    """Gate 1, on every path: absent passes, present must prove itself.

    A browser attaches ``Origin`` to cross-origin requests automatically and a
    page cannot forge it; non-browser clients send none. The rebinding threat is
    specifically a malicious page in a victim's browser reaching a server on
    their machine — the case that *does* carry the header.

    So the allow-list **ships empty**, and the emptiness is the position rather
    than an unfinished configuration: every real client is unaffected and every
    browser-originated request gets a ``403``. ADR-0006 states the honest limit
    that follows — no client in this exhibit sends an ``Origin``, so only the
    negative scenario exercises this at all.
    """

    def __init__(self, app: ASGIApp, *, allowed_origins: frozenset[str] = frozenset()) -> None:
        """Wrap the application, with an allow-list that defaults to empty."""
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Refuse a request whose ``Origin`` is not on the allow-list."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = Headers(scope=scope).get("origin")
        if origin is not None and origin not in self.allowed_origins:
            await refusals.forbidden_origin()(scope, receive, send)
            return

        await self.app(scope, receive, send)


class ShapeGate:
    """Gate 2, and the reason gate 3 is safe: header and body must agree.

    **The comparison is a structural no-op on the legacy leg.** A legacy-era
    request carries none of the headers this gate compares — the protocol package
    routes on ``MCP-Protocol-Version`` before any handler, and an absent header
    routes as legacy — so there is nothing to compare and nothing is compared.
    That is ADR-0006's own amendment rather than a hole: the exemption gate 3
    grants is what step 2 protects, and the leg without the exemption does not
    need the protection.

    **Reading the body is not the comparison, and happens on both legs.** ADR-0006
    says the legacy leg is carried by steps 4, 5 and 6 — token, scope, domain —
    and step 5 needs to know which tool is being called. So the body is decoded
    either way and the tool name goes into request state; what the modern leg gets
    on top is a *proved* method, which is the only thing gate 3 will branch on.

    **The body is handed back, not consumed.** Reading it drains the ASGI
    ``receive`` channel and the mounted application drains it again, so this
    replaces the channel with one that replays the buffered body once and then
    **delegates to the original**. Returning ``http.disconnect`` after the body
    instead makes the application abandon its response mid-flight. #32 found
    that; it is a correctness constraint on this gate rather than a detail of it.
    """

    def __init__(self, app: ASGIApp) -> None:
        """Wrap the application."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Prove header and body agree, then hand both on."""
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        body, replay = await _buffer(receive)
        state = _state(scope)

        document = _decode(body)
        if document is None:
            # Unparseable, so there is no method to prove and no exemption to
            # grant. The token gate runs, and the application answers the parse
            # error afterwards — which is the order this chain exists for.
            await self.app(scope, replay, send)
            return

        state[REQUEST_ID_STATE] = document.get("id")
        method = document.get("method")
        state[CALLED_TOOL_STATE] = _called_tool(document)

        # The legacy leg stops here: nothing above compared a header, and there
        # is no header below to compare.
        if headers.get(MCP_PROTOCOL_VERSION_HEADER) is None:
            await self.app(scope, replay, send)
            return

        if headers.get(MCP_METHOD_HEADER) != method:
            await self._reject(
                f"{MCP_METHOD_HEADER} header does not match the request body's method",
                scope,
                replay,
                send,
            )
            return

        name_key = NAME_BEARING_METHODS.get(method) if isinstance(method, str) else None
        if name_key is not None:
            parameters = document.get("params")
            named = parameters.get(name_key) if isinstance(parameters, dict) else None
            if named is not None and decode_header_value(headers.get(MCP_NAME_HEADER)) != named:
                await self._reject(
                    f"{MCP_NAME_HEADER} header does not match the request body's "
                    f"{name_key!r} parameter",
                    scope,
                    replay,
                    send,
                )
                return

        state[PROVEN_METHOD_STATE] = method
        await self.app(scope, replay, send)

    async def _reject(self, message: str, scope: Scope, receive: Receive, send: Send) -> None:
        """``400`` and a ``HeaderMismatch`` JSON-RPC error, which the clause requires as a pair."""
        response = refusals.protocol_error(
            HEADER_MISMATCH,
            message,
            request_id=_state(scope).get(REQUEST_ID_STATE),
            status=400,
        )
        await response(scope, receive, send)


class TokenGate:
    """Gates 3 and 4, and the resolution step between 4 and 5.

    Lookup runs here rather than at dispatch because it is conditional on nothing
    dispatch knows, and because ``tools/list`` and ``tools/call`` share one scope
    check precisely so that one rule has one implementation — resolving at
    dispatch would give it two (ADR-0006).

    **A directory miss is an explicit refusal, not an empty principal.** A
    principal with no roles would clear the scope gate and then clear a role
    check demanding nothing, so an unknown subject holding ``erp.write`` would
    write a row charged to a null partition. The refusal reuses ``role_missing``,
    whose record it shares exactly.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        key_set: KeySet,
        directory: PrincipalDirectory,
        audience: str,
        metadata_url: str,
        scopes_supported: tuple[str, ...],
    ) -> None:
        """Wrap the application with everything a token check needs and nothing more."""
        self.app = app
        self.key_set = key_set
        self.directory = directory
        self.audience = audience
        self.metadata_url = metadata_url
        self.scopes_supported = scopes_supported

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Validate the token, resolve the principal, or refuse."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = _state(scope)
        # Gate 3. It branches on the method gate 2 **proved**, never on the one
        # the body merely claims: a legacy request sets no proven method, so the
        # exemption is unavailable on that leg by construction.
        if state.get(PROVEN_METHOD_STATE) == DISCOVER_METHOD:
            await self.app(scope, receive, send)
            return

        presented = _bearer(Headers(scope=scope).get("authorization"))
        if presented is None:
            # RFC 6750: no credentials at all is not an error. Nothing is wrong
            # with the token; there simply is not one.
            response = refusals.missing_credentials(
                metadata_url=self.metadata_url, scopes=self.scopes_supported
            )
            await response(scope, receive, send)
            return

        try:
            token = await validate(
                presented,
                key_set=self.key_set,
                issuer=self.key_set.issuer,
                audience=self.audience,
            )
        except TokenRefusal as refusal:
            response = refusals.rejected_credentials(
                refusal.description, metadata_url=self.metadata_url
            )
            await response(scope, receive, send)
            return

        principal = self.directory.lookup(token.claims)
        if principal is None:
            await refusals.protocol_error(
                refusals.ROLE_DENIED_CODE,
                DIRECTORY_MISS.value,
                request_id=state.get(REQUEST_ID_STATE),
                data=refusals.refusal_payload(DIRECTORY_MISS),
            )(scope, receive, send)
            return

        state[PRINCIPAL_STATE] = principal
        state[TOKEN_STATE] = token
        await self.app(scope, receive, send)


class ScopeGate:
    """Gate 5: the token does not carry what the called tool requires.

    **In middleware rather than at dispatch, and the reason is the wire shape.**
    ADR-0013 placed gates 5 and 6 at dispatch *"where the Action is known"*. The
    Action is known here too — gate 2 recorded the tool name and layer 1 holds
    the registry — and the refusal ADR-0002 specifies is an HTTP ``403`` carrying
    a ``WWW-Authenticate`` challenge, which nothing inside a JSON-RPC dispatch
    can produce: by then the response is a JSON-RPC envelope at ``200``. Gate 6
    stays at dispatch, where both of its shapes fit inside that envelope.
    Recorded as an amendment to ADR-0013 by #37.

    **It runs on both legs**, which is why the tool name comes from the body
    rather than from the ``Mcp-Name`` header: ADR-0006's amendment says the
    legacy leg is carried by steps 4, 5 and 6, and a legacy request has no header
    to read. Reading the body is also the sounder choice on the modern leg, where
    the two are equal by then — dispatch acts on the body, so a gate that
    authorized the header would be authorizing a different call from the one that
    runs.

    The scope rule still has **one implementation**: this gate and the handler's
    ``decide_call`` both call
    :func:`~mcp_erp.authorization.policy.permits_scope`, which is the same
    deliberate N+1 the chain already pays inside a batch.

    A tool name nothing is registered under is left alone. Dispatch owns *no
    such tool*, and answering it here would make an unknown name and an
    unpermitted one distinguishable in the wrong direction.
    """

    def __init__(self, app: ASGIApp, *, registry: Registry, metadata_url: str) -> None:
        """Wrap the application with the registry the tool name is resolved against."""
        self.app = app
        self.registry = registry
        self.metadata_url = metadata_url

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Refuse a call whose token does not carry the tool's scope."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        state = _state(scope)
        called = state.get(CALLED_TOOL_STATE)
        registration = self.registry.get(called) if isinstance(called, str) else None
        principal = state.get(PRINCIPAL_STATE)

        if (
            registration is not None
            and principal is not None
            and not permits_scope(principal, registration.action)
        ):
            response = refusals.insufficient_scope(
                registration.action.scope,
                tool=registration.name,
                metadata_url=self.metadata_url,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def _called_tool(document: dict[str, Any]) -> str | None:
    """The tool name a body calls, or ``None`` if the body calls no tool.

    Reads ``params.name`` for ``tools/call`` and nothing else. The key comes from
    the protocol package's own map of name-bearing methods, so a revision that
    renamed it would not leave this silently reading a key that no longer exists.
    """
    if document.get("method") != "tools/call":
        return None
    parameters = document.get("params")
    if not isinstance(parameters, dict):
        return None
    name = parameters.get(NAME_BEARING_METHODS["tools/call"])
    return name if isinstance(name, str) else None


async def _buffer(receive: Receive) -> tuple[bytes, Receive]:
    """Drain the request body and return it with a channel that replays it once.

    The replacement yields the buffered body and then **delegates** to the
    original channel, so the application sees the disconnect and any later
    messages exactly as it would have.
    """
    chunks: list[bytes] = []
    more = True
    while more:
        message = await receive()
        if message["type"] != "http.request":
            more = False
            continue
        chunks.append(message.get("body", b""))
        more = bool(message.get("more_body", False))
    body = b"".join(chunks)
    replayed = False

    async def replay() -> Message:
        nonlocal replayed
        if not replayed:
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await receive()

    return body, replay


def _decode(body: bytes) -> dict[str, Any] | None:
    """The request body as a JSON object, or ``None`` if it is not one."""
    try:
        document = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return document if isinstance(document, dict) else None


def _state(scope: Scope) -> MutableMapping[str, Any]:
    """The per-request state mapping, created if the server did not supply one."""
    state = scope.get("state")
    if state is None:
        state = {}
        scope["state"] = state
    return state


def _bearer(header: str | None) -> str | None:
    """The credential from an ``Authorization`` header, or ``None``.

    **Header only.** ADR-0006 publishes ``bearer_methods_supported: ["header"]``,
    which turns *a token in the query string is not honoured* from a behaviour we
    happen to exhibit into a contract we then keep — so there is deliberately no
    fallback to a query parameter here to delete.
    """
    if header is None or not header.lower().startswith(BEARER):
        return None
    credential = header[len(BEARER) :].strip()
    return credential or None

"""The conformance client's Docker-free half — which wait bounds which request.

`tests/conformance/` proves the flow by performing it, and needs Keycloak, this
server and GitHub Pages to say anything at all. This file proves the one thing
that suite cannot: that the read wait is lifted off a long-lived `GET` stream
and left on everything else.

**A run cannot say it in either direction.** `conformance_client.TIMEOUT` records
why no stream is opened against this server at all; and even against one that
opened a stream, a read timeout closing a quiet stream is answered by the
protocol package's own reconnect loop and the flow still completes. So
[#86](https://github.com/marcosfsousa/mcp-erp/issues/86) is a rule to assert
directly or not at all.

**The assertions are made against a socket, not against the server.** The fake
below answers every request with event-stream headers and then says nothing,
which is a stream that is *healthy and quiet* — the one case a read wait cannot
tell from a stuck one. The client is the one :func:`conformance_client.connect`
builds, with a small `timeout` in place of the module's, so the difference shows
in two seconds rather than in thirty.

Docker-free like `tests/test_tokens.py`, and carried by the same `Lint and
types` job for the same reason: a wait applied to the wrong request is an
ordinary Python defect, and a suite that needs Compose to notice one would
report it as the authorization server being slow.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Final

import httpx2
from mcp.shared.inbound import MCP_PROTOCOL_VERSION_HEADER
from mcp_types.version import LATEST_PROTOCOL_VERSION

from conformance_client import Bearer, protocol_client

WAIT: Final = 0.5
"""The whole-request wait these tests bound everything with.

`conformance_client.TIMEOUT` in miniature, and small for the reason that
constant is large: what is being asserted is *which requests this number
reaches*, and asserting it at thirty seconds would cost thirty seconds.
"""

BUDGET: Final = 2.0
"""How long a stream is watched before it counts as having outlived :data:`WAIT`.

Four times the wait, so *the read timeout did not fire* is a measurement rather
than a race with it.
"""

QUIET: Final = 30.0
"""How long the fake holds a stream open without sending anything.

Longer than :data:`BUDGET` by enough that the server is never the thing that
ends a test — every outcome below is the client's timeout firing or not firing.
"""

AS_THE_PACKAGE_ASKS: Final = {"accept": "application/json, text/event-stream"}
"""The `accept` `streamable_http` puts on every request it makes, verbatim.

Copied from `StreamableHTTPTransport._prepare_headers` rather than narrowed to
`text/event-stream`, because it is the header the rule is actually read against
and it is **the same on the `POST`s as on the stream**. A test that sent a
tidier one would be proving a rule this client does not have.
"""

AS_DISCOVERY_ASKS: Final = {MCP_PROTOCOL_VERSION_HEADER: LATEST_PROTOCOL_VERSION}
"""What a metadata `GET` carries, which is a protocol version and no `accept`.

`mcp.client.auth.utils` builds every discovery request as exactly this header
and nothing else, so it is read from the package rather than written out here —
a literal would be a second copy of an era, and this file's whole subject is
which era is being spoken. It is the other `GET` on this client, and the one
that must keep its read wait.
"""

TOKEN: Final = Bearer("not a token, and never presented to anything that reads one")
"""Any `httpx2.Auth`, because the client takes one and none of this is about which."""


async def _quiet_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Answer any request with an open event stream, and then say nothing at all.

    Headers only, then silence. Chunked rather than a length, so the body is
    genuinely unfinished and a client waiting on it is waiting on a read.
    """
    await reader.readuntil(b"\r\n\r\n")
    writer.write(
        b"HTTP/1.1 200 OK\r\ncontent-type: text/event-stream\r\ntransfer-encoding: chunked\r\n\r\n"
    )
    await writer.drain()
    await asyncio.sleep(QUIET)


@asynccontextmanager
async def _serving() -> AsyncIterator[str]:
    """A loopback address that answers as :func:`_quiet_stream`, on a port the kernel picks.

    Closed rather than shut down. `Server.__aexit__` waits for its handlers, and
    these handlers are asleep for :data:`QUIET` by design — waiting for one would
    make every test here take that long to tear down. `asyncio.run` cancels
    what is left when the loop closes, which is the right end for a connection
    whose whole purpose was to stay open.
    """
    server = await asyncio.start_server(_quiet_stream, "127.0.0.1", 0)
    try:
        host, port = server.sockets[0].getsockname()[:2]
        yield f"http://{host}:{port}/mcp"
    finally:
        server.close()


def test_a_stream_that_is_merely_quiet_is_not_closed_by_the_request_wait() -> None:
    """#86's acceptance criterion, as the only assertion that can fail on it.

    A `GET` the protocol package opens for server-initiated messages is healthy
    and idle for as long as the server has nothing to say, and *idle* is the one
    state `conformance_client.TIMEOUT`'s argument excludes. Run against this
    module before :class:`conformance_client.Unhurried`, the socket below closes
    at :data:`WAIT` and this reads `closed`.
    """

    async def watch() -> str:
        async with _serving() as url, protocol_client(TOKEN, timeout=WAIT) as http:
            try:
                async with http.sse(url, headers=AS_THE_PACKAGE_ASKS) as events:
                    async with asyncio.timeout(BUDGET):
                        async for _ in events:
                            pass
            except httpx2.ReadTimeout:
                return "closed"
            except TimeoutError:
                return "still open"

        return "the server ended it"

    assert asyncio.run(watch()) == "still open"


async def _sending(
    method: str, headers: Mapping[str, str], json: Mapping[str, str] | None = None
) -> str:
    """Whether the read wait still ends one request the fake will never answer.

    The two assertions below differ by a request line and a set of headers and
    by nothing else, which is what the rule they check is about: it reads the
    request rather than the address, so what a test has to vary is exactly what
    it declares.
    """
    async with _serving() as url, protocol_client(TOKEN, timeout=WAIT) as http:
        try:
            await http.request(method, url, headers=headers, json=json)
        except httpx2.ReadTimeout:
            return "bounded"

    return "unbounded"


def test_a_post_keeps_the_read_wait_a_tool_call_needs() -> None:
    """The other half, and the reason the rule is not a second number on the client.

    A `tools/call` is a `POST` through this same client, carrying this same
    `accept` — the package will read an event stream back from it — and it is
    one of the things `conformance_client.TIMEOUT` exists to bound. A read wait
    lifted client-wide would take this with it, and a server that stopped
    answering mid-call would hang the run instead of failing it.
    """
    assert asyncio.run(_sending("POST", AS_THE_PACKAGE_ASKS, {"jsonrpc": "2.0"})) == "bounded"


def test_a_discovery_get_keeps_the_read_wait_it_had() -> None:
    """The rule is about a stream, not about a method.

    Discovery is the other `GET` on this client — protected resource metadata,
    then the authorization server's — and it fetches a document rather than
    opening a stream. It is told apart by what it declares it will read, so a
    rule that had keyed on `GET` alone would have left the whole discovery chain
    unbounded and this is what says so. It is driven through the client here;
    :func:`test_a_request_the_auth_flow_yields_is_bounded_too` is what says the
    same of the copy the package actually sends.
    """
    assert asyncio.run(_sending("GET", AS_DISCOVERY_ASKS)) == "bounded"


class _Yielding(httpx2.Auth):
    """An `httpx2.Auth` that yields a request it built itself, as the package's does.

    `mcp.client.auth.utils` constructs each discovery `GET` and the registration
    `POST` with a bare `httpx2.Request`, and `oauth2.py` builds the token form
    post the same way. Reproduced here rather than driven through the real
    provider, because what the rule turns on is only that the request was
    *yielded* — it never passes `AsyncClient.send`, so it never receives the
    client's waits, and the shape of its body has nothing to do with it.
    """

    def __init__(self, method: str, headers: Mapping[str, str]) -> None:
        """Keep what the yielded request will declare.

        Args:
            method: The request line the auth flow will produce.
            headers: What that request declares it will read.
        """
        self._method = method
        self._headers = headers

    async def async_auth_flow(
        self, request: httpx2.Request
    ) -> AsyncGenerator[httpx2.Request, httpx2.Response]:
        """Yield one request of this flow's own making, to the address under test."""
        yield httpx2.Request(self._method, request.url, headers=self._headers)


async def _yielding(method: str, headers: Mapping[str, str]) -> str:
    """Whether a request the auth flow yields is bounded, rather than one the client built.

    Watched under :data:`BUDGET` rather than left to run out, because a request
    with no waits does not fail — it waits for the fake, and the failure that
    eventually arrives is the fake closing at :data:`QUIET`, thirty seconds later
    and under a name that says nothing about a timeout. The guard is what turns
    *this never came back* into an answer this function can return.
    """
    async with (
        _serving() as url,
        protocol_client(_Yielding(method, headers), timeout=WAIT) as http,
    ):
        try:
            async with asyncio.timeout(BUDGET):
                await http.post(url, json={"jsonrpc": "2.0"})
        except httpx2.ReadTimeout:
            return "bounded"
        except TimeoutError:
            return "unbounded"

    return "the server answered"


def test_a_request_the_auth_flow_yields_is_bounded_too() -> None:
    """The waits reach every request, not only the ones the client resolved them for.

    `AsyncClient.send` stamps the client's timeout onto the request it is handed
    and onto no other, and `_send_handling_auth` passes what the auth flow yields
    straight to the transport. So the token form post and the discovery chain
    ahead of it arrive carrying no waits, which `httpcore` reads as no wait on
    anything — the one shape `conformance_client.TIMEOUT` named and did not
    reach. Run against this module before `Unhurried` supplied the waits itself,
    both assertions below read `unbounded`.
    """
    assert asyncio.run(_yielding("POST", {})) == "bounded"
    assert asyncio.run(_yielding("GET", AS_DISCOVERY_ASKS)) == "bounded"

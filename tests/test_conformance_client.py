"""The conformance client's Docker-free half — which wait bounds which request.

`tests/conformance/` proves the flow by performing it, and needs Keycloak, this
server and GitHub Pages to say anything at all. This file proves the one thing
that suite cannot: that the read wait is lifted off a long-lived `GET` stream
and left on everything else.

**A run cannot say it in either direction.** This server negotiates the era that
opens no server-initiated stream — `server/discover`, and no session identifier
on any response — so the flow reaches the exempt wait exactly never, and reached
it exactly never before the fix either. Even against a server that did open one,
the read timeout closing a quiet stream is answered by the package's own
reconnect loop and the run still passes.
[#86](https://github.com/marcosfsousa/mcp-erp/issues/86) is therefore a rule to
assert directly or not at all.

**The assertions are made against a socket, not against the server.** The fake
below answers every request with event-stream headers and then says nothing,
which is a stream that is *healthy and quiet* — the one case a read wait cannot
tell from a stuck one. The client is the one :func:`connect` builds, with a
small `timeout` in place of the module's, so the difference shows in two seconds
rather than in thirty.

Docker-free like `tests/test_tokens.py`, and carried by the same job step for
the same reason: a wait applied to the wrong request is an ordinary Python
defect, and a suite that needs Compose to notice one would report it as the
authorization server being slow.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

import httpx2

from conformance_client import Bearer, _protocol_client

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

AS_DISCOVERY_ASKS: Final = {"mcp-protocol-version": "2025-06-18"}
"""What a metadata `GET` carries, which is a protocol version and no `accept`.

`mcp.client.auth.utils` builds every discovery request this way. It is the other
`GET` on this client, and the one that must keep its read wait.
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
        async with _serving() as url, _protocol_client(TOKEN, timeout=WAIT) as http:
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


def test_a_post_keeps_the_read_wait_a_tool_call_needs() -> None:
    """The other half, and the reason the rule is not a second number on the client.

    A `tools/call` is a `POST` through this same client, carrying this same
    `accept` — the package will read an event stream back from it — and it is
    one of the things `conformance_client.TIMEOUT` exists to bound. A read wait
    lifted client-wide would take this with it, and a server that stopped
    answering mid-call would hang the run instead of failing it.
    """

    async def call() -> str:
        async with _serving() as url, _protocol_client(TOKEN, timeout=WAIT) as http:
            try:
                await http.post(url, json={"jsonrpc": "2.0"}, headers=AS_THE_PACKAGE_ASKS)
            except httpx2.ReadTimeout:
                return "bounded"

        return "unbounded"

    assert asyncio.run(call()) == "bounded"


def test_a_discovery_get_keeps_the_read_wait_it_had() -> None:
    """The rule is about a stream, not about a method.

    Discovery is the other `GET` on this client — protected resource metadata,
    then the authorization server's — and it fetches a document rather than
    opening a stream. It is told apart by what it declares it will read, so a
    rule that had keyed on `GET` alone would have left the whole discovery chain
    unbounded and this is what says so.
    """

    async def discover() -> str:
        async with _serving() as url, _protocol_client(TOKEN, timeout=WAIT) as http:
            try:
                await http.get(url, headers=AS_DISCOVERY_ASKS)
            except httpx2.ReadTimeout:
                return "bounded"

        return "unbounded"

    assert asyncio.run(discover()) == "bounded"

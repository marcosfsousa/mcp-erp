"""One request over Streamable HTTP, for every suite that drives the wire.

The second piece of shared tooling above the four test directories, beside
`tokens.py` and for the same reason: ADR-0008 puts **every** decision-matrix row
and **every** attack scenario on real HTTP, so the thing that builds a request is
the piece most likely to become slow and duplicated if it grows organically.

**Hand-built envelopes, not the protocol package's client, and that is on
purpose here.** The suites that use this assert on **status codes and response
headers** — `401` versus `403`, the `WWW-Authenticate` parameters, `ttlMs` and
`cacheScope` — and a client library's job is to hide exactly those. The real
client is the conformance client's leg (#46), which earns its token through a
hosted identity document and asserts that the protocol works end to end; this
asserts what the server said.

Nothing protocol-shaped is hand-written even so. The header names, the envelope
keys, the supported revision and the base64 sentinel codec all come from the
package, so a suite cannot pass against a spelling the server does not use.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, Final

import httpx2
from mcp.shared.inbound import (
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_PROTOCOL_VERSION_HEADER,
    NAME_BEARING_METHODS,
    encode_header_value,
)
from mcp_types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
)
from mcp_types.version import LATEST_PROTOCOL_VERSION

BASE_URL = os.environ.get("MCP_ERP_BASE_URL", "http://localhost:8080").rstrip("/")
"""Where the requests go: the gateway's published address.

The gateway is the only way in, deliberately — neither replica publishes a port,
so a suite cannot pin itself to one of them and then report a statelessness
result that was never tested.
"""

RESOURCE = os.environ.get("MCP_ERP_RESOURCE_URL", "http://localhost:8080/mcp")
"""What the server calls itself, and what every token's audience must name.

Separate from :data:`BASE_URL` on the same terms the token helper separates the
issuer from the address it talks to: **identity is the resource identifier;
:data:`BASE_URL` is transport.** Under Compose they are the same string, and
they stop being the same the moment a reader puts the gateway somewhere else.
"""

ENDPOINT: Final = "/mcp"
"""The tool endpoint's path, which is the resource identifier's path."""

METADATA_PATH: Final = "/.well-known/oauth-protected-resource/mcp"
"""Path-inserted, per RFC 9728 §3.1 — the segment goes between host and path."""

METADATA_URL = f"{RESOURCE.rsplit('/', 1)[0]}{METADATA_PATH}"
"""The absolute address every challenge names, derived from the resource identifier."""

SERVED_BY_HEADER: Final = "x-served-by"
"""Which replica answered, as the **gateway** reports it.

Not something the resource server says about itself: it has no idea it is one of
two, which is the property under test.
"""

CLIENT_INFO: Final = {"name": "mcp-erp-suite", "version": "0"}
"""Optional by the specification and sent anyway, because a real client sends it."""

TIMEOUT: Final = 30.0


def envelope(
    method: str, params: Mapping[str, Any] | None = None, *, request_id: int = 1
) -> dict[str, Any]:
    """A modern-era JSON-RPC request, with the per-request metadata in ``params._meta``.

    The envelope keys are the package's own constants. There is no handshake to
    perform first: the `2026-07-28` revision removed connection initialization
    entirely, and every request carries the metadata a handshake used to
    establish — which is the whole reason a stateless server is expressible.
    """
    body_params = dict(params or {})
    body_params["_meta"] = {
        PROTOCOL_VERSION_META_KEY: LATEST_PROTOCOL_VERSION,
        CLIENT_CAPABILITIES_META_KEY: {},
        CLIENT_INFO_META_KEY: CLIENT_INFO,
    }
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": body_params}


def routing_headers(
    method: str, params: Mapping[str, Any] | None = None, *, token: str | None = None
) -> dict[str, str]:
    """The headers a modern request carries, derived from the body it will send.

    Derived rather than passed, so a suite that is not *about* header agreement
    cannot accidentally send a mismatched pair and blame the server. The suites
    that are about it build the disagreement explicitly.
    """
    headers = {
        "content-type": "application/json",
        # Both, although this server answers only the first. The `MUST` that
        # names the two response modes binds a **client's** ability to read
        # them — "the client MUST support both" — and a suite that stopped
        # sending `text/event-stream` would stop being a faithful client.
        # The register's *No streamed response mode* interpretation carries
        # the reading.
        "accept": "application/json, text/event-stream",
        MCP_PROTOCOL_VERSION_HEADER: LATEST_PROTOCOL_VERSION,
        MCP_METHOD_HEADER: method,
    }

    name_key = NAME_BEARING_METHODS.get(method)
    if name_key is not None and params is not None and name_key in params:
        headers[MCP_NAME_HEADER] = encode_header_value(str(params[name_key]))

    if token is not None:
        headers["authorization"] = f"Bearer {token}"

    return headers


def get(path: str) -> httpx2.Response:
    """One plain GET against the server, for the routes that are not the tool endpoint.

    Here rather than in each suite for the reason this module exists at all: the
    base address, the timeout and the decision not to raise on a `4xx` are one
    set of choices, and four copies of a client constructor is four places for
    them to come apart.
    """
    with httpx2.Client(base_url=BASE_URL, timeout=TIMEOUT) as http:
        return http.get(path)


def post(
    method: str,
    params: Mapping[str, Any] | None = None,
    *,
    token: str | None = None,
    base_url: str | None = None,
    request_id: int = 1,
) -> httpx2.Response:
    """Send one request and return the response, whatever it is.

    Deliberately not raising on a `4xx`: a refusal is the subject of half the
    suites that call this, and a helper that raised would make them assert
    against an exception rather than against the wire.
    """
    with httpx2.Client(base_url=base_url or BASE_URL, timeout=TIMEOUT) as http:
        return http.post(
            ENDPOINT,
            headers=routing_headers(method, params, token=token),
            json=envelope(method, params, request_id=request_id),
        )


def result(response: httpx2.Response) -> dict[str, Any]:
    """The ``result`` object of a successful JSON-RPC response.

    Raises:
        AssertionError: The response is not a `200`, or carries an ``error``.
            An assertion rather than an exception type of its own, because every
            caller is a test and the failure message wants the body in it.
    """
    assert response.status_code == httpx2.codes.OK, f"{response.status_code}: {response.text}"
    document: dict[str, Any] = response.json()
    assert "error" not in document, document["error"]
    payload: dict[str, Any] = document["result"]
    return payload


def error(response: httpx2.Response) -> dict[str, Any]:
    """The ``error`` object of a JSON-RPC error response.

    Raises:
        AssertionError: The response carries a result instead.
    """
    document: dict[str, Any] = response.json()
    assert "error" in document, document
    payload: dict[str, Any] = document["error"]
    return payload


def call_tool(
    name: str, arguments: Mapping[str, Any] | None = None, *, token: str
) -> httpx2.Response:
    """One ``tools/call``, with the ``Mcp-Name`` header the body implies."""
    return post("tools/call", {"name": name, "arguments": dict(arguments or {})}, token=token)


def challenge(response: httpx2.Response) -> dict[str, str]:
    """The ``WWW-Authenticate`` parameters, parsed into a mapping.

    Parsed rather than string-matched so that a suite asserts on *which*
    parameters are present, which is what ADR-0002 specified — a substring check
    would pass on a header that carried the right words in the wrong roles.

    Raises:
        AssertionError: The response carries no challenge.
    """
    header = response.headers.get("www-authenticate")
    assert header is not None, f"no challenge on {response.status_code}: {response.text}"
    assert header.startswith("Bearer "), header

    parameters: dict[str, str] = {}
    for pair in _split(header[len("Bearer ") :]):
        name, _, value = pair.partition("=")
        parameters[name.strip()] = value.strip().strip('"')
    return parameters


def _split(parameters: str) -> list[str]:
    """Split ``auth-param`` pairs on commas that are not inside a quoted string.

    ``scope`` is space-delimited and ``error_description`` is prose, so both can
    carry a comma. Splitting naively works today and would fail on the first
    description that needed one, silently, by producing a parameter nobody set.
    """
    pairs: list[str] = []
    current: list[str] = []
    quoted = False
    for character in parameters:
        if character == '"':
            quoted = not quoted
        if character == "," and not quoted:
            pairs.append("".join(current))
            current = []
            continue
        current.append(character)
    if current:
        pairs.append("".join(current))
    return pairs

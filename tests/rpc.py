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

TRANSPORT_HEADERS: Final = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
}
"""What a request carries in either era, because both of these are HTTP rather than protocol.

``Accept`` names both response modes although this server answers only the first.
The `MUST` that names the two binds a **client's** ability to read them — *"the
client MUST support both"* — and a suite that stopped sending
``text/event-stream`` would stop being a faithful client. The register's *No
streamed response mode* interpretation carries the reading.

One definition rather than one per shape: the two shapes differ by what the
modern era **added**, and a constant that both start from is what keeps that the
only difference between them.
"""

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
        **TRANSPORT_HEADERS,
        MCP_PROTOCOL_VERSION_HEADER: LATEST_PROTOCOL_VERSION,
        MCP_METHOD_HEADER: method,
    }

    name_key = NAME_BEARING_METHODS.get(method)
    if name_key is not None and params is not None and name_key in params:
        headers[MCP_NAME_HEADER] = encode_header_value(str(params[name_key]))

    return _credentialed(headers, token)


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
    return send(
        routing_headers(method, params, token=token),
        envelope(method, params, request_id=request_id),
        base_url=base_url,
    )


def legacy_post(
    method: str,
    params: Mapping[str, Any] | None = None,
    *,
    token: str | None = None,
    headers: Mapping[str, str] | None = None,
    request_id: int = 1,
) -> httpx2.Response:
    """The **second request shape**: a legacy-era call, which is a call with no envelope.

    ADR-0009's cost line names this — *"a second request shape in the suites that
    exists only to be refused"* — and it is here rather than in the one suite that
    uses it for the reason this module exists: what a request on the wire looks
    like is one set of decisions, and the legacy shape is decided by subtraction
    from the modern one.

    **Everything the modern era added is absent, and the absence is the whole
    definition.** No ``MCP-Protocol-Version``, no ``Mcp-Method``, no ``Mcp-Name``,
    and no ``params._meta``: the handshake era establishes once, at
    ``initialize``, what the `2026-07-28` revision carries per request. Era
    routing keys on the version header alone and an absent one routes as legacy,
    so what makes this a legacy request is precisely what it does not send.

    :data:`TRANSPORT_HEADERS` stays, because both of those are HTTP rather than era.

    Args:
        method: The JSON-RPC method, sent in the body and nowhere else.
        params: The method's parameters, verbatim — no envelope is merged in.
        token: A bearer credential, when the request is meant to carry one.
        headers: Extra headers, merged last, so a caller can add a header this
            shape defines itself by omitting. That is the parameter's only
            purpose and the seam assertions are its only callers: they send
            ``Mcp-Method`` on a leg that can prove nothing with it, which is how
            they show the ``server/discover`` exemption follows from absence
            rather than from a default.
        request_id: The JSON-RPC identifier.
    """
    sent = _credentialed(dict(TRANSPORT_HEADERS), token)
    sent.update(headers or {})

    return send(
        sent,
        {"jsonrpc": "2.0", "id": request_id, "method": method, "params": dict(params or {})},
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


def send(
    headers: Mapping[str, str], body: Mapping[str, Any], *, base_url: str | None = None
) -> httpx2.Response:
    """One POST to the tool endpoint, and the only place any shape builds a client.

    The two shapes differ in what they send and in nothing else. Keeping the
    address, the timeout and the decision not to raise on a `4xx` in one function
    is what makes that true rather than merely intended — the same argument
    :func:`get` states, applied to the second shape that arrived after it.

    **Public since #44, for the suite this module's own docstring anticipated:**
    *"the suites that are about it build the disagreement explicitly."* A row
    asserting that a header and a body must agree cannot use :func:`post`, which
    derives one from the other precisely so that no suite sends a mismatched pair
    by accident. What it needs is this — the headers it wrote, the body it wrote,
    and the same client every other request is made with.

    Args:
        headers: Exactly what to send, including any credential.
        body: The request body, sent as JSON.
        base_url: Somewhere other than the gateway, for the one suite that
            addresses a replica by name.

    Returns:
        The response, whatever it is.
    """
    with httpx2.Client(base_url=base_url or BASE_URL, timeout=TIMEOUT) as http:
        return http.post(ENDPOINT, headers=dict(headers), json=dict(body))


def _credentialed(headers: dict[str, str], token: str | None) -> dict[str, str]:
    """The headers with a bearer credential added, when there is one to add.

    Both shapes present a token the same way, because the token is the seam and
    the seam is era-independent — which is the property the legacy rows assert.
    Two spellings of this would be two ways for that to stop being true.
    """
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    return headers


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

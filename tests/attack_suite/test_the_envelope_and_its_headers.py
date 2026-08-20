"""Gate 2 and the rungs behind it: what a modern request must say about itself.

Five scenarios — `header_body_mismatch`, `missing_required_header`,
`protocol_version_skew`, `malformed_meta` and `unsupported_protocol_version` —
and they belong together because they are one question asked five ways: **does
this request agree with itself, and does it name a revision this server
implements?**

**The disagreements are built by hand, which is what `rpc.send` exists for.**
`rpc.post` derives the headers from the body precisely so that a suite which is
not about header agreement cannot send a mismatched pair and blame the server.
These suites are about it, so they write both halves.

**Two refusals from two places, and the difference is worth seeing.** ADR-0006's
gate 2 compares the method and name headers against the body **before** the token
gate runs, so a mismatch is refused with no credential involved at all. The
envelope rungs — `params._meta`, and the revision the envelope names — sit inside
the protocol package, past the gate chain, and so are reachable only with a
token. Both answer `400` with a JSON-RPC error, which is the pair the clause
requires; which of the two answered is visible in whether a token was needed to
get there, and every test below says which it is asserting.
"""

import base64
from typing import Any

import httpx2
from mcp.shared.inbound import (
    MCP_METHOD_HEADER,
    MCP_NAME_HEADER,
    MCP_PROTOCOL_VERSION_HEADER,
    encode_header_value,
)
from mcp_types import PROTOCOL_VERSION_META_KEY
from mcp_types.jsonrpc import HEADER_MISMATCH, INVALID_PARAMS, UNSUPPORTED_PROTOCOL_VERSION
from mcp_types.version import LATEST_PROTOCOL_VERSION, MODERN_PROTOCOL_VERSIONS
from scenarios import exercises

import rpc
from tokens import mint

READ_TOOL = "list_requisitions"

CALL = {"name": READ_TOOL, "arguments": {}}

A_REVISION_THIS_SERVER_DOES_NOT_IMPLEMENT = "1999-01-01"
"""Not a handshake revision either, which is what keeps it a modern-era request.

Era routing sends a version header it does not recognise to the **modern** entry
— the legacy leg is chosen by the header being absent or naming a handshake
revision — so an unknown value arrives at the classifier rather than at the
transport that would have negotiated it.
"""


def _token() -> str:
    """One reader's credential, for the rungs that sit past the token gate."""
    return mint("tomas.weber", ["erp.read"]).access_token


@exercises("header_body_mismatch")
def test_header_body_mismatch() -> None:
    """A header claiming one method while the body carries another is refused.

    Scenario: `header_body_mismatch`, `basis: clause`, `MUST` — *"Servers … MUST
    reject requests where the values specified in the headers do not match the
    corresponding values in the request body."*

        removal: Route on the header without comparing it to the body.

    `floor: true`, as gate 2. It is the step that makes gate 3 safe: the
    `server/discover` exemption is granted on a method, the method arrives in a
    caller-controlled header, and proving header and body agree first is what
    turns an authentication bypass into something structurally impossible.
    `auth_bypass_via_method_header_mismatch` is that attack; this is the
    comparison it runs into.

    **Refused with no token in play.** The mismatch is caught ahead of gate 4,
    which is why this request carries a credential and would have been refused
    without one: what is asserted is the comparison, not the order, and the order
    is the other row's.
    """
    headers = rpc.routing_headers("tools/call", CALL, token=_token())
    headers[MCP_METHOD_HEADER] = "tools/list"

    response = rpc.send(headers, rpc.envelope("tools/call", CALL))

    assert response.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(response)["code"] == HEADER_MISMATCH
    # The call did not run: a refusal carrying a result would mean the
    # comparison happened after dispatch, which is no comparison at all.
    assert "result" not in response.json()


@exercises("header_body_mismatch")
def test_the_name_header_is_compared_after_the_sentinel_form_is_decoded() -> None:
    """The Base64 sentinel form, both ways round — where a naive comparison goes wrong.

    Scenario: `header_body_mismatch`.

    `Mcp-Name` carries a tool name that may not survive an HTTP field
    round-trip, so the protocol package wraps such values in a `=?base64?…?=`
    sentinel. A server that compares the **raw header** to the body value is
    wrong in both directions and the pair is what shows it: it refuses a
    legitimate request whose name arrived encoded, and — the half that matters —
    it can be made to pass a request where the encoded header and the body name
    two different tools, by any encoding difference the comparison does not
    understand.

    So the assertion is that the comparison is against the **decoded value**: the
    sentinel form of the body's own name is accepted, and the sentinel form of
    another tool's name is refused.
    """
    encoded = encode_header_value(READ_TOOL)
    sentinel = f"=?base64?{base64.b64encode(READ_TOOL.encode('utf-8')).decode('ascii')}?="
    # The codec passes a header-safe name through verbatim, so the sentinel form
    # has to be written out to be exercised at all. Both spell one tool name.
    assert encoded == READ_TOOL
    assert sentinel != READ_TOOL

    agreeing = rpc.routing_headers("tools/call", CALL, token=_token())
    agreeing[MCP_NAME_HEADER] = sentinel
    permitted = rpc.send(agreeing, rpc.envelope("tools/call", CALL))
    assert permitted.status_code == httpx2.codes.OK, permitted.text

    named_elsewhere = {"name": "get_requisition", "arguments": {"id": "req_0001"}}
    disagreeing = rpc.routing_headers("tools/call", named_elsewhere, token=_token())
    disagreeing[MCP_NAME_HEADER] = sentinel

    refused = rpc.send(disagreeing, rpc.envelope("tools/call", named_elsewhere))

    assert refused.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(refused)["code"] == HEADER_MISMATCH


@exercises("missing_required_header")
def test_missing_required_header() -> None:
    """A POST omitting a required standard header is refused rather than defaulted.

    Scenario: `missing_required_header`, `basis: clause`, `MUST` — *"These
    headers are REQUIRED for compliance. … servers MUST return HTTP status 400
    Bad Request and MUST include a JSON-RPC error response … A required standard
    header (MCP-Protocol-Version, Mcp-Method, Mcp-Name) is missing."*

        removal: Default a missing header from the body instead of refusing.

    **Absence is a mismatch, which is the whole of the implementation.** There is
    no separate *missing* branch to get wrong: the header is compared to the body
    and nothing never equals something. Under the recorded removal the comparison
    is skipped when the header is absent, which is precisely how the exemption
    gate 3 grants becomes reachable without proof — so this row and
    `header_body_mismatch` split on the deletion rather than on the answer, and
    the answer is the same `-32020` for both.

    **The version header is deliberately not one of the two tested here.**
    Omitting it is not a header failure on this server: era routing keys on it
    before any gate runs, so a request without one is a *legacy* request and is
    carried by ADR-0009's three seam rows. Asserting a `400` for it would be
    asserting against a server this exhibit does not run.
    """
    without_method = rpc.routing_headers("tools/list", {}, token=_token())
    del without_method[MCP_METHOD_HEADER]

    refused = rpc.send(without_method, rpc.envelope("tools/list", {}))

    assert refused.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(refused)["code"] == HEADER_MISMATCH

    without_name = rpc.routing_headers("tools/call", CALL, token=_token())
    del without_name[MCP_NAME_HEADER]

    also_refused = rpc.send(without_name, rpc.envelope("tools/call", CALL))

    assert also_refused.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(also_refused)["code"] == HEADER_MISMATCH


@exercises("protocol_version_skew")
def test_protocol_version_skew() -> None:
    """A version header disagreeing with the envelope's own declared version.

    Scenario: `protocol_version_skew`, `basis: clause`, `MUST` — *"If the values
    do not match, the server MUST reject the request with 400 Bad Request and a
    HeaderMismatch JSON-RPC error."*

        removal: Read the version from the header and ignore `_meta`.

    **`HeaderMismatch`, not `UnsupportedProtocolVersion`, and the distinction is
    the row.** The envelope here names a revision this server does not implement,
    so a server that read the header and ignored `_meta` would answer `-32022`
    and tell the caller its *version* is the problem. The truth is that the
    request disagrees with itself, and the clause names the code that says so.
    `unsupported_protocol_version` is the row where both halves agree on an
    unimplemented revision, and it gets the other code.

    Past the token gate, so it carries one: this rung is the protocol package's
    and sits behind the gate chain.
    """
    headers = rpc.routing_headers("tools/list", {}, token=_token())
    assert headers[MCP_PROTOCOL_VERSION_HEADER] == LATEST_PROTOCOL_VERSION

    body = rpc.envelope("tools/list", {})
    body["params"]["_meta"][PROTOCOL_VERSION_META_KEY] = A_REVISION_THIS_SERVER_DOES_NOT_IMPLEMENT

    response = rpc.send(headers, body)

    assert response.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(response)["code"] == HEADER_MISMATCH


@exercises("malformed_meta")
def test_malformed_meta() -> None:
    """A POST missing a required `_meta` field is refused as malformed.

    Scenario: `malformed_meta`, `basis: clause`, `MUST` — *"A request missing any
    required field is malformed; the server MUST reject it with JSON-RPC error
    code -32602 … the response status MUST be 400 Bad Request."*

        removal: Make `_meta` optional in the request model.

    Two shapes, because the removal reaches both: no `_meta` at all, and a
    `_meta` carrying only some of what the envelope requires. The second is the
    one an optional model actually produces — a client that sends the object and
    forgets a key — and a server that accepted it would be negotiating a protocol
    version from a default nobody sent.
    """
    absent = rpc.envelope("tools/list", {})
    del absent["params"]["_meta"]

    refused = rpc.send(rpc.routing_headers("tools/list", {}, token=_token()), absent)

    assert refused.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(refused)["code"] == INVALID_PARAMS

    partial = rpc.envelope("tools/list", {})
    partial["params"]["_meta"] = {PROTOCOL_VERSION_META_KEY: LATEST_PROTOCOL_VERSION}

    also_refused = rpc.send(rpc.routing_headers("tools/list", {}, token=_token()), partial)

    assert also_refused.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(also_refused)["code"] == INVALID_PARAMS


@exercises("unsupported_protocol_version")
def test_unsupported_protocol_version() -> None:
    """A revision this server does not implement is refused with the list it does.

    Scenario: `unsupported_protocol_version`, `basis: adr`, sourced to ADR-0009
    §The gate chain is not uniform across the two legs.

        removal: Exempt an unrecognised `MCP-Protocol-Version` from gate 4, so
                 the classifier's supported-version list answers a caller
                 holding no token.

    **The row ADR-0010 held out until the seam assertions answered its
    condition.** That condition was whether a modern-era request declaring an
    unsupported version still reaches the gate chain — ADR-0009 having voided the
    earlier observation, because era routing precedes the chain entirely. It
    does, and this is where that stops being a note and becomes a falsifier.

    Both halves are asserted, because the row is about **where** the refusal
    happens as much as what it says. Unauthenticated, the token gate answers
    first and the supported-version list is not disclosed to a stranger. With a
    token, the classifier answers `-32022` carrying the revisions this server
    does implement and echoing the one that was asked for — which is also what
    proves the request reached the modern entry rather than the legacy leg, since
    the handshake era has no such code and would have negotiated instead.
    """
    headers = {
        **rpc.TRANSPORT_HEADERS,
        MCP_PROTOCOL_VERSION_HEADER: A_REVISION_THIS_SERVER_DOES_NOT_IMPLEMENT,
        MCP_METHOD_HEADER: "tools/list",
    }
    body = rpc.envelope("tools/list", {})
    body["params"]["_meta"][PROTOCOL_VERSION_META_KEY] = A_REVISION_THIS_SERVER_DOES_NOT_IMPLEMENT

    unauthenticated = rpc.send(headers, body)

    assert unauthenticated.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(unauthenticated)["resource_metadata"] == rpc.METADATA_URL
    assert not unauthenticated.content

    refused = rpc.send({**headers, "authorization": f"Bearer {_token()}"}, body)

    assert refused.status_code == httpx2.codes.BAD_REQUEST
    error = rpc.error(refused)
    assert error["code"] == UNSUPPORTED_PROTOCOL_VERSION
    data: dict[str, Any] = error["data"]
    assert data["supported"] == list(MODERN_PROTOCOL_VERSIONS)
    assert data["requested"] == A_REVISION_THIS_SERVER_DOES_NOT_IMPLEMENT

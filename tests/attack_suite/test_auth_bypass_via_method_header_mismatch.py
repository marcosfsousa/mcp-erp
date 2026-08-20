"""`auth_bypass_via_method_header_mismatch` — the exemption cannot be claimed on a header.

Scenario: `auth_bypass_via_method_header_mismatch`, `basis: adr`, sourced to
ADR-0006 §The gate order is a security property, not a style choice.

    removal: Move the exemption check ahead of header/body validation.

**The one row that covers a gate step which is a branch rather than a refusal.**
Gate 3 refuses nothing: it decides whether gate 4 runs. That makes it invisible
to every other row in the suite — a chain with the exemption in the wrong place
answers every one of them identically — and it is why ADR-0006 says the step is
worth a scenario *whichever order had been chosen*.

**What the attack is.** `server/discover` answers strangers, because a modern
client's path works by probing it and putting that probe behind a `401` would
rest the exhibit's third-party evidence on recovery behaviour nobody has tested.
The method arrives in a caller-controlled header. So: send
`Mcp-Method: server/discover`, put `tools/call` in the body, present no
credential, and a server that grants the exemption on the header executes a tool
for a caller holding nothing.

**The fix is ordering, not a special case**, which is what makes this row's
removal a *move* rather than a deletion. Prove header and body agree first and
the attack becomes inexpressible: there is no request that names the exempt
method to gate 3 and a tool to dispatch.

Its legacy-era twin is `legacy_discover_exemption_unavailable`, and the two are
different mechanisms behind the same door: there, gate 2 has no header to compare
and the exemption is unavailable because gate 3 keys on a method gate 2 *proved*.
"""

import httpx2
from mcp.shared.inbound import MCP_METHOD_HEADER
from mcp_types.jsonrpc import HEADER_MISMATCH
from mcp_types.version import LATEST_MODERN_VERSION
from scenarios import exercises

import rpc

DISCOVER = "server/discover"

TOOL = "list_requisitions"

CALL = {"name": TOOL, "arguments": {}}


@exercises("auth_bypass_via_method_header_mismatch")
def test_the_exemption_is_unavailable_to_a_body_that_calls_a_tool() -> None:
    """The attack, refused by the comparison rather than by the token gate.

    `-32020` and not `401` is the assertion. Both are refusals and only one of
    them says the right thing: the request never got as far as being about a
    missing credential, because it was rejected for disagreeing with itself —
    which is the order ADR-0006 fixed and the reason gate 3 is safe.

    Under the recorded removal this exact request returns a tool result to a
    caller who presented nothing.
    """
    headers = rpc.routing_headers("tools/call", CALL)
    headers[MCP_METHOD_HEADER] = DISCOVER

    response = rpc.send(headers, rpc.envelope("tools/call", CALL))

    assert response.status_code == httpx2.codes.BAD_REQUEST
    assert rpc.error(response)["code"] == HEADER_MISMATCH
    assert "result" not in response.json()


@exercises("auth_bypass_via_method_header_mismatch")
def test_the_exemption_it_tried_to_claim_is_real() -> None:
    """The control, and without it the row asserts nothing.

    A refusal above would look identical on a server that had simply never
    granted the exemption — at which point the test says *the unauthenticated
    method does not exist* rather than *it cannot be claimed by a tool call*. So:
    the same absent credential, an honest header, and a `200`.
    """
    permitted = rpc.post(DISCOVER, {})

    assert rpc.result(permitted)["supportedVersions"] == [LATEST_MODERN_VERSION]


@exercises("auth_bypass_via_method_header_mismatch")
def test_the_body_it_smuggled_needs_a_token_when_it_is_declared_honestly() -> None:
    """The other control: the smuggled call is one the token gate refuses.

    Same body, same absent credential, and a header that tells the truth about
    it — `401`. Which pins what the header was buying: not a different tool, not
    a different argument, but the token check itself.
    """
    refused = rpc.post("tools/call", CALL)

    assert refused.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(refused)["resource_metadata"] == rpc.METADATA_URL

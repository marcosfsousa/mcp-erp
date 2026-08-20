"""`get_stream_removed` — the modern leg answers `GET` and `DELETE` with `405`.

Scenario: `get_stream_removed`, `basis: clause`, `SHOULD` — *"A server that
supports only this revision and receives such traffic from an older client SHOULD
respond as follows: … HTTP GET or DELETE to the MCP endpoint: respond with 405
Method Not Allowed."*

    removal: Route a `GET` carrying a modern `MCP-Protocol-Version` to the
             handshake-era transport, which answers it with a stream.

**This row arrived carrying two defects, both raised from #37 and both this
ticket's** — recorded on #44 in full, and closed here:

*It claimed `status: asserted` with no test behind it.* Nothing in
`tests/attack_suite/` or `tests/wire/` issued a `GET` at all; every request in
both went through `rpc.post`. The suite's invariant is that exactly one row may
carry `status: documented`, and a row claiming an assertion that does not exist
is that second exemption wearing the wrong label. This file is the assertion.

*It cited `405` where the chain answers `401`.* Executed by hand against the
running stack, the four answers are:

===============================================  ===============================
`GET`, no token, any version header              `401` + challenge — **gate 4**
`GET`, token, `MCP-Protocol-Version` set         `405` + `Allow: POST`
`GET`, token, no version header                  an open `text/event-stream`
`DELETE`, token                                  `405`
===============================================  ===============================

The `405` is real and is reachable **only with a valid token on the modern
leg**. Unauthenticated, gate 4 refuses first, which is ADR-0006's ordering
working as designed rather than a defect. A test written from the row as it stood
would have asserted `405` against an unauthenticated `GET` and failed — or been
written to pass and quietly asserted the wrong thing. So the credential below is
load-bearing, and map constraint `#6` was amended to say the `405`/`401` split
out loud.

**And its `removal` named a deletion nothing could see, which is why it moved.**
It read *"Register a GET route on the MCP endpoint"* — but the route
`mcp_erp.app` registers is an ASGI application under a Starlette `Route` with no
method restriction, so `GET` already reaches the protocol package on both legs
and a second registration could never be reached. #38 found the same defect on
`legacy_underscoped_same_denial_class` and named the rule: **a removal nobody can
perform is a row nobody can falsify.** The deletion recorded now is the one this
file's assertion actually rests on — the era routing that sends a version-bearing
`GET` to the modern entry, where it is refused, instead of to the handshake-era
transport, which would open the stream the row exists to keep out of the modern
era.

**The legacy leg's stream is not this row's business and is not a defect.** It
exists, ADR-0008 records that the substrate offers no way to switch it off, and
ADR-0009 authorises it identically to any other legacy traffic. The row's
`prevents` line scopes itself to *"surviving into the **modern era**"* for exactly
that reason, and the test below asserts the modern leg alone.
"""

import httpx2
from mcp.shared.inbound import MCP_PROTOCOL_VERSION_HEADER
from mcp_types.version import LATEST_PROTOCOL_VERSION
from scenarios import exercises

import rpc
from tokens import mint

ALLOW = "allow"


def _credential() -> dict[str, str]:
    """A real reader's token, which is what the `405` sits behind."""
    return {"authorization": f"Bearer {mint('tomas.weber', ['erp.read']).access_token}"}


@exercises("get_stream_removed")
def test_a_modern_get_is_refused_with_method_not_allowed() -> None:
    """The scenario. `405`, and the `Allow` header that says what the endpoint is for.

    The version header is what makes this a modern-era request, and the token is
    what gets it past gate 4 — both are the difference between asserting the
    clause and asserting the gate chain that stands in front of it.

    `Allow: POST` is asserted rather than the status alone because it is the
    half a client can act on: the specification's own remedy for an older client
    is to learn that this endpoint takes one method.
    """
    with httpx2.Client(base_url=rpc.BASE_URL, timeout=rpc.TIMEOUT) as http:
        response = http.get(
            rpc.ENDPOINT,
            headers={
                **_credential(),
                MCP_PROTOCOL_VERSION_HEADER: LATEST_PROTOCOL_VERSION,
            },
        )

    assert response.status_code == httpx2.codes.METHOD_NOT_ALLOWED
    assert response.headers[ALLOW] == "POST"


@exercises("get_stream_removed")
def test_a_delete_is_refused_the_same_way() -> None:
    """The clause names `GET` **or** `DELETE`, and session termination is the other half.

    A stateless server has no session to terminate — map constraint `#5` — so
    there is nothing here for a `DELETE` to mean, and the refusal says so in the
    protocol's own words rather than by ignoring the request.
    """
    with httpx2.Client(base_url=rpc.BASE_URL, timeout=rpc.TIMEOUT) as http:
        response = http.request(
            "DELETE",
            rpc.ENDPOINT,
            headers={**_credential(), MCP_PROTOCOL_VERSION_HEADER: LATEST_PROTOCOL_VERSION},
        )

    assert response.status_code == httpx2.codes.METHOD_NOT_ALLOWED


@exercises("get_stream_removed")
def test_an_unauthenticated_get_meets_the_token_gate_first() -> None:
    """The correction, asserted rather than described: `401` before `405`.

    This is the request the row's citation reads as though it describes, and it
    is answered by ADR-0006's gate 4 — before the transport is reached at all, so
    the method it would have refused never comes up. Asserting it here is what
    stops the next reader writing the `405` assertion against a stranger and
    concluding the server is wrong.

    It is also the more useful of the two answers: an unauthenticated caller
    learns where to get a credential, and learns nothing about which methods the
    endpoint serves.
    """
    with httpx2.Client(base_url=rpc.BASE_URL, timeout=rpc.TIMEOUT) as http:
        response = http.get(
            rpc.ENDPOINT, headers={MCP_PROTOCOL_VERSION_HEADER: LATEST_PROTOCOL_VERSION}
        )

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(response)["resource_metadata"] == rpc.METADATA_URL
    assert ALLOW not in response.headers

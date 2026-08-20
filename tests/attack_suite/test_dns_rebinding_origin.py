"""`dns_rebinding_origin` — a request that came from a browser is refused.

Scenario: `dns_rebinding_origin`, `basis: clause`, `MUST` — *"Servers MUST
validate the Origin header on all incoming connections … servers MUST respond
with HTTP 403 Forbidden."*

    removal: Skip the allow-list check when `Origin` is present.

**The threat is specific and so is the defence.** DNS rebinding is a malicious
page in a victim's browser reaching a server on the victim's own machine — an
exhibit that runs on `localhost` is exactly the target. A browser attaches
`Origin` to such a request automatically and a page cannot forge it; non-browser
clients send none. So the allow-list **ships empty**, and the emptiness is the
position rather than an unfinished configuration: every real client is
unaffected, and every browser-originated request is refused.

**`floor: true`, as gate 1, and it is the honest limit ADR-0006 states out
loud** — no client in this exhibit sends an `Origin`, so this negative scenario
is the only thing that exercises the check at all. A row nobody could delete
without a red check, guarding a path nothing else reaches.

**The refusal carries no challenge, deliberately.** Re-authorizing would not
help: what is refused is where the request came from rather than what it
carried, and ADR-0002 keys refusal shape on the remedy.
"""

import httpx2
from scenarios import exercises

import rpc
from tokens import mint

BROWSER_ORIGIN = "https://malicious.example"

TOOL = "list_requisitions"

CALL = {"name": TOOL, "arguments": {}}


@exercises("dns_rebinding_origin")
def test_a_browser_originated_call_is_refused_even_with_a_valid_token() -> None:
    """The scenario. A good credential does not buy a bad origin anything.

    The token is genuine and would be permitted from anywhere else, which is what
    makes this about the origin: a page that had somehow obtained a token still
    cannot reach the tool from a browser.
    """
    headers = rpc.routing_headers(
        "tools/call", CALL, token=mint("tomas.weber", ["erp.read"]).access_token
    )
    headers["origin"] = BROWSER_ORIGIN

    response = rpc.send(headers, rpc.envelope("tools/call", CALL))

    assert response.status_code == httpx2.codes.FORBIDDEN
    assert "www-authenticate" not in response.headers
    assert "result" not in response.text


@exercises("dns_rebinding_origin")
def test_the_same_call_without_an_origin_is_permitted() -> None:
    """The control: the header is the only difference between refused and served.

    Every other suite in this directory sends no `Origin` and is answered, so
    this could be left implicit — and it is not, because a `403` proves nothing
    on its own about *which* of the request's properties earned it.
    """
    permitted = rpc.call_tool(TOOL, token=mint("tomas.weber", ["erp.read"]).access_token)

    assert permitted.status_code == httpx2.codes.OK, permitted.text


@exercises("dns_rebinding_origin")
def test_the_gate_covers_the_unauthenticated_document_too() -> None:
    """Gate 1 sits on **every** path, which is what *all incoming connections* means.

    The protected resource metadata document is the one route that answers
    without a token, and it is exactly as reachable from a browser as the tool
    endpoint is — so a rebinding gate mounted on the tool route alone would leave
    the one document a page can read unguarded. It is served by a sibling route
    rather than by a path allow-list, so nothing about its exemption from the
    token gate carries over to this one.
    """
    refused = rpc.get(rpc.METADATA_PATH, headers={"origin": BROWSER_ORIGIN})
    permitted = rpc.get(rpc.METADATA_PATH)

    assert refused.status_code == httpx2.codes.FORBIDDEN
    assert permitted.status_code == httpx2.codes.OK
    assert permitted.json()["resource"] == rpc.RESOURCE

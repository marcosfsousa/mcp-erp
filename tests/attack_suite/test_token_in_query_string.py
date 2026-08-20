"""`token_in_query_string` — a credential in the URI buys nothing.

Scenario: `token_in_query_string`, `basis: clause`, `MUST NOT` — *"Access tokens
MUST NOT be included in the URI query string."*

    removal: Read the bearer token from the query string when the header is
             absent.

**The clause is about where a credential ends up, not about whether it works.** A
token in a query string is written to access logs, kept in browser history, and
handed to whatever the next hop's `Referer` reaches — so a server that honoured
one would be spreading a valid credential across systems that were never supposed
to hold it, every request, silently.

**There is deliberately no fallback to delete.** ADR-0006 publishes
`bearer_methods_supported: ["header"]` in the protected resource metadata, which
turns *a token in the query string is not honoured* from a behaviour this server
happens to exhibit into a contract it keeps — and the document is asserted here
beside the behaviour, because a published contract nothing checks is the pair
this suite exists to keep together.

**The refusal is the no-credential one, and that is the right one.** RFC 6750
draws the line at whether a credential was *presented*, and one in the query
string was not presented — so the challenge carries no `error` parameter. A
server that answered `invalid_token` here would be telling the client something
is wrong with its token, when what is wrong is that it has not sent one.
"""

import httpx2
from scenarios import exercises

import rpc
from tokens import mint

TOOL = "list_requisitions"

CALL = {"name": TOOL, "arguments": {}}


@exercises("token_in_query_string")
def test_token_in_query_string() -> None:
    """The same token, in the query string instead of the header, is not honoured.

    One credential, two places, two answers — which is what makes this about the
    presentation rather than about the token. The permitted call is not
    decoration: without it a `401` would be equally consistent with a token that
    had simply expired.
    """
    minted = mint("tomas.weber", ["erp.read"])

    permitted = rpc.call_tool(TOOL, token=minted.access_token)
    assert permitted.status_code == httpx2.codes.OK, permitted.text

    refused = rpc.send(
        rpc.routing_headers("tools/call", CALL),
        rpc.envelope("tools/call", CALL),
        path=f"{rpc.ENDPOINT}?access_token={minted.access_token}",
    )

    assert refused.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(refused)
    # No credential was presented, so nothing is wrong with one: RFC 6750's own
    # line, and ADR-0006 honours it.
    assert "error" not in parameters
    assert parameters["resource_metadata"] == rpc.METADATA_URL
    assert "result" not in refused.text


@exercises("token_in_query_string")
def test_the_metadata_publishes_the_header_as_the_only_method() -> None:
    """The contract half: `bearer_methods_supported` names one method and means it.

    A client reading the document learns where to put its credential, and this
    row is what makes that document true. The two assertions are the same claim
    from either end — what the server publishes, and what it does — and neither
    is worth much without the other.
    """
    document = rpc.get(rpc.METADATA_PATH).json()

    assert document["bearer_methods_supported"] == ["header"]

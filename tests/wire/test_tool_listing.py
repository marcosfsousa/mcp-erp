"""What the listing declares to everybody, and the invariance across callers.

**The filter itself is not here any more.** #66 drew the line this directory is
named for — an assertion whose expected value *changes with the caller* is the
decision matrix's — and #43 moved the five it named, one per scope set the filter
is exercised across. They are rows of `matrix.yaml` now, driven by
`tests/matrix/test_rows_for_the_tool_listing.py`. The fourth refusal in ADR-0002's
set is **absence**, and absence varies with the token, so it went with them.

What is left is the same rule read the other way. `cacheScope`, the `ttlMs` cap,
the declared schemas and `listChanged: false` are things the server states
**identically to every caller**, so there is no principal to key them on. *The
listing is a function of the token and not of the person* asserts an invariance
**across** callers rather than a value that varies with one — splitting it into
two rows would keep both halves and lose the equality between them, which is the
entire claim and what ADR-0002's cache proof rests on. And the agreement between
the listing and the call is something nothing in `scenarios.yaml` consults.

The freshness hint is the part that has an argument underneath it.
`cacheScope: "private"` is forced — the specification warns that a `"public"`
result from an authenticated endpoint may be shared between callers, and a
scope-filtered listing marked public is a cross-principal leak. `ttlMs = min(5
minutes, remaining token lifetime)` is safe only because the listing is a **pure
function of the access token**: new scopes mean a new token, which is a different
cache key under `private`, so the cache cannot serve a listing that misrepresents
the caller's scopes.
"""

import time

import httpx2

import rpc
from tokens import Minted, mint

FIVE_MINUTES_MS = 300_000
"""ADR-0002's cap, and the number the realm's five-minute token makes a real `min`."""

TOOL = "list_requisitions"

EVERY_TOOL = {
    "list_requisitions",
    "get_requisition",
    "submit_requisition",
    "record_invoice",
    "approve_requisition",
}
"""The whole declared set, which is what the schema assertion below walks.

The three per-capability sets this file used to hold went to `matrix.yaml` with
the rows that asserted them — which scope reaches which tools is precisely a
value that varies with the caller. What remains is a claim about every tool at
once, so it needs the union rather than the split.
"""


def _listing(minted: Minted) -> dict[str, object]:
    """The `tools/list` result for one minted token."""
    return rpc.result(rpc.post("tools/list", token=minted.access_token))


def _names(minted: Minted) -> set[str]:
    """The tool names one token reaches."""
    tools = _listing(minted)["tools"]
    assert isinstance(tools, list)
    return {tool["name"] for tool in tools}


def test_the_listing_is_a_function_of_the_token_and_not_of_the_person() -> None:
    """The invariant ADR-0002's cache proof rests on, asserted where it is observable.

    Two people whose ERP roles differ as much as the cast allows — one holding no
    role at all, one holding the auditing role that widens every read — get the
    same listing under the same scope set. That is `permits_scope` reading
    token-derived fields only. A role check on the listing would make a directory
    revocation invisible for up to five minutes on an unchanged token, and
    nothing in the code would object.
    """
    assert _names(mint("priya.raman", ["erp.read"])) == _names(mint("anna.lindqvist", ["erp.read"]))


def test_the_listing_is_private_and_expires_with_the_token() -> None:
    """`cacheScope: "private"`, and `ttlMs = min(5 minutes, remaining token lifetime)`."""
    minted = mint("priya.raman", ["erp.read"])
    listing = _listing(minted)

    assert listing["cacheScope"] == "private"

    remaining_ms = int((int(minted.claims["exp"]) - time.time()) * 1000)
    ttl = listing["ttlMs"]
    assert isinstance(ttl, int)
    assert 0 < ttl <= FIVE_MINUTES_MS
    # The realm issues five-minute tokens, so the token's own remaining lifetime
    # is the `min`'s winner and the cap is what stops a longer-lived token from
    # buying a longer cache. A few seconds of tolerance, because the two clocks
    # are the container's and this machine's.
    assert ttl <= remaining_ms + 5_000
    assert ttl >= remaining_ms - 5_000


def test_the_listing_declares_the_schemas_layer_three_authored() -> None:
    """`outputSchema` is declared on every tool, and each input schema says what it takes.

    The listing takes nothing, which is the governing rule holding rather than an
    omission: a cost-centre filter would change no authorization decision and a
    free-text one would leak which centres exist. The named read takes exactly
    one argument, which is the identifier it is named for and nothing beside it.
    """
    tools = _listing(mint("priya.raman", ["erp.read", "erp.write", "erp.decide"]))["tools"]
    assert isinstance(tools, list)
    declared = {tool["name"]: tool for tool in tools}

    assert set(declared) == EVERY_TOOL
    for tool in declared.values():
        assert tool["inputSchema"]["additionalProperties"] is False
        assert tool["outputSchema"]["additionalProperties"] is False

    assert declared["list_requisitions"]["inputSchema"]["properties"] == {}
    assert declared["list_requisitions"]["outputSchema"]["required"] == ["requisitions"]

    assert declared["get_requisition"]["inputSchema"]["required"] == ["id"]
    assert declared["get_requisition"]["outputSchema"]["required"] == ["requisition"]

    # No `cost_centre` anywhere in a write's arguments: the partition is
    # server-derived, so an out-of-partition write is inexpressible rather than
    # refused, and no schema enumerates the organisation's centres.
    assert "cost_centre" not in declared["submit_requisition"]["inputSchema"]["properties"]
    assert "cost_centre" not in declared["approve_requisition"]["inputSchema"]["properties"]
    assert "cost_centre" not in declared["record_invoice"]["inputSchema"]["properties"]
    # And no `amount` either: the threshold is decided on the row the server
    # holds, never on a number the caller restated — and an invoice has no
    # amount at all, because the order it bills fixes one.
    assert "amount" not in declared["approve_requisition"]["inputSchema"]["properties"]
    assert "amount" not in declared["record_invoice"]["inputSchema"]["properties"]


def test_the_tool_set_is_fixed_at_deploy() -> None:
    """`listChanged: false`.

    That notification announces that the **server's** tool set changed; ours is
    fixed at deploy. What varies here is per-caller, which the notification
    cannot express — and declaring it would additionally require a streaming
    endpoint that map constraint `#6` refuses.

    "A **second** streaming endpoint" until 2026-08-19, when ADR-0002 cut the
    first one. The clause still refuses this: `#6`'s standalone-stream half is
    untouched by the cut, and it is the half this cites.
    """
    capabilities = rpc.result(rpc.post("server/discover"))["capabilities"]
    assert capabilities["tools"]["listChanged"] is False


def test_calling_a_tool_the_listing_omits_is_refused_and_says_which_scope() -> None:
    """An unlisted tool called anyway gets a `403` naming the tool and the scope.

    It discloses the shape of the API and never the contents of the database: the
    scope is genuinely published in `scopes_supported`, and the tool name is one
    the caller themselves supplied.
    """
    response = rpc.call_tool(TOOL, token=mint("priya.raman").access_token)

    assert response.status_code == httpx2.codes.FORBIDDEN
    parameters = rpc.challenge(response)
    assert parameters["error"] == "insufficient_scope"
    assert parameters["scope"] == "erp.read"
    assert parameters["resource_metadata"] == rpc.METADATA_URL

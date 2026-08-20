"""`tools/list` filters on granted scope alone, and says how long it may be cached.

The fourth refusal in ADR-0002's set is **absence**: a tool the caller's token
does not reach is not in the listing at all, rather than refused on the way in.

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

READ_TOOLS = {"list_requisitions", "get_requisition"}
"""The two tools declaring `read`, and therefore the whole of what `erp.read` reaches."""

WRITE_TOOLS = {"submit_requisition", "record_invoice"}
"""The two tools declaring `write`, and the pair ADR-0012's coarse verbs are for.

One scope reaches both, and the ERP role decides which of the two a caller
actually achieves anything with — `submit_requisition` requires none and
`record_invoice` requires `invoice_clerk`. That is the intersection doing visible
work, and it is why `erp.write` is ungated at issuance: a role mapping on it would
lock every submitter out of a scope ADR-0003 gives them.
"""

DECIDE_TOOLS = {"approve_requisition"}
"""The one tool declaring `decide`, and the only one of the three sets that is
gated by a role as well — which is what makes the listing's *scope alone* filter
observable rather than merely stated."""


def _listing(minted: Minted) -> dict[str, object]:
    """The `tools/list` result for one minted token."""
    return rpc.result(rpc.post("tools/list", token=minted.access_token))


def _names(minted: Minted) -> set[str]:
    """The tool names one token reaches."""
    tools = _listing(minted)["tools"]
    assert isinstance(tools, list)
    return {tool["name"] for tool in tools}


def test_a_read_token_reaches_the_read_tools() -> None:
    """The positive case: one capability, and every tool declaring it."""
    assert _names(mint("priya.raman", ["erp.read"])) == READ_TOOLS


def test_a_token_with_no_capability_scope_reaches_nothing() -> None:
    """Absence is the fourth refusal, and it is the one with no wire shape at all.

    Every token carries at least `openid`, so this is a token that authenticates
    and reaches nothing rather than a token that fails.
    """
    assert _names(mint("priya.raman")) == set()


def test_the_write_scope_reaches_the_write_tool_and_no_read_tool() -> None:
    """Scopes are a plain set with **no implication between them**.

    All eight subsets of the three are legal, which is what keeps *may submit but
    never approve* and *may approve but not submit* both expressible. A ladder
    where one scope implied another would collapse the ceiling to one dimension
    and make a scope a role wearing a scope's clothes.

    Until `submit_requisition` shipped, the write half of that claim could only
    be made negatively — a write token reached nothing at all, which a ladder
    would also produce. Now the two capabilities partition the tool set, and the
    assertion is that a token holding one reaches its own side and neither more
    nor less.

    Since #42 the write side holds two tools, and the listing shows both to a
    Person who can use neither: Priya Raman holds no ERP role, so she reaches
    `record_invoice` here and is refused at its role gate when she calls it. That
    refusal is asserted where it happens, in `test_record_invoice.py`.
    """
    assert _names(mint("priya.raman", ["erp.write"])) == WRITE_TOOLS
    assert not READ_TOOLS & WRITE_TOOLS


def test_both_scopes_reach_the_union_and_nothing_else() -> None:
    """A token is a ceiling, and two capabilities buy exactly the two sides.

    Priya Raman holds no ERP role at all, so what she reaches here is the token's
    doing alone — which is the same fact `test_the_listing_is_a_function_of_the
    _token_and_not_of_the_person` makes from the other direction.
    """
    assert _names(mint("priya.raman", ["erp.read", "erp.write"])) == READ_TOOLS | WRITE_TOOLS
    assert not (READ_TOOLS | WRITE_TOOLS) & DECIDE_TOOLS


def test_the_deciding_scope_reaches_the_deciding_tool_for_a_person_who_may_not_use_it() -> None:
    """The listing filters on granted scope **alone**, so a role gate is invisible here.

    Priya Raman holds `approver` in the realm and no ERP role at all, so the
    realm issues her `erp.decide` and the server refuses her at the role gate.
    She sees the tool anyway — and that is the design: filtering on the
    intersection would hide it from her, and the `-31010` denial class would
    collapse into an absence with no wire shape at all.

    That refusal is asserted where it happens, in `test_approve_requisition.py`.
    What is asserted here is that she gets far enough to be refused.
    """
    assert _names(mint("priya.raman", ["erp.decide"])) == DECIDE_TOOLS


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

    assert set(declared) == READ_TOOLS | WRITE_TOOLS | DECIDE_TOOLS
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

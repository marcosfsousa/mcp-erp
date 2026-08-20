"""The refusal contract, across all three live tools at once.

    A resource **named** in the request is refused, never omitted.
    A resource **discovered** by listing is omitted, never refused.

ADR-0013 wrote that sentence because the two halves are one contract and only
one of them was being checked. Each half has its own falsifier in the attack
suite — `row_probe_indistinguishable` for named, `list_partition_scoped` for
discovered — and both of those look at one tool. This looks at the seam between
them: **one identifier, two tools, and the two answers a caller gets.**

`submit_requisition` is the third tool and it names no resource, so neither half
governs it directly. What it contributes is the row: a caller raises one, and
the pair above is then asserted about a row this run created rather than only
about seeded ones. That is also the only place all three tools appear in one
sequence, which is what makes *holds across all three* a thing to point at.

**Where this lives, since #43 wrote `matrix.yaml`.** This is the seam *between*
two tools rather than a row about either: neither attack-suite row says that the
**same** row takes the **other** shape through the other tool, and no
`(principal x tool x resource)` row does either — a row names one tool. So it
stays, on the narrow ground the wire README already records for it.
"""

from collections.abc import Iterator
from typing import Any

import pytest

import fixtures
import requisitions as visible
import rpc
from tokens import mint

GET = "get_requisition"
LIST = "list_requisitions"
SUBMIT = "submit_requisition"

INSIDER = "tomas.weber"
"""CC-4100, and the owner of the rows below."""

OUTSIDER = "yusuf.demir"
"""Everything Tomas is, in CC-4200 — the row-scoping foil the seed says he is."""


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Start from the generated fixtures; this module submits, so it must know where it began."""
    fixtures.load()
    yield


def _get(username: str, identifier: str) -> dict[str, Any]:
    """What `get_requisition` answers one Person, as a JSON-RPC result."""
    minted = mint(username, ["erp.read"])
    return rpc.result(rpc.call_tool(GET, {"id": identifier}, token=minted.access_token))


def _submitted(username: str) -> str:
    """Raise one requisition and return its identifier."""
    minted = mint(username, ["erp.write"])
    result = rpc.result(
        rpc.call_tool(
            SUBMIT,
            {
                "vendor": "Nordwind Office Supplies",
                "amount": "1200.00",
                "currency": "EUR",
                "description": "40 ergonomic desk chairs",
            },
            token=minted.access_token,
        )
    )

    assert result["isError"] is False, result
    identifier: str = result["structuredContent"]["requisition"]["id"]
    return identifier


def test_the_two_read_tools_agree_about_a_row_the_caller_may_see() -> None:
    """Named and discovered are the same row, described the same way.

    The two tools share one rendering — `Requisition.as_row` — and one output
    shape, so this is asserting that the sharing is real rather than that two
    descriptions happen to agree today.
    """
    identifier = fixtures.a_row_in("CC-4200")
    named = _get(OUTSIDER, identifier)

    assert named["isError"] is False, named
    assert named["structuredContent"]["requisition"]["id"] == identifier
    assert identifier in visible.visible_to(OUTSIDER)


def test_one_identifier_is_refused_by_name_and_omitted_from_the_listing() -> None:
    """Both halves of the contract, on one row, for one caller.

    This is the seam the two attack-suite rows do not cover between them: each
    asserts its own half about its own tool, and neither says that the *same*
    row takes the *other* shape through the other tool. A design that refused per
    row in the listing, or that omitted a named row by answering an empty
    success, would satisfy one row and fail here.
    """
    identifier = fixtures.a_row_in("CC-4300")

    named = _get(OUTSIDER, identifier)
    assert named["isError"] is True, named
    assert named["structuredContent"]["reason"] == "not_found"

    discovered = visible.visible_to(OUTSIDER)
    assert identifier not in discovered


def test_a_listing_carries_no_reason_for_what_it_leaves_out() -> None:
    """Omitted, never refused — so there is nowhere in the result to learn why.

    A per-row reason would be an existence oracle by the other route: the caller
    would learn a row is there and that somebody else can see it, which is
    exactly what the named half spends its refusal shape avoiding.
    """
    minted = mint(OUTSIDER, ["erp.read"])
    result = rpc.result(rpc.call_tool(LIST, token=minted.access_token))

    assert set(result["structuredContent"]) == {"requisitions"}
    for row in result["structuredContent"]["requisitions"]:
        assert "reason" not in row


def test_a_row_that_never_existed_is_refused_by_name_like_any_other() -> None:
    """Named is named, whether or not there is anything behind it.

    The byte-identity of this refusal with a foreign row's is the attack suite's;
    what is asserted here is only that an absent row takes the *named* shape —
    a refusal — rather than the discovered one.
    """
    absent = _get(INSIDER, fixtures.ABSENT_IDENTIFIER)

    assert absent["isError"] is True, absent
    assert absent["structuredContent"]["reason"] == "not_found"


def test_a_submitted_row_is_then_named_and_discovered_by_its_submitter() -> None:
    """All three tools in one sequence, on a row this run created.

    The write is the only one of the three that names no resource, so it is what
    puts a row into the contract rather than what the contract governs. Its
    partition is the submitter's, which is why the row it produces is one Tomas
    can both name and discover and one Yusuf can do neither with.
    """
    identifier = _submitted(INSIDER)

    named = _get(INSIDER, identifier)
    assert named["isError"] is False, named
    assert named["structuredContent"]["requisition"]["cost_centre"] == "CC-4100"
    assert identifier in visible.visible_to(INSIDER)

    refused = _get(OUTSIDER, identifier)
    assert refused["isError"] is True, refused
    assert refused["structuredContent"]["reason"] == "not_found"
    assert identifier not in visible.visible_to(OUTSIDER)

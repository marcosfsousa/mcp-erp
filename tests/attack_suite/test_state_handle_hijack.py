"""`state_handle_hijack` — possessing an identifier is not being allowed to write.

Scenario: `state_handle_hijack`, `basis: clause`, `normative_strength: MUST NOT`.

    MCP servers MUST NOT treat possession of a state handle as authentication.

    — MCP Security Best Practices §State Handle Hijacking, fetched 2026-08-12

A requisition identifier is a **state handle** by the specification's own
definition: an identifier a stateless server mints and receives back as an
ordinary tool argument on each request. The clause forbids treating possession of
one as authentication, and this is the write path's half of that — the read
path's is `row_probe_indistinguishable`, and the two split because their removals
are different deletions.

**The write half is the one that has to assert twice.** A refusal that answers
`not_found` and writes anyway is not a refusal, so the row is read back after the
attempt and a legitimate approver then decides it — which proves it was still
decidable rather than merely still readable. This is the only row in the suite
that asserts a refused write changed nothing.

**Reached by guessing, not by being handed the identifier.** ADR-0003 takes a
deliberate deviation from a specification `SHOULD` — identifiers are sequential
and legible — precisely so an attack scenario can guess a foreign one. What is
traded away is defence in depth: the attacker reaches the row-scoping check
rather than being stopped before it, and reaching it is what makes the check
demonstrated rather than asserted.

**The prober holds the deciding role**, and that is load-bearing. A prober with
no role would be refused at step 2 and the scenario would prove nothing about
step 3: what must stop him is the partition and only the partition.

*Removal, as the shipped design makes it.* `scenarios.yaml` was written at #9 and
names the removal as looking the row up without a cost-centre predicate — which
ADR-0013 then made **the design** rather than the removal: the store loads by
identifier alone and layer 2 refuses, so that the empty join and the foreign row
converge at one return site instead of in SQL. The deletion that makes this
attack succeed against the code that shipped is *taking the decision before the
chain has permitted it*. The row's `removal` field is corrected in the same
commit as this file.
"""

from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from scenarios import exercises

import fixtures
import rpc
from mcp_erp.purchase_to_pay.approve_requisition import THRESHOLD
from tokens import mint

APPROVE = "approve_requisition"
GET = "get_requisition"

PROBER = "yusuf.demir"
"""CC-4200, holding `approver` — everything the owner's approver holds, elsewhere.

The role matters as much as the centre. He clears the scope gate and the role
gate, so the only thing between him and a foreign row is row scoping, which is
the step this scenario is about.
"""

OWNER = "tomas.weber"
"""CC-4100, holding `approver`. Reads the row back, and decides it at the end."""

OWNER_SUBJECT = "tomas-weber"
"""The same person as the directory keys him, which is what a fixture's row holds.

Written out rather than derived from :data:`OWNER`. The seed's subjects happen to
be the usernames with the dot swapped for a hyphen, and a suite that relied on
that would be asserting against a coincidence in seven rows of authored data.
"""

TARGET_CENTRE = "CC-4100"


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Wipe and reload the rows once before this module, on ADR-0003's shape.

    This module decides a row at the end, so it must start from a row nothing has
    decided. Module-scoped rather than session-scoped for the reason the two
    suites beside it state.
    """
    fixtures.load()
    yield


def _guessed_identifier() -> str:
    """One generated identifier in a centre the prober does not hold, below the threshold.

    Drawn from the fixtures rather than from a listing, because a listing would
    never show it to him — which is the whole premise. Sequential identifiers are
    what make it guessable, and ADR-0003 took that deviation for exactly this.

    **Below the threshold, and not the owner's own row.** Both are asked for
    rather than assumed, because the answer has to be refused for the *partition*
    and nothing else: a row above €5,000 would additionally be refused for the
    amount — the prober holds `approver` and not `unlimited_approver` — and one
    the owner raised himself would be refused at the end for the separation edge,
    where this scenario needs the owner's decision to go through. A scenario that
    passes for two reasons cannot say which one it tested.
    """
    return fixtures.a_decidable_row_in(TARGET_CENTRE, not_raised_by=OWNER_SUBJECT)


def _decide(username: str, identifier: str) -> dict[str, Any]:
    """One `approve_requisition` call naming one item, as a JSON-RPC result.

    A one-item batch, which layer 1 renders directly rather than folding — so
    what this scenario reads back is the answer itself, exactly as it was before
    the list arrived at #41.
    """
    return rpc.result(
        rpc.call_tool(
            APPROVE,
            {"ids": [identifier], "decision": "approve"},
            token=mint(username, ["erp.decide"]).access_token,
        )
    )


def _row(username: str, identifier: str) -> dict[str, Any]:
    """The requisition as somebody who may see it reads it back."""
    result = rpc.result(
        rpc.call_tool(GET, {"id": identifier}, token=mint(username, ["erp.read"]).access_token)
    )

    assert result["isError"] is False, result
    row: dict[str, Any] = result["structuredContent"]["requisition"]
    return row


@exercises("state_handle_hijack")
def test_the_target_is_a_row_the_prober_could_otherwise_decide() -> None:
    """The precondition, held by a test rather than by trust.

    A scenario asserting that a write was refused passes just as well against a
    row that does not exist, at which point it asserts nothing. So: the row is
    there, it is in somebody else's centre, it is below the threshold, and the
    prober did not raise it — every reason to refuse him except the one under
    test is absent.
    """
    identifier = _guessed_identifier()
    row = _row(OWNER, identifier)

    assert row["cost_centre"] == TARGET_CENTRE
    assert row["status"] == "submitted"
    # Against the declared threshold rather than against a literal amount, since
    # #43 the fixtures come from `matrix.yaml` and the row this picks moves with
    # the table. What has to hold is the *property* the helper asked for.
    assert Decimal(row["amount"]) <= THRESHOLD
    assert row["submitted_by"]["id"] != "yusuf-demir"
    assert row["submitted_by"]["id"] != OWNER_SUBJECT


@exercises("state_handle_hijack")
def test_possession_of_a_guessed_identifier_does_not_authorize_the_write() -> None:
    """The clause. The handle is an argument, never a credential.

    `not_found` rather than a refusal naming the centre, because the row's
    existence and its cost centre are facts only the database holds — the same
    non-disclosure the read path keeps, arriving on the write path.
    """
    identifier = _guessed_identifier()

    refused = _decide(PROBER, identifier)

    assert refused["isError"] is True, refused
    assert refused["structuredContent"]["reason"] == "not_found"


@exercises("state_handle_hijack")
def test_the_refused_write_left_the_row_exactly_as_it_was() -> None:
    """The second half, and the half a refusal that wrote anyway would fail.

    Read back by somebody who may see it, then **decided by somebody who may
    decide it** — because *still submitted* could also be true of a row that had
    been damaged in some other way, and a row that can still be approved is one
    the attempt genuinely did not touch.
    """
    identifier = _guessed_identifier()

    _decide(PROBER, identifier)

    assert _row(OWNER, identifier)["status"] == "submitted"

    permitted = _decide(OWNER, identifier)
    assert permitted["isError"] is False, permitted
    assert permitted["structuredContent"]["requisition"]["status"] == "approved"
    assert permitted["structuredContent"]["purchase_order"]["approved_by"]["id"] == "tomas-weber"

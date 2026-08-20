"""`double_approval_via_batch_retry` — a retried batch cannot approve anything twice.

Scenario: `double_approval_via_batch_retry`, `basis: adr`, sourced to ADR-0002
§Surviving contact with a retrying client.

    removal: Drop per-item idempotency and decide each item afresh.

**The attacker here is a well-behaved client.** Nothing malicious is sent: the
same batch is submitted twice, which is what a model does when a result comes
back marked in error and it cannot tell which half of it failed. ADR-0002 states
the promise as *"a model that ignores every field and retries the whole batch
cannot double-approve"* — ignoring every field is the premise rather than the
failure, so this suite retries the call verbatim.

**Signalling is not control.** Every refusal in this project carries a remedy and
two retry booleans, and none of them are enforcement: a client is free to ignore
all three. What makes the promise true is the terminal-state predicate riding in
the `UPDATE` and the unique constraint on `purchase_order.requisition_id`, so the
second decision matches no row and mints no order — per item, inside one call.

**It could not be asserted until there was a batch.** #40 shipped the single-item
tool and its terminal state; the retry it is named for takes more than one item,
because the failure it forbids is a batch answering for the items it managed and
re-deciding the ones it had already done. That is #41's, and this is it.

**The order count is read from the database and not from the wire.** A refused
item answers with a reason and no order, so a response cannot distinguish *no
second order* from *a second order that was not shown*. There is no tool that
lists a purchase order — ADR-0002 cut every read tool that demonstrated no
authorization behaviour — so the fact lives one layer down and is read there.
"""

from collections.abc import Iterator
from typing import Any

import pytest

import fixtures
import rpc
from requisitions import raised_by
from tokens import mint

APPROVE = "approve_requisition"
GET = "get_requisition"

APPROVER = "tomas.weber"
"""CC-4100, `approver`. Decides both rows below, and decides them once."""

SUBMITTER = "priya.raman"
"""CC-4100, no ERP role. Raises the rows, so the submitter edge refuses nobody here."""

AMOUNT = "480.00"
"""Below the threshold, so nothing but the retry can be what refuses the second call.

A row above €5,000 would be refused for a second reason and a scenario that
passes for two reasons cannot say which one it tested.
"""


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Wipe and reload, so this module's orders are the only ones in the table."""
    fixtures.load()
    yield


def _decide(username: str, identifiers: list[str]) -> dict[str, Any]:
    """One `approve_requisition` call over the whole batch, as a JSON-RPC result."""
    return rpc.result(
        rpc.call_tool(
            APPROVE,
            {"ids": identifiers, "decision": "approve"},
            token=mint(username, ["erp.decide"]).access_token,
        )
    )


def _status(username: str, identifier: str) -> str:
    """What the requisition says about itself, read back through the named read."""
    result = rpc.result(
        rpc.call_tool(GET, {"id": identifier}, token=mint(username, ["erp.read"]).access_token)
    )

    assert result["isError"] is False, result
    status: str = result["structuredContent"]["requisition"]["status"]
    return status


def test_the_batch_is_two_rows_this_approver_may_decide() -> None:
    """The precondition, held by a test rather than by trust.

    A scenario asserting that a second approval was refused passes just as well
    against rows nobody could approve in the first place, at which point it
    asserts nothing. So: two rows, both submitted, both in the approver's own
    centre, both below the threshold, and neither raised by him.
    """
    batch = [raised_by(SUBMITTER, AMOUNT), raised_by(SUBMITTER, AMOUNT)]

    for identifier in batch:
        assert _status(APPROVER, identifier) == "submitted"
    assert fixtures.purchase_orders_for(*batch) == 0


def test_a_retried_batch_answers_already_decided_for_every_item_and_mints_nothing() -> None:
    """The scenario. Twice the same call, once the effect.

    The first call decides both rows and emits one order each. The second is
    byte-for-byte the same request, and every item comes back `already_decided`
    with the remedy `none` and both retry booleans false — because a decided row
    is decided for everybody, and no person and no token makes it decidable
    again.

    The count afterwards is the assertion the wire cannot make: two orders, one
    per requisition, unchanged by the retry.
    """
    batch = [raised_by(SUBMITTER, AMOUNT), raised_by(SUBMITTER, AMOUNT)]

    first = _decide(APPROVER, batch)
    retried = _decide(APPROVER, batch)

    assert first["isError"] is False, first
    assert [
        answer["requisition"]["status"] for answer in first["structuredContent"]["outcomes"]
    ] == [
        "approved",
        "approved",
    ]

    assert retried["isError"] is True
    assert retried["structuredContent"]["outcomes"] == [
        {
            "reason": "already_decided",
            "remedy": "none",
            "retry_identical_helps": False,
            "retry_as_other_person_helps": False,
        }
    ] * len(batch)

    assert fixtures.purchase_orders_for(*batch) == len(batch)
    for identifier in batch:
        assert _status(APPROVER, identifier) == "approved"


def test_a_partly_decided_batch_retries_into_one_answer_per_item() -> None:
    """The shape the retry actually arrives in, which is not all-or-nothing.

    A model retries when a result comes back marked in error, and a mixed batch
    is exactly that: one item refused and the rest decided. The retry therefore
    re-sends items that already went through, and what it gets is one answer per
    item — `already_decided` for the half that succeeded, and the original
    refusal, unchanged, for the half that did not.

    **Idempotency is per item and not per call.** A whole-call guard keyed on
    the request would answer the retry once and hide the item that is still
    decidable; here the item that was refused for its own reasons is still
    refused for them, and nothing about the retry made it decidable or made the
    others decidable again.
    """
    decidable = raised_by(SUBMITTER, AMOUNT)
    foreign = fixtures.identifiers_in("CC-4200")

    batch = [decidable, *sorted(foreign)]
    first = _decide(APPROVER, batch)
    retried = _decide(APPROVER, batch)

    assert first["isError"] is True
    assert first["structuredContent"]["outcomes"][0]["requisition"]["status"] == "approved"
    assert first["structuredContent"]["outcomes"][1]["reason"] == "not_found"

    answers = retried["structuredContent"]["outcomes"]
    assert len(answers) == len(batch)
    assert answers[0]["reason"] == "already_decided"
    assert answers[1]["reason"] == "not_found"
    assert fixtures.purchase_orders_for(*batch) == 1

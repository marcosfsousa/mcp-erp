"""What the identifier mint does at four digits, and what it does past them.

The one thing every write in the exhibit has in common: all three of them mint
their row's handle from `_next_identifier`, which #70 factored into a single
expression serving `requisition`, `purchase_order` and `invoice`. A defect there
is a defect in all three tables at once, and #84 found one — the pad truncated,
so the ten-thousandth row of any table minted a handle a row already held and the
table could take no further writes.

**It belongs here rather than in `tests/matrix/`.** What a table mints next does
not vary with the caller: the same submission by any Person with `erp.write`
produces the same next identifier, so there is no `(principal x tool x resource)`
to key it on. That is this directory's own dividing line — *what varies with the
caller is the matrix's, what the server declares regardless is ours*.

**Nothing here asserts the SQL.** The expression is a fragment interpolated into
three statements and a test that read its text would pass on a fragment that
padded to four and truncated, which is the defect. So the boundary is driven:
a table one row short of five figures, then a real write through the tool that
writes it, and the handle that came back is the assertion.

**The wipe is per test here, not per module.** ADR-0003 chose to wipe and reload
once rather than between rows, and every other write suite takes that as a
module-scoped reload — the reason it gives is that *each write row owns a fixture
outright, so no row can disturb another*. That premise is exactly what fails
here: what this module manipulates is the high-water mark all three tables mint
from, which no row owns and every row moves, so a test running after the
boundary test would mint from a table its neighbour left in another state.
Recorded as an amendment to ADR-0003 by #84.

`fixtures.ABSENT_IDENTIFIER` and `fixtures.ABSENT_ORDER` — absent for a whole run
everywhere else — are restored by `fixtures.at_the_ceiling` itself rather than by
that reload: it is a context manager, so their absence holds outside its block
whatever happens inside it, instead of resting on this module remembering to
reload (#112).
"""

import re
from collections.abc import Iterator

import pytest

import fixtures
import requisitions as raise_one
import rpc
from tokens import mint

APPROVE = "approve_requisition"
RECORD = "record_invoice"

AMOUNT = "480.00"
"""Below the approval threshold, so the chain below costs one role and no argument."""

SUBMITTER = "priya.raman"
"""CC-4100, `erp.write` and no ERP role at all. Raises the row the chain runs on."""

APPROVER = "ingrid.holm"
"""CC-4100, `unlimited_approver`. Decides it, which is what emits the order."""

RECORDER = "rafael.costa"
"""CC-4100, `invoice_clerk`, and not the approver — so the second edge stays clear."""

FOUR_DIGITS = re.compile(r"req_[0-9]{4}")
"""What a requisition's handle looks like below ten thousand.

The pad width written as an expectation rather than as a fragment of SQL. Four is
what the *Legible identifiers* deviation buys — a handle a reader can guess — and
#84 widened the field past 9999 without moving this.

Unanchored, and matched with `fullmatch` at its one use, which is what makes
`req_10000` fail it. A `match` would accept that string's first ten characters,
so a second caller wanting a *contains* test must not reach for this one.
"""


@pytest.fixture(autouse=True)
def requisitions() -> Iterator[None]:
    """Start every test from the generated fixtures, and leave them that way.

    Function-scoped, for the reason the module docstring gives: the high-water
    mark is what this module moves, so one test's leftovers are the next one's
    subject — a row minted by one shifts what the next mints from.

    **Not what restores the ceiling rows.** `fixtures.at_the_ceiling` is a
    context manager and reloads on its own way out, so `req_9999` and `po_9999`
    are gone before this fixture is reached. What is left for this to do is the
    ordinary per-test wipe, which is the whole of its job.
    """
    fixtures.load()
    yield
    fixtures.load()


def _submit() -> str:
    """Raise one requisition and name the handle it was minted.

    `requisitions.raised_by` rather than a call built here, on that module's own
    rule: raising a row as setup is what it was lifted above the test directories
    to serve, and this is the fourth caller of the three that moved it.
    """
    return raise_one.raised_by(SUBMITTER, AMOUNT)


def _approve(identifier: str) -> str:
    """Approve one requisition and name the order that came out.

    A one-item list, because `approve_requisition` is the batch and one outcome
    renders as the decision itself rather than under `outcomes` — which is what
    lets this read the order straight out of the result.

    Written here rather than beside `raised_by`, although
    `test_record_invoice.py::_approved` is the same two calls: that is two
    callers, and the rule the shared module states is that a helper moves up at
    three. A third will be the one to move it.
    """
    decided = rpc.result(
        rpc.call_tool(
            APPROVE,
            {"ids": [identifier], "decision": "approve"},
            token=mint(APPROVER, ["erp.decide"]).access_token,
        )
    )
    assert decided["isError"] is False, decided
    order: str = decided["structuredContent"]["purchase_order"]["id"]
    return order


def _record(order: str) -> str:
    """Bill one order and name the invoice that came out."""
    recorded = rpc.result(
        rpc.call_tool(RECORD, {"id": order}, token=mint(RECORDER, ["erp.write"]).access_token)
    )
    assert recorded["isError"] is False, recorded
    invoice: str = recorded["structuredContent"]["invoice"]["id"]
    return invoice


def test_a_handle_below_the_ceiling_is_padded_to_four_digits() -> None:
    """The rendering the exhibit has always produced, pinned before it is widened.

    #84's fix lets the number grow past four digits and must not move anything
    below that, because the committed fixture rendering and every identifier a
    reader has ever seen are four digits wide. Driving a submission against the
    loaded fixtures is the whole assertion: nothing there is near the ceiling, so
    what comes back is what came back before the fix.
    """
    assert FOUR_DIGITS.fullmatch(_submit())


def test_the_chain_mints_past_the_ceiling_on_all_three_tables() -> None:
    """Ten thousand, on `requisition`, `purchase_order` and `invoice` in one pass.

    Each table holds a row at `9999`, so each of the three writes is the one that
    crosses. They are driven as a chain rather than as three independent writes
    because that is the only way to reach the second and third mints at all —
    an order exists only where an approval emitted one, and an invoice only where
    an order was billed.

    **The handle is the whole assertion, and it is a sharper signal than the
    failure the defect produces in production.** Before the fix this minted
    `req_1000` — the pad truncating from the right — and a table that genuinely
    held ten thousand rows would already hold that handle, so the write failed on
    the primary key and every retry recomputed the same maximum and collided
    again. Three rows is enough to reach the boundary and not enough to reach the
    collision, which is the point: it catches the wrong handle directly, where a
    test that waited for a key violation would need ten thousand rows to say the
    same thing more slowly.

    Each handle is also carried forward as the next call's argument, so a mint
    that returned something the read path could not hydrate would fail here too.
    """
    with fixtures.at_the_ceiling():
        requisition = _submit()
        order = _approve(requisition)
        invoice = _record(order)

    assert requisition == "req_10000"
    assert order == "po_10000"
    assert invoice == "inv_10000"


def test_the_ceiling_rows_are_gone_even_when_the_block_raises() -> None:
    """What makes `fixtures.ABSENT_IDENTIFIER`'s absence structural rather than promised.

    The docstring on that constant tells every other suite the value never
    exists, and this module is the one exception. Before #112 the exception was
    held open by discipline — `at_the_ceiling` wrote and the fixture above
    reloaded — so a test that raised between them left `req_9999` in the table,
    and the next module to read it as *never existed* would have been reading a
    row.

    Raising deliberately is the whole assertion, because a block that ends
    normally cannot tell a context manager's exit from the caller remembering.
    Asserted inside this test rather than left to the fixture, for the same
    reason: the fixture reloads afterwards either way and would hide the answer.

    Counted through `fixtures.purchase_orders_for`, which reads the database.
    `fixtures.every_identifier` would not do: it derives from the committed
    rendering, so it answers what the fixtures *declare* rather than what the
    tables hold, and these three rows are in no rendering by design.
    """
    with pytest.raises(RuntimeError, match="deliberate"):
        with fixtures.at_the_ceiling():
            assert fixtures.purchase_orders_for(fixtures.ABSENT_IDENTIFIER) == 1
            raise RuntimeError("deliberate, to end the block the way a failure would")

    assert fixtures.purchase_orders_for(fixtures.ABSENT_IDENTIFIER) == 0

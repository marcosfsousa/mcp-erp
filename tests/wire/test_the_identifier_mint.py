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

**The wipe is per test here, not per module.** ADR-0003 chose a wipe per run and
every other write suite takes it, because rows a previous test left behind change
nothing those suites assert. This module is the exception by construction: what
it manipulates *is* the high-water mark the mint reads, so a test that ran after
the ceiling test would mint from a table one of its neighbours moved. It also
means `fixtures.ABSENT_IDENTIFIER` and `fixtures.ABSENT_ORDER` — absent for a
whole run everywhere else — are restored to absence before this module ends.
"""

import re
from collections.abc import Iterator

import pytest

import fixtures
import rpc
from tokens import mint

SUBMIT = "submit_requisition"
APPROVE = "approve_requisition"
RECORD = "record_invoice"

VENDOR = "Meridian Cloud Services"
"""One of the four names `submit_requisition` enumerates. Nothing here turns on which."""

AMOUNT = "480.00"
"""Below the threshold, so the chain below costs one role and no argument."""

DESCRIPTION = "Managed Kubernetes, annual"

SUBMITTER = "priya.raman"
"""CC-4100, `erp.write` and no ERP role at all. Raises the row the chain runs on."""

APPROVER = "ingrid.holm"
"""CC-4100, `unlimited_approver`. Decides it, which is what emits the order."""

RECORDER = "rafael.costa"
"""CC-4100, `invoice_clerk`, and not the approver — so the second edge stays clear."""

FOUR_DIGITS = re.compile(r"req_[0-9]{4}")
"""What a requisition's handle looks like below the ceiling, anchored end to end.

The pad width written as an expectation rather than as a fragment of SQL. Four is
what the *Legible identifiers* deviation buys — a handle a reader can guess —
and the fix for #84 widens the field past 9999 without moving this.
"""


@pytest.fixture(autouse=True)
def requisitions() -> Iterator[None]:
    """Start every test from the generated fixtures, and leave them that way.

    Function-scoped, for the reason the module docstring gives: the high-water
    mark is what this module moves, so one test's leftovers are the next one's
    subject. The trailing reload is what puts `req_9999` and `po_9999` back out
    of the tables before another module reads either as *never existed*.
    """
    fixtures.load()
    yield
    fixtures.load()


def _submit(username: str = SUBMITTER) -> str:
    """Raise one requisition and name the handle it was minted."""
    raised = rpc.result(
        rpc.call_tool(
            SUBMIT,
            {
                "vendor": VENDOR,
                "amount": AMOUNT,
                "currency": "EUR",
                "description": DESCRIPTION,
            },
            token=mint(username, ["erp.write"]).access_token,
        )
    )
    assert raised["isError"] is False, raised
    identifier: str = raised["structuredContent"]["requisition"]["id"]
    return identifier


def _approve(identifier: str, username: str = APPROVER) -> str:
    """Approve one requisition and name the order that came out.

    A one-item list, because `approve_requisition` is the batch and one outcome
    renders as the decision itself rather than under `outcomes` — which is what
    lets this read the order straight out of the result.
    """
    decided = rpc.result(
        rpc.call_tool(
            APPROVE,
            {"ids": [identifier], "decision": "approve"},
            token=mint(username, ["erp.decide"]).access_token,
        )
    )
    assert decided["isError"] is False, decided
    order: str = decided["structuredContent"]["purchase_order"]["id"]
    return order


def _record(order: str, username: str = RECORDER) -> str:
    """Bill one order and name the invoice that came out."""
    recorded = rpc.result(
        rpc.call_tool(RECORD, {"id": order}, token=mint(username, ["erp.write"]).access_token)
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
    fixtures.at_the_ceiling()

    requisition = _submit()
    order = _approve(requisition)
    invoice = _record(order)

    assert requisition == "req_10000"
    assert order == "po_10000"
    assert invoice == "inv_10000"

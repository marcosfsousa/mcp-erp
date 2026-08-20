"""The whole chain, one branch per row — the largest block in the table.

Ten rows, and between them every step of ADR-0006's fixed order fires at least
once: the scope gate, the role gate, row scoping, and both of this tool's
relationship rules in the order the `Action` declares them. Plus the terminal
state, which is not an authorization refusal at all and is answered only *after*
the chain permits — so a caller who may not decide a row learns nothing about
whether it has been decided.

Two rows are worth naming because neither is about a rule failing:

* `approve_refused_when_the_scope_carries_no_role` is the middle denial class. A
  `403` here would be a lie — it would instruct the client to acquire a scope it
  already holds, producing an identical token and an identical refusal — so it is
  a `-31010`, and it is reachable only because ADR-0007 gives Priya Raman
  `approver` in the realm and no ERP role at all.
* `approve_refuses_above_the_threshold_where_no_unlimited_approver_exists` is
  ADR-0003's deliberate hole. CC-4200 has nobody holding `unlimited_approver`, so
  this refusal truthfully reports `retry_as_other_person_helps: true` in a centre
  where no such person exists. **A remedy names a class of action, not an
  available human** — and this row is why that distinction is tested rather than
  described.

Each row owns its own fixture outright, so the two rows that approve cannot
disturb the eight that do not.
"""

from collections.abc import Iterator

import driver
import pytest
from driver import Row

import fixtures

TOOL = "approve_requisition"


@pytest.fixture(scope="module", autouse=True)
def rows() -> Iterator[None]:
    """Start from the fixtures, with the purchase orders reset to what they render.

    This module writes: two rows approve, and one names a requisition the
    rendering already carries as decided. The loader clears `invoice` and
    `purchase_order` before `requisition` and re-inserts all three, so what the
    tables hold at the first assertion is what the matrix declares and not what a
    previous run left.
    """
    fixtures.load()
    yield


@pytest.mark.parametrize("row", driver.rows_for(TOOL), ids=driver.name)
def test_the_decision_answers_what_the_row_declares(row: Row) -> None:
    """One principal deciding one row, and the answer the table expects."""
    driver.drive(row)

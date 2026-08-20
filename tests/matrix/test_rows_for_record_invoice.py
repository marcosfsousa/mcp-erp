"""The second separation edge, decided against the other entity.

Six rows. The resource is the **purchase order** — the thing acted against, never
the thing created — so a row here names an order and the invoice it would write
does not exist when the decision is taken.

Two of the six carry the edge itself, and they are the pair rather than either
alone: Ingrid Holm is refused on the order she approved, and Rafael Costa is
permitted on the same shape of order approved by someone else. A single row would
show a refusal without showing that the rule is about a **position on this
chain** rather than about the person.

**No row here expects `not_found` on a foreign partition, and that is the
organisation's shape rather than an omission.** Both holders of `invoice_clerk`
sit in CC-4100, so an order in another centre is unreachable by anyone who gets
past the role gate — which is exactly what ADR-0013 names this tool for: a
declaration that wrongly granted breadth on this write would ship green, and
review is the guard.
"""

from collections.abc import Iterator

import driver
import pytest

import fixtures
from mcp_erp.purchase_to_pay.fixtures import Row

TOOL = "record_invoice"


@pytest.fixture(scope="module", autouse=True)
def loaded_fixtures() -> Iterator[None]:
    """Start from the fixtures, with the invoices reset to what they render.

    One row expects `already_invoiced`, and the order it names is rendered
    already billed — so the refusal is a fact about the row rather than about
    whether an earlier assertion in this module happened to run first.
    """
    fixtures.load()
    yield


@pytest.mark.parametrize("row", driver.rows_for(TOOL), ids=driver.name)
def test_the_recording_answers_what_the_row_declares(row: Row) -> None:
    """One principal billing one order, and the answer the table expects."""
    driver.drive(row)

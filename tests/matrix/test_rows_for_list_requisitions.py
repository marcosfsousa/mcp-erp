"""What one principal discovers, asserted as set equality over the fixtures.

Four rows: the scope that is absent, the caller's own partition, another
partition, and the auditing role that reads all three. Set equality rather than
membership or a subset, because that is what makes the claim one — a subset
assertion passes on a handler that returns nothing, and a membership assertion
passes on one that returns everything.

The expected set is **computed from the fixtures** rather than written beside
the row, which is the correspondence ADR-0003 said would otherwise rot: every
write row added to the matrix adds a fixture, and every fixture changes what a
read row sees. A generator that emits them all can compute it; a human
maintaining it by hand cannot.

**Omission, not refusal.** A row scoped away is simply absent from the answer and
carries no reason anywhere — the named half of that contract belongs to
`get_requisition`, one file along.
"""

from collections.abc import Iterator

import driver
import pytest
from driver import Row

import fixtures

TOOL = "list_requisitions"


@pytest.fixture(scope="module", autouse=True)
def rows() -> Iterator[None]:
    """Wipe and reload the fixtures once before this module, never between rows.

    Nothing here writes, so the reload is about starting from a known set rather
    than about isolation: another module in this directory submits and approves,
    and set equality over *the fixtures* is only a claim if the fixtures are what
    the table holds.

    In the test module rather than in a `conftest.py`, for the reason the attack
    suite states: `tests/conftest.py` already exists and the types job runs over
    `tests/`, so a second file of that name is a duplicate module to mypy.
    """
    fixtures.load()
    yield


@pytest.mark.parametrize("row", driver.rows_for(TOOL), ids=driver.name)
def test_the_listing_returns_the_partitions_the_row_declares(row: Row) -> None:
    """One principal, and exactly the identifiers their partitions hold."""
    driver.drive(row)

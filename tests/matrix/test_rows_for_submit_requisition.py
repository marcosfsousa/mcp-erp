"""Submitting is gated by scope alone, and the partition is supplied rather than decided.

Three rows: the scope that is absent, and two people in two centres each getting
their **own** centre stamped on what they raise. The second pair is the claim —
`submit_requisition` takes no cost centre, so an out-of-partition write is
inexpressible rather than refused, and which centre a row lands in is decided by
who raised it.

**These rows carry no `given`**, because the resource is the thing acted against
and this tool acts against none: it creates one. They write, which is why this
module reloads before it runs and why the read rows live in files of their own.
"""

from collections.abc import Iterator

import driver
import pytest
from driver import Row

import fixtures

TOOL = "submit_requisition"


@pytest.fixture(scope="module", autouse=True)
def rows() -> Iterator[None]:
    """Start from the fixtures, so a submission is observably new.

    This module writes, so the reload is what keeps it from depending on whatever
    a previous module left behind. It still does not isolate rows between tests —
    ADR-0003 chose a wipe per run rather than per row, and the alternative it
    rejected is a test-only reset route on a server whose entire subject is
    authorization.
    """
    fixtures.load()
    yield


@pytest.mark.parametrize("row", driver.rows_for(TOOL), ids=driver.name)
def test_a_submission_lands_where_the_row_declares(row: Row) -> None:
    """One principal raising one requisition, charged where the table says."""
    driver.drive(row)

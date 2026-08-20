"""One named row, and the refusal that says nothing about why.

Five rows: the scope that is absent, a row the caller holds, a row in another
partition, an identifier no row carries, and the auditing role reading across
every partition.

The third and fourth are the pair that matters. **A resource named in the request
is refused, never omitted** — so both are a tool result marked in error carrying
`not_found`, and they reach it through layer 2's single return site, which is
what keeps the refusal from being an existence oracle. That the two answer
*byte-identically* is `row_probe_indistinguishable`'s claim and stays in the
attack suite; what is asserted here is that each takes the shape its reason
declares.
"""

from collections.abc import Iterator

import driver
import pytest
from driver import Row

import fixtures

TOOL = "get_requisition"


@pytest.fixture(scope="module", autouse=True)
def rows() -> Iterator[None]:
    """Wipe and reload the fixtures once before this module.

    Nothing here writes; the reload is what keeps this module from depending on
    whatever the writing modules beside it left behind.
    """
    fixtures.load()
    yield


@pytest.mark.parametrize("row", driver.rows_for(TOOL), ids=driver.name)
def test_the_named_read_answers_what_the_row_declares(row: Row) -> None:
    """One principal naming one row, and the answer the table expects."""
    driver.drive(row)

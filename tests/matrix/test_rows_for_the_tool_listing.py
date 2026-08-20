"""The listing's scope filter, one row per scope set, over the wire.

The five assertions #66 handed here from `tests/wire/test_tool_listing.py`. The
rule that moved them is the one that names the ninth job: an assertion whose
expected value **changes with the caller** is this table's; one the server makes
**identically to every caller** — `cacheScope`, the `ttlMs` cap, the declared
schemas, `listChanged: false` — stays there, and so does *the listing is a
function of the token and not of the person*, which asserts an invariance
**across** callers rather than a value that varies with one.

All five mint for Priya Raman, who holds no ERP role at all, so what she reaches
is the token's doing and nothing else. On the deciding row that is the whole
claim: the realm issues her `erp.decide`, the server refuses her at the role
gate, and she sees the tool anyway — because the filter reads granted scope
alone, and filtering on the intersection would collapse the `-31010` denial class
into an absence with no wire shape at all.

**This directory touches no database**, which is why the rows here take no
reload: the listing is a function of the token and of which tools are deployed,
and neither is a row in a table.
"""

import driver
import pytest

from mcp_erp.purchase_to_pay.fixtures import Row

TOOL = "tools/list"


@pytest.mark.parametrize("row", driver.rows_for(TOOL), ids=driver.name)
def test_the_listing_reaches_what_the_scope_set_declares(row: Row) -> None:
    """One scope set, and exact set equality over the names it reaches."""
    driver.drive(row)

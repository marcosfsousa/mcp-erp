"""Four requisitions, so that a listing has something to scope.

**This file is temporary and its replacement is already specified.** ADR-0003
splits the seed in two: the organisation is authored, and the per-row
requisitions are **generated from the decision matrix definition**, one fixture
owned outright by one row. That generator is #43's, and `matrix.yaml` does not
exist yet — so there is nothing to generate these from, and asserting set
equality against an empty table would assert nothing at all.

What is here is therefore the smallest set that makes `list_partition_scoped`
falsifiable, and no more: one cost centre with two rows, and the other two with
one each, so that *the caller's own partition*, *another partition* and *all
three* are three different answers. #43 deletes this file.

**The wipe is once per run, not between rows**, which is the shape ADR-0003
already chose. The alternative it rejected is worth restating because it is the
reason there is a loader here at all rather than a route: a test-only reset
endpoint would be *"the single most quotable finding a reviewer could hand
back"* on a server whose entire subject is authorization. A suite holding a
database credential is the lesser cost, and it stays on this side of the wire.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Final, NamedTuple

import psycopg

DATABASE_URL = os.environ.get(
    "MCP_ERP_DATABASE_URL",
    "postgresql://mcp_erp:not-a-secret-demo-password@localhost:5432/mcp_erp",
)
"""Postgres as the host reaches it, which Compose publishes on its usual port.

Not a secret and conspicuously so, on the same terms as the Cast's password: the
exhibit runs on the reader's machine and nowhere else, so there is nothing here
to leak.
"""


class Row(NamedTuple):
    """One seeded requisition, flat and literal.

    No defaults, no inheritance and no references to another row — the guardrail
    ADR-0003 put on the matrix's own `given` block, kept here so that this file
    cannot quietly become the thing that block is forbidden to become.
    """

    id: str
    cost_centre: str
    vendor: str
    amount: Decimal
    description: str
    submitted_by: str


ROWS: Final = (
    Row(
        "req_0001",
        "CC-4100",
        "ven_0001",
        Decimal("1200.00"),
        "40 ergonomic desk chairs",
        "tomas-weber",
    ),
    Row(
        "req_0002",
        "CC-4100",
        "ven_0003",
        Decimal("480.00"),
        "Quarterly window cleaning",
        "priya-raman",
    ),
    Row(
        "req_0003",
        "CC-4200",
        "ven_0002",
        Decimal("7500.00"),
        "Managed Kubernetes, annual",
        "yusuf-demir",
    ),
    Row("req_0004", "CC-4300", "ven_0004", Decimal("950.00"), "Trade stand signage", "mei-tanaka"),
)
"""Two centres of the three hold one row; CC-4100 holds two.

Every submitter raises against **their own** cost centre, because that is what
the domain makes inexpressible otherwise: `submit_requisition` takes no cost
centre and stamps the submitter's. A row that broke that would be data no tool
could have produced.
"""


def load() -> None:
    """Replace the requisition table's contents with :data:`ROWS`.

    Idempotent by deleting first, so a run that follows a run starts from the
    same place. Nothing else in the schema is touched: the organisation is
    loaded at boot from the seed's own rendering, and re-inserting it here would
    put a second author on rows the drift check already polices.
    """
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        # Ordered by what references what. Both descendant tables are empty
        # until the tools that write them exist, and clearing them anyway is
        # what keeps this loader correct when they do.
        cursor.execute("DELETE FROM invoice")
        cursor.execute("DELETE FROM purchase_order")
        cursor.execute("DELETE FROM requisition")
        cursor.executemany(
            """
            INSERT INTO requisition
                (id, cost_centre, vendor, amount, description, submitted_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [tuple(row) for row in ROWS],
        )
        connection.commit()


def identifiers_in(*cost_centres: str) -> set[str]:
    """The identifiers of the seeded rows charged to these cost centres.

    Derived from :data:`ROWS` rather than written out beside each assertion, so
    that adding a row cannot leave one expectation stale while the others move.
    """
    return {row.id for row in ROWS if row.cost_centre in cost_centres}


def every_identifier() -> set[str]:
    """Every seeded identifier — what breadth by role is supposed to return."""
    return {row.id for row in ROWS}

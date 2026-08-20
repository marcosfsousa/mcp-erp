"""Four requisitions, so that a listing has something to scope.

**Above the test directories, beside `rpc.py` and `tokens.py`.** It shipped
inside `tests/attack_suite/` with the one suite that needed it, and moved here
the moment a second directory did — which is the rule `tokens.py` already
states: shared tooling that lives in one artifact's directory becomes that
artifact's and gets copied by the next. `tests/conftest.py` is what puts this
directory on the import path, so `import seeded_requisitions` reads the same
from any of the five.

**This file is temporary and its replacement is already specified.** ADR-0003
splits the seed in two: the organisation is authored, and the per-row
requisitions are **generated from the decision matrix definition**, one fixture
owned outright by one row. That generator is #43's, and `matrix.yaml` does not
exist yet — so there is nothing to generate these from, and asserting set
equality against an empty table would assert nothing at all.

What is here is therefore the smallest set that makes `list_partition_scoped`
falsifiable, and no more: one cost centre with two rows, and the other two with
one each, so that *the caller's own partition*, *another partition* and *all
three* are three different answers. The same four rows serve
`row_probe_indistinguishable` unchanged — a named row in another centre is one
of these, and a row that never existed is any identifier past the last of them.
#43 deletes this file.

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


ABSENT_IDENTIFIER: Final = "req_9999"
"""An identifier in the right shape that no row carries, and none will.

The *never existed* half of `row_probe_indistinguishable`. Written out rather
than derived from :data:`ROWS`, because it has to stay absent for the whole run
and `submit_requisition` mints the next identifier after the highest that
exists — a value one past the last seeded row would be handed out by the fourth
submission of a suite. Nothing reaches four figures in a test run.
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


def purchase_orders_for(*identifiers: str) -> int:
    """How many purchase orders exist against these requisitions.

    The one question about a decision's effect that no tool answers: an order is
    emitted by approval and there is no tool that lists one, by ADR-0002's count
    of five. `double_approval_via_batch_retry` asserts that a retried batch
    *minted nothing*, and this is the only place that fact is readable — a
    refusal carries no order, so the wire cannot tell "no second order" from
    "a second order that was not shown".

    Here rather than in that suite for the reason this module exists at all: it
    is where a test-side database credential lives, and a second one is a second
    place for the address and the connection handling to come apart.
    """
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM purchase_order WHERE requisition_id = ANY(%s)",
            (list(identifiers),),
        )
        row = cursor.fetchone()

    assert row is not None
    count: int = row[0]
    return count


def identifiers_in(*cost_centres: str) -> set[str]:
    """The identifiers of the seeded rows charged to these cost centres.

    Derived from :data:`ROWS` rather than written out beside each assertion, so
    that adding a row cannot leave one expectation stale while the others move.
    """
    return {row.id for row in ROWS if row.cost_centre in cost_centres}


def every_identifier() -> set[str]:
    """Every seeded identifier — what breadth by role is supposed to return."""
    return {row.id for row in ROWS}

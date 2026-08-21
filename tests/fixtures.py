"""The seed's disposable half, as the suites read it and as the database takes it.

**Above the test directories, beside `rpc.py`, `tokens.py` and
`requisitions.py`**, on the rule `tokens.py` states: shared tooling that lives in
one artifact's directory becomes that artifact's and gets copied by the next.

It replaces `seeded_requisitions.py`, which shipped with #37 holding four
hand-written rows and said in its own docstring that #43 would delete it. This is
that deletion. What changed is the author: the rows are no longer written here,
they are **generated from `docs/decision-matrix/matrix.yaml`** by
`mcp_erp.purchase_to_pay.fixtures` and committed as a rendering, so a
hand-edited fixture is a `Seed renders clean` failure rather than a surprise.
ADR-0003 fixed that split before either half existed — *the organisation is
authored; the test data is generated*.

**What did not move is the credential.** ADR-0003 rejected a test-only reset
route — *"the single most quotable finding a reviewer could hand back"* on a
server whose entire subject is authorization — and accepted a suite holding a
database credential instead. So the loader is here, on this side of the wire, and
the generator in `src/` never opens a socket.

**The wipe is once per module, not between rows.** Every suite that writes takes
a module-scoped reload, which is what makes the modules independent of each other
without isolating rows inside one — the shape ADR-0003 chose and the alternative
it named.

*Amended 2026-08-20 by #84.* **One suite reloads between its own tests**, and it
is the one whose subject is what the tables mint next. ADR-0003's reason for
wiping once is that each write row owns its fixture outright, so no row can
disturb another; the mint's high-water mark is the state that rule does not
cover, because no row owns it and every row moves it. That module — and
:func:`at_the_ceiling`, which only it calls — is the whole of the exception.

**Nothing is looked up by identifier.** The identifiers are ordinal and the
generator renumbers them when a row is inserted, so every suite here asks for a
fixture by the **matrix row that owns it** or by the partition it sits in. That
is what makes an inserted row a renumbered rendering and not a broken suite.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Final, NamedTuple

import psycopg

from mcp_erp.purchase_to_pay.approve_requisition import THRESHOLD
from mcp_erp.purchase_to_pay.fixtures import FIXTURE_RENDERING

DATABASE_URL = os.environ.get(
    "MCP_ERP_DATABASE_URL",
    "postgresql://mcp_erp:not-a-secret-demo-password@localhost:5432/mcp_erp",
)
"""Postgres as the host reaches it, which Compose publishes on its usual port.

Not a secret and conspicuously so, on the same terms as the Cast's password: the
exhibit runs on the reader's machine and nowhere else, so there is nothing here
to leak.
"""

REPO: Final = Path(__file__).resolve().parents[1]
"""The checkout, from this file's own location.

The same resolution `tokens.py` makes for the seed, and for the same reason: the
rendering is committed, so a suite reads it out of the tree it is running from
rather than out of an installed package's data directory.
"""


class Row(NamedTuple):
    """One generated requisition, flat and literal.

    ``row`` is the matrix row that owns it — the field that ties an ordinal
    identifier back to the expectation it exists for, and the one column the
    database never sees.
    """

    row: str
    id: str
    cost_centre: str
    vendor: str
    amount: Decimal
    description: str
    submitted_by: str
    status: str


class Order(NamedTuple):
    """One generated purchase order: what an approval in a `given` block emitted."""

    row: str
    id: str
    requisition_id: str
    approved_by: str
    status: str


class Bill(NamedTuple):
    """One generated invoice.

    ``Bill`` rather than ``Invoice`` because ``CONTEXT.md`` spends *invoice* on
    the entity layer 3 declares, and a second type of that name in the suites
    would be a second thing to mean by the word.
    """

    row: str
    id: str
    purchase_order_id: str
    recorded_by: str


def _rendering() -> dict[str, list[dict[str, str]]]:
    """The committed rendering, read once at import."""
    document: dict[str, list[dict[str, str]]] = json.loads(
        (REPO / FIXTURE_RENDERING).read_text(encoding="utf-8")
    )
    return document


_RENDERED: Final = _rendering()

ROWS: Final = tuple(
    Row(
        row=entry["row"],
        id=entry["id"],
        cost_centre=entry["cost_centre"],
        vendor=entry["vendor"],
        amount=Decimal(entry["amount"]),
        description=entry["description"],
        submitted_by=entry["submitted_by"],
        status=entry["status"],
    )
    for entry in _RENDERED["requisitions"]
)
"""Every generated requisition, in the order the matrix declares its rows."""

ORDERS: Final = tuple(
    Order(
        row=entry["row"],
        id=entry["id"],
        requisition_id=entry["requisition_id"],
        approved_by=entry["approved_by"],
        status=entry["status"],
    )
    for entry in _RENDERED["purchase_orders"]
)
"""Every generated purchase order — one per fixture whose `given` names an approver."""

INVOICES: Final = tuple(
    Bill(
        row=entry["row"],
        id=entry["id"],
        purchase_order_id=entry["purchase_order_id"],
        recorded_by=entry["recorded_by"],
    )
    for entry in _RENDERED["invoices"]
)
"""Every generated invoice — one per fixture whose order is already billed."""

ABSENT_IDENTIFIER: Final = "req_9999"
"""A requisition identifier in the right shape that no row carries, and none will.

The *never existed* half of `row_probe_indistinguishable`, and the resource every
matrix row with no `given` names on a tool that hydrates a requisition. Written
out rather than derived from :data:`ROWS`, because it has to stay absent for the
whole run and `submit_requisition` mints the next identifier after the highest
that exists — a value one past the last fixture would be handed out by the next
submission. Nothing reaches four figures in a test run.

**One module writes this value deliberately**, since #84: :func:`at_the_ceiling`
puts a row here so that the next write is the one crossing into five figures,
which is the only way to drive that boundary at all. It reloads before and after
every one of its tests, so the absence this docstring promises holds everywhere
else.
"""

ABSENT_ORDER: Final = "po_9999"
"""The same, one entity along, for the rows that hydrate a purchase order."""

ABSENT_INVOICE: Final = "inv_9999"
"""The same again, one entity further, and no suite hydrates one.

There is no tool that takes an invoice's identifier — ADR-0002's count of five
stops one entity short — so this names no resource and appears in no matrix row.
It is here because :func:`at_the_ceiling` writes all three tables and the third
value should be spelled where the other two are, rather than inline at its one
use as a fourth place the ceiling's number is written down.
"""


def load() -> None:
    """Replace the three generated tables' contents with the committed rendering.

    Idempotent by deleting first, so a run that follows a run starts from the
    same place. The organisation is untouched: it is loaded at boot from its own
    rendering, and re-inserting it here would put a second author on rows the
    drift check already polices.

    ``status`` is written explicitly on both tables rather than left to the
    column default. A fixture that is already decided, or already billed, is the
    only way `already_decided` and `already_invoiced` are reachable without a
    suite first performing the write that reaches them — which would make the
    refusal a fact about the suite's own ordering rather than about the row.
    """
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        # Ordered by what references what, in both directions: the deletes run
        # from the leaf inward and the inserts from the root outward.
        cursor.execute("DELETE FROM invoice")
        cursor.execute("DELETE FROM purchase_order")
        cursor.execute("DELETE FROM requisition")
        cursor.executemany(
            """
            INSERT INTO requisition
                (id, cost_centre, vendor, amount, description, submitted_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    row.id,
                    row.cost_centre,
                    row.vendor,
                    row.amount,
                    row.description,
                    row.submitted_by,
                    row.status,
                )
                for row in ROWS
            ],
        )
        cursor.executemany(
            """
            INSERT INTO purchase_order (id, requisition_id, approved_by, status)
            VALUES (%s, %s, %s, %s)
            """,
            [(order.id, order.requisition_id, order.approved_by, order.status) for order in ORDERS],
        )
        cursor.executemany(
            "INSERT INTO invoice (id, purchase_order_id, recorded_by) VALUES (%s, %s, %s)",
            [(bill.id, bill.purchase_order_id, bill.recorded_by) for bill in INVOICES],
        )
        connection.commit()


def at_the_ceiling() -> None:
    """Add one chain at ``9999`` to each of the three generated tables.

    The mint derives the next identifier from the highest that exists, so this is
    the whole of what it takes to put a table one write away from five figures —
    and it is the only way to reach that boundary in a test, since nothing in the
    tool set lets a caller choose an identifier.

    **One chain rather than three loose rows.** ``purchase_order`` references a
    requisition and ``invoice`` references an order, so a row in each table needs
    two references anyway; pointing them at each other means the three rows this
    writes reference nothing the rendering owns, and a suite reading the fixtures
    sees them as one extra chain rather than as three tables it has to reconcile.
    The identities on it are the requisition's own submitter, because no rule is
    ever applied to these rows — they exist to be the maximum and nothing else.

    **It leaves all three of :data:`ABSENT_IDENTIFIER`, :data:`ABSENT_ORDER` and
    :data:`ABSENT_INVOICE` present**, which is exactly the three values it writes.
    The first two are documented as absent for a whole run, so a caller must
    restore the tables with :func:`load` before any other module runs — see
    `tests/wire/test_the_identifier_mint.py`, which is the only caller and
    reloads between its own tests as well as after them.

    These are not Fixtures in `CONTEXT.md`'s sense and no matrix row owns one.
    They are hand-written into generated tables, which is what #43 removed from
    this module — the difference is that a Fixture exists to be *asserted
    against* and these exist to be the maximum, so nothing looks one up, nothing
    expects one, and they are gone before the next module reads the tables.
    """
    base = ROWS[0]
    with psycopg.connect(DATABASE_URL) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO requisition
                (id, cost_centre, vendor, amount, description, submitted_by, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'approved')
            """,
            (
                ABSENT_IDENTIFIER,
                base.cost_centre,
                base.vendor,
                base.amount,
                base.description,
                base.submitted_by,
            ),
        )
        cursor.execute(
            "INSERT INTO purchase_order (id, requisition_id, approved_by, status)"
            " VALUES (%s, %s, %s, 'invoiced')",
            (ABSENT_ORDER, ABSENT_IDENTIFIER, base.submitted_by),
        )
        cursor.execute(
            "INSERT INTO invoice (id, purchase_order_id, recorded_by) VALUES (%s, %s, %s)",
            (ABSENT_INVOICE, ABSENT_ORDER, base.submitted_by),
        )
        connection.commit()


def owned_by(row: str) -> Row:
    """The requisition one matrix row owns.

    Raises:
        AssertionError: No row of that name owns a fixture. A broken reference
            rather than an answer — a suite naming a row that does not exist is
            asserting against nothing, which is the failure mode a lookup by
            ordinal identifier would hide.
    """
    matches = [entry for entry in ROWS if entry.row == row]
    assert len(matches) == 1, f"{row!r} owns {len(matches)} requisitions"
    return matches[0]


def order_owned_by(row: str) -> Order:
    """The purchase order one matrix row's chain reached.

    Raises:
        AssertionError: The row owns no order.
    """
    matches = [entry for entry in ORDERS if entry.row == row]
    assert len(matches) == 1, f"{row!r} owns {len(matches)} purchase orders"
    return matches[0]


def identifiers_in(*cost_centres: str) -> set[str]:
    """The identifiers of the generated rows charged to these cost centres.

    Derived from :data:`ROWS` rather than written out beside each assertion, so
    that adding a matrix row cannot leave one expectation stale while the others
    move. This is the set every read row asserts equality over.
    """
    return {row.id for row in ROWS if row.cost_centre in cost_centres}


def every_identifier() -> set[str]:
    """Every generated identifier — what breadth by role is supposed to return."""
    return {row.id for row in ROWS}


def cost_centres() -> set[str]:
    """The centres the fixtures actually populate.

    Three of three is what makes an auditing role's breadth distinguishable from
    a principal who merely belongs to two, so the count is asserted rather than
    assumed by the suite that makes that claim.
    """
    return {row.cost_centre for row in ROWS}


def a_row_in(cost_centre: str) -> str:
    """One generated identifier in this cost centre, chosen by the data.

    The lowest, which is the first row the matrix declares there — so it is
    stable across runs and across insertions elsewhere in the table. Callers want
    *a row in that partition* and nothing else about it; a caller that wanted a
    particular one names its matrix row through :func:`owned_by`.

    Raises:
        AssertionError: No fixture is charged to that centre.
    """
    identifiers = identifiers_in(cost_centre)
    assert identifiers, f"no fixture is charged to {cost_centre!r}"
    return min(identifiers)


def a_decidable_row_in(cost_centre: str, *, not_raised_by: str) -> str:
    """One generated identifier in this centre that one approver can actually decide.

    Every rule that would refuse it for a reason other than the caller's
    partition is ruled out here rather than left to coincidence: it is still
    submitted, so the terminal state does not fire; it is at or below the
    threshold, so an ordinary `approver` clears the amount; and it was not raised
    by the person about to decide it, so the first separation edge does not fire
    either.

    That is a longer signature than a lookup by identifier, and it is the point.
    A suite that pinned `req_0002` would be asserting against an ordinal the
    generator renumbers; this asks for the row's *properties*, which are what the
    scenario is actually about.

    Args:
        cost_centre: The partition the row must sit in.
        not_raised_by: The subject about to decide it, excluded as a submitter.

    Raises:
        AssertionError: The centre holds no such fixture.
    """
    candidates = {
        row.id
        for row in ROWS
        if row.cost_centre == cost_centre
        and row.status == "submitted"
        and row.amount <= THRESHOLD
        and row.submitted_by != not_raised_by
    }
    assert candidates, f"{cost_centre!r} holds no fixture {not_raised_by!r} could decide"
    return min(candidates)


def purchase_orders_for(*identifiers: str) -> int:
    """How many purchase orders exist against these requisitions.

    The one question about a decision's effect that no tool answers: an order is
    emitted by approval and there is no tool that lists one, by ADR-0002's count
    of five. `double_approval_via_batch_retry` asserts that a retried batch
    *minted nothing*, and this is the only place that fact is readable — a
    refusal carries no order, so the wire cannot tell "no second order" from
    "a second order that was not shown".

    *Amended 2026-08-21 by #85.* **A second suite asks the same question of a
    concurrent pair rather than of a retry.**
    `tests/wire/test_approve_requisition.py` reads this for
    `test_two_simultaneous_decisions_on_one_requisition_mint_one_order`, which is
    the second assertion in that directory not made over HTTP and says so in its
    own README. Nothing about the question changed — an effect the tool set does
    not expose is still an effect the tool set does not expose — so this stayed
    one function rather than gaining a caller-shaped variant.

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

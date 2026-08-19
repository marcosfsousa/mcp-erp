"""Where the ERP's rows come from, and the one query the read path needs.

Layer 3's only input or output. It lives here rather than anywhere else in
`src/` because a database dependency in layer 2 would be a layer-2 implementation
the ejection suite cannot run — the principal directory is a committed file held
in memory for exactly that reason (ADR-0013).

**The query does not filter by cost centre, and that is the design.** Pushing the
partition into a ``WHERE`` clause would put row scoping in two places: one
equality check in :mod:`mcp_erp.authorization.policy` and one predicate in SQL,
with ``partition_bypass`` re-implemented beside it. The second copy is the
fail-open ADR-0013 named — *a handler that takes a whole-call permit and lists
every partition* — arriving by the opposite route, as a handler that scopes rows
without the chain ever being asked. So every candidate row is loaded and
:func:`~mcp_erp.authorization.policy.decide_item` decides each one.

The index the schema declares on ``requisition.cost_centre`` is therefore unused
today. It was written for the read path's one question and it stays correct; if
a later ticket ever pushes the predicate down, it will have to move the bypass
with it, and the index is what makes that a performance choice rather than a
rewrite.
"""

from decimal import Decimal
from typing import Protocol

from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool

from mcp_erp.purchase_to_pay.requisition import Requisition

_SELECT_ALL = """
    SELECT
        requisition.id,
        requisition.cost_centre,
        requisition.vendor,
        vendor.name,
        requisition.amount,
        requisition.currency,
        requisition.description,
        requisition.submitted_by,
        person.name,
        requisition.status
    FROM requisition
    JOIN vendor ON vendor.id = requisition.vendor
    JOIN person ON person.subject = requisition.submitted_by
    ORDER BY requisition.id
"""
"""Every requisition, with the two labels the ``{id, label}`` pairs need.

``ORDER BY`` is for the reader and for nothing else. No entity carries a
timestamp — ADR-0003 handed *when things happened* to the audit-trail work with
a blank page — so there is no meaningful chronological order to return, and no
test asserts this one: read rows assert **set equality** over returned
identifiers, because row scoping is a question of which rows come back and not
of the sequence they arrive in.
"""


class Requisitions(Protocol):
    """What the handler needs from a store, which is one method.

    A protocol rather than a concrete type, so the handler is written against
    what it uses. It is not an injection seam for a stub: the wire suites drive
    the real database, on ADR-0008's rule that a matrix row green in-process
    while the wire path goes unexercised is a test passing for the wrong reason.
    """

    async def all(self) -> tuple[Requisition, ...]:
        """Every requisition in the ERP, unscoped.

        Unscoped is the contract, not an omission: the caller is the policy
        chain, and a store that pre-filtered would be answering a question only
        layer 2 is allowed to answer.
        """
        ...


class PostgresRequisitions:
    """The shipped store, reading through a pool the composition root owns.

    The pool is a connection cache and not request state — it holds nothing
    about who called, so two replicas behind no sticky routing stay
    indistinguishable to a caller, which is the property map constraint `#5`
    exists to make falsifiable.
    """

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[TupleRow]]) -> None:
        """Hold the pool the lifespan opened."""
        self._pool = pool

    async def all(self) -> tuple[Requisition, ...]:
        """Read every requisition, with its vendor and submitter labels."""
        async with self._pool.connection() as connection:
            cursor = await connection.execute(_SELECT_ALL)
            rows = await cursor.fetchall()

        return tuple(
            Requisition(
                id=str(row[0]),
                cost_centre=str(row[1]),
                vendor=str(row[2]),
                vendor_name=str(row[3]),
                amount=Decimal(row[4]),
                currency=str(row[5]),
                description=str(row[6]),
                submitted_by=str(row[7]),
                submitter_name=str(row[8]),
                status=str(row[9]),
            )
            for row in rows
        )

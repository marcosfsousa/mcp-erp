"""Where the ERP's rows come from, and the three queries the tools need.

Layer 3's only input or output. It lives here rather than anywhere else in
`src/` because a database dependency in layer 2 would be a layer-2 implementation
the ejection suite cannot run — the principal directory is a committed file held
in memory for exactly that reason (ADR-0013).

**No query filters by cost centre, and that is the design.** Pushing the
partition into a ``WHERE`` clause would put row scoping in two places: one
equality check in :mod:`mcp_erp.authorization.policy` and one predicate in SQL,
with ``partition_bypass`` re-implemented beside it. The second copy is the
fail-open ADR-0013 named — *a handler that takes a whole-call permit and lists
every partition* — arriving by the opposite route, as a handler that scopes rows
without the chain ever being asked. So every candidate row is loaded and
:func:`~mcp_erp.authorization.policy.decide_item` decides each one.

That applies to :meth:`Requisitions.by_id` as much as to
:meth:`Requisitions.all`, and it is load-bearing there rather than merely
consistent. ``SELECT … WHERE id = %s AND cost_centre = %s`` is the removal the
``state_handle_hijack`` scenario names in the other direction, and it would make
the empty join and the foreign row converge **in SQL** instead of at layer 2's
single return site — the same answer today, reached by a mechanism no test in
``tests/authorization`` can see.

The index the schema declares on ``requisition.cost_centre`` is therefore unused
today. It was written for the read path's one question and it stays correct; if
a later ticket ever pushes the predicate down, it will have to move the bypass
with it, and the index is what makes that a performance choice rather than a
rewrite.
"""

from decimal import Decimal
from typing import Final, Protocol

from psycopg import AsyncConnection
from psycopg.rows import TupleRow
from psycopg_pool import AsyncConnectionPool

from mcp_erp.purchase_to_pay.requisition import Requisition

_COLUMNS = """
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
"""
"""One requisition's columns, with the two labels the ``{id, label}`` pairs need.

Written once because :func:`_as_requisition` reads them positionally, and three
statements selecting *nearly* the same list is how a positional read comes apart.
"""

_SELECT_ALL: Final = f"""
    SELECT {_COLUMNS}
    FROM requisition
    JOIN vendor ON vendor.id = requisition.vendor
    JOIN person ON person.subject = requisition.submitted_by
    ORDER BY requisition.id
"""
"""Every requisition, unscoped.

``ORDER BY`` is for the reader and for nothing else. No entity carries a
timestamp — ADR-0003 handed *when things happened* to the audit-trail work with
a blank page — so there is no meaningful chronological order to return, and no
test asserts this one: read rows assert **set equality** over returned
identifiers, because row scoping is a question of which rows come back and not
of the sequence they arrive in.
"""

_SELECT_ONE: Final = f"""
    SELECT {_COLUMNS}
    FROM requisition
    JOIN vendor ON vendor.id = requisition.vendor
    JOIN person ON person.subject = requisition.submitted_by
    WHERE requisition.id = %s
"""
"""One requisition by identifier, and by identifier **alone**.

The cost centre is deliberately absent from the predicate; see the module
docstring. A row in another partition is loaded and then refused by the chain,
which is what keeps the refusal a layer-2 property rather than a SQL one.
"""

_INSERT: Final = f"""
    WITH minted AS (
        INSERT INTO requisition (id, cost_centre, vendor, amount, currency, description,
                                 submitted_by)
        SELECT
            'req_' || lpad(
                (coalesce(max(substring(id from '[0-9]+$')::integer), 0) + 1)::text, 4, '0'
            ),
            %s, %s, %s, %s, %s, %s
        FROM requisition
        RETURNING *
    )
    SELECT {_COLUMNS}
    FROM minted AS requisition
    JOIN vendor ON vendor.id = requisition.vendor
    JOIN person ON person.subject = requisition.submitted_by
"""
"""Write one row, minting the next identifier, and read it back with its labels.

**The identifier is sequential and legible**, against a specification ``SHOULD``
— the normative register's *Legible identifiers* deviation, taken so that the
probe scenario can guess a foreign identifier rather than be handed one. So the
next one is derived from the highest that exists rather than drawn from a
sequence: a sequence would have to be re-synchronised every time the fixtures are
reloaded with explicit identifiers, and a loader that forgot would mint a
duplicate key on the first submission after it.

One statement rather than an insert followed by a select, so the row a caller is
shown is the row that was written and not a later read of the same identifier.
``status`` and the ``id`` are the server's; ``currency`` is passed rather than
left to the column default, because the caller stated it.
"""

_MINT_LOCK: Final = 0x726571
"""``req`` in ASCII, as an advisory lock key. One writer mints at a time.

The identifier above is read and written in one statement and that is still not
atomic: two transactions can both read the same maximum under read-committed
isolation and the loser gets a primary-key violation. Two replicas behind no
sticky routing is a property this exhibit **tests** (map constraint `#5`), so
concurrent submissions are a real shape rather than a hypothetical one. A
transaction-scoped advisory lock is one line and releases itself on commit or
rollback, where a table lock would serialise the reads as well.
"""


class Requisitions(Protocol):
    """What the handlers need from a store, which is three methods.

    A protocol rather than a concrete type, so the handlers are written against
    what they use. It is not an injection seam for a stub: the wire suites drive
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

    async def by_id(self, identifier: str) -> Requisition | None:
        """The requisition with this identifier, whoever it belongs to, or ``None``.

        The hydration a named read needs. Returning the foreign row rather than
        hiding it is what lets ``decide_item`` refuse it at the same return site
        the absent row reaches — the convergence is layer 2's to make, and a
        store that answered ``None`` for both would have made it here instead.
        """
        ...

    async def create(
        self,
        *,
        cost_centre: str,
        vendor: str,
        amount: Decimal,
        currency: str,
        description: str,
        submitted_by: str,
    ) -> Requisition:
        """Write one requisition and return it as written.

        ``cost_centre`` and ``submitted_by`` are the server's, resolved from the
        principal before this is called; the rest are the caller's. Keyword-only,
        because two adjacent identifier-shaped strings passed positionally is how
        a submitter ends up charged to a vendor.
        """
        ...


class PostgresRequisitions:
    """The shipped store, reading and writing through a pool the composition root owns.

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

        return tuple(_as_requisition(row) for row in rows)

    async def by_id(self, identifier: str) -> Requisition | None:
        """Read one requisition by identifier, without asking whose it is."""
        async with self._pool.connection() as connection:
            cursor = await connection.execute(_SELECT_ONE, (identifier,))
            row = await cursor.fetchone()

        return None if row is None else _as_requisition(row)

    async def create(
        self,
        *,
        cost_centre: str,
        vendor: str,
        amount: Decimal,
        currency: str,
        description: str,
        submitted_by: str,
    ) -> Requisition:
        """Mint an identifier and write the row, inside one transaction.

        Raises:
            RuntimeError: The insert returned nothing, which can only mean the
                statement stopped being an insert. Refused rather than returned
                as an empty row, so a broken query fails here instead of three
                assertions later.
        """
        async with self._pool.connection() as connection:
            await connection.execute("SELECT pg_advisory_xact_lock(%s)", (_MINT_LOCK,))
            cursor = await connection.execute(
                _INSERT,
                (cost_centre, vendor, amount, currency, description, submitted_by),
            )
            row = await cursor.fetchone()

        if row is None:
            raise RuntimeError("the requisition insert returned no row")
        return _as_requisition(row)


def _as_requisition(row: TupleRow) -> Requisition:
    """One database row as the entity, read positionally against :data:`_COLUMNS`."""
    return Requisition(
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

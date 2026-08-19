"""Where the ERP's rows come from, and the queries the tools need.

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

from mcp_erp.purchase_to_pay.purchase_order import Decided, PurchaseOrder
from mcp_erp.purchase_to_pay.requisition import Requisition

_COLUMNS: Final = """
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

_STATUSES: Final = {True: "approved", False: "rejected"}
"""What a decision writes, keyed on which way it went.

The two values the column's own ``requisition_status`` enum permits beside
``submitted``, written here so the statement above takes a status rather than a
verb — a decision is one update with one parameter, not two statements that could
drift apart.
"""

_DECIDE: Final = """
    UPDATE requisition
    SET status = %s
    WHERE id = %s AND status = 'submitted'
"""
"""Move one requisition to a terminal state, **if it is not in one already**.

``AND status = 'submitted'`` is what makes the terminal-state rule true rather
than usually true. The handler holds a row loaded a moment earlier, and a check
against that row is a check against what was true when it was read: two callers
deciding the same requisition at once would both pass it. The predicate here is
evaluated by the database against the row it is about to write, so exactly one of
the two updates matches and the loser is told ``already_decided`` — which is what
ADR-0002's promise that a retrying model cannot double-approve actually rests on.

No ``RETURNING``: the decided row is read back by :data:`_SELECT_ONE` inside the
same transaction, because ``RETURNING`` cannot join and the row a caller is shown
carries its vendor's and submitter's names.
"""

_INSERT_ORDER: Final = """
    WITH minted AS (
        INSERT INTO purchase_order (id, requisition_id, approved_by)
        SELECT
            'po_' || lpad(
                (coalesce(max(substring(id from '[0-9]+$')::integer), 0) + 1)::text, 4, '0'
            ),
            %s, %s
        FROM purchase_order
        RETURNING *
    )
    SELECT minted.id, minted.requisition_id, minted.approved_by, person.name, minted.status
    FROM minted
    JOIN person ON person.subject = minted.approved_by
"""
"""Emit the order an approval produces, minting its identifier the same way.

Sequential and legible for the same reason a requisition's is — the normative
register's *Legible identifiers* deviation — and derived from the highest that
exists rather than from a sequence, so reloading fixtures with explicit
identifiers cannot leave a sequence to mint a duplicate key.

``status`` and ``id`` are the server's; the cost centre is **not written at all**,
which is ADR-0003's correction to ADR-0002 expressed in the statement rather than
only in the schema.
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

_ORDER_MINT_LOCK: Final = 0x706F
"""``po`` in ASCII. The same argument as :data:`_MINT_LOCK`, on the other table.

A second key rather than the same one, because the two mints are independent: a
submission and an approval have no reason to wait for each other, and sharing a
key would serialise them for a race neither is in.
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

    async def decide(self, identifier: str, *, approve: bool, approved_by: str) -> Decided | None:
        """Move one requisition to a terminal state, and emit an order if approved.

        Returns ``None`` when the row was decided already — **the terminal-state
        rule, evaluated where the write happens.** A check against the row the
        handler loaded a moment earlier is a check against what was true when it
        was read, and two callers deciding at once would both pass it; the
        predicate is in the update, so exactly one of them wins.

        Authorization is not consulted here and must have been decided before this
        is called. The store answers *whether the row was still decidable*, which
        is a domain precondition rather than a decision about a caller.

        Args:
            identifier: The requisition to decide, already hydrated and permitted.
            approve: Approve it, or reject it. A rejection is equally terminal and
                emits nothing.
            approved_by: The approver's subject, from the principal. The caller
                supplies no identity, which is what makes the submitter rule a
                check against a position on the chain.

        Returns:
            What the decision produced, or ``None`` if there was nothing left to
            decide.
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

    async def decide(self, identifier: str, *, approve: bool, approved_by: str) -> Decided | None:
        """Decide one requisition and emit its order, inside one transaction.

        Three statements and one transaction, which is what makes the pair
        atomic: a requisition marked ``approved`` with no order beside it would be
        a chain with a missing link, and an order against a row still marked
        ``submitted`` would be one that could be minted twice.

        Raises:
            RuntimeError: The decided row could not be read back, or the order
                insert returned nothing. Both mean a statement stopped being what
                it says it is — refused here rather than three assertions later.
        """
        async with self._pool.connection() as connection:
            decided = await connection.execute(_DECIDE, (_STATUSES[approve], identifier))
            if decided.rowcount != 1:
                # Nothing matched, so the row was in a terminal state already.
                # Not an error and not an authorization refusal: the handler
                # turns it into `already_decided`, which is the domain's word.
                return None

            cursor = await connection.execute(_SELECT_ONE, (identifier,))
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError(f"the decided requisition {identifier!r} could not be read")
            requisition = _as_requisition(row)

            if not approve:
                return Decided(requisition=requisition, purchase_order=None)

            await connection.execute("SELECT pg_advisory_xact_lock(%s)", (_ORDER_MINT_LOCK,))
            cursor = await connection.execute(_INSERT_ORDER, (identifier, approved_by))
            order = await cursor.fetchone()

        if order is None:
            raise RuntimeError("the purchase order insert returned no row")
        return Decided(
            requisition=requisition,
            purchase_order=_as_purchase_order(order, label=requisition.description),
        )


def _as_purchase_order(row: TupleRow, *, label: str) -> PurchaseOrder:
    """One order row as the entity, read positionally against :data:`_INSERT_ORDER`.

    ``label`` comes from the requisition this transaction just decided rather than
    from a fourth join: the row is in hand, and joining back to it to read a
    column already held would be a second reading of the same fact.
    """
    return PurchaseOrder(
        id=str(row[0]),
        requisition_id=str(row[1]),
        requisition_label=label,
        approved_by=str(row[2]),
        approver_name=str(row[3]),
        status=str(row[4]),
    )


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

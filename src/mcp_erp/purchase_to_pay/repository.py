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

That applies to :meth:`Requisitions.by_id` and :meth:`PurchaseOrders.by_id` as
much as to :meth:`Requisitions.all`, and it is load-bearing there rather than
merely consistent. ``SELECT … WHERE id = %s AND cost_centre = %s`` is the removal the
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

from mcp_erp.purchase_to_pay.invoice import Invoice, Recorded
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


def _next_identifier(prefix: str) -> str:
    """The expression that mints one table's next identifier, for a prefixed handle.

    **The identifier is sequential and legible**, against a specification
    ``SHOULD`` — the normative register's *Legible identifiers* deviation, taken
    so that the probe scenario can guess a foreign identifier rather than be
    handed one. So the next one is derived from the highest that exists rather
    than drawn from a sequence: a sequence would have to be re-synchronised every
    time the fixtures are reloaded with explicit identifiers, and a loader that
    forgot would mint a duplicate key on the first write after it.

    **Written once because the argument is one argument.** Each of the three
    tables mints on exactly these terms, differing only in the prefix, and the
    expression is fiddly enough that three copies is three places for the pad
    width or the anchor to drift. The table is not a parameter: the expression
    reads ``id`` from whatever the enclosing statement selects from, so each
    caller's own ``FROM`` names it.

    **Four digits is a floor, not a ceiling, since #84.** ``lpad`` truncates from
    the right when its input is already wider than the target, so a fixed ``4``
    minted ``req_1000`` for the ten-thousandth row — a handle the table already
    held. The insert failed on the primary key, the retry recomputed the same
    maximum and collided again, and the table could take no further writes: a hard
    stop at 9999 that nobody chose, reported as a key violation that named no
    limit. Taking the width from the number itself removes that stop rather than
    moving it. Everything below 10000 is unchanged, which is what the committed
    fixture rendering rests on, and the row after ``req_9999`` is ``req_10000``.

    **The bound is now 2147483647 rows per table, and it is the cast's width that
    sets it.** ``::integer`` is int4, so the row after ``req_2147483647`` fails on
    the ``+ 1`` rather than on the key. The cast itself succeeds — verified
    against the running database, ``select '2147483647'::integer + 1`` answers
    ``ERROR: integer out of range`` — so a maintainer greps for an overflow and
    not for a cast that never fails. It is a different error at a number nobody
    chose, which is the shape of the defect above and not its recurrence only
    because the pad was reachable and this is not: the exhibit seeds seventeen
    requisitions and #84's own boundary test is the only thing here that has ever
    passed three figures.
    Widening to ``::bigint`` is one word and was left alone deliberately, because
    #84 put the ``substring`` and its cast out of scope. **Written down rather than
    fixed is the whole point** — the previous bound cost nothing to reach and was
    stated nowhere, and that, rather than its value, is what made it a defect.

    **Sorting stops agreeing with minting at the same boundary.** ``ORDER BY id``
    is lexical, so ``req_10000`` sorts before ``req_9999``. :data:`_SELECT_ALL` is
    the only statement that orders, its own docstring says that ordering is for
    the reader and for nothing else, and no test asserts it — so this is a cost
    accepted here rather than a defect deferred.

    The width is computed from the number, so the number is written once here and
    interpolated twice. Postgres folds the two identical aggregates into one, and
    a second literal copy would be the drift this helper exists to prevent.

    Args:
        prefix: The handle's leading token, without its separator.

    Returns:
        A SQL fragment, for interpolation into an ``INSERT … SELECT``. It carries
        no caller data — the only substitution is this literal — so it is not a
        parameterised value and must never become one.
    """
    number_expression = "(coalesce(max(substring(id from '[0-9]+$')::integer), 0) + 1)::text"
    return (
        f"'{prefix}_' || lpad({number_expression}, greatest(4, length({number_expression})), '0')"
    )


_INSERT: Final = f"""
    WITH minted AS (
        INSERT INTO requisition (id, cost_centre, vendor, amount, currency, description,
                                 submitted_by)
        SELECT
            {_next_identifier("req")},
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

The identifier comes from :func:`_next_identifier`, which carries the argument
for why it is shaped as it is.

One statement rather than an insert followed by a select, so the row a caller is
shown is the row that was written and not a later read of the same identifier.
``status`` and the ``id`` are the server's; ``currency`` is passed rather than
left to the column default, because the caller stated it.
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

_ORDER_COLUMNS: Final = """
    purchase_order.id,
    purchase_order.requisition_id,
    requisition.description,
    requisition.cost_centre,
    purchase_order.approved_by,
    person.name,
    purchase_order.status
"""
"""One purchase order's columns, with the three the entity needs from its joins.

Two of those three are the ``{id, label}`` pairs' labels. The third is
``requisition.cost_centre``, and reading it here is ADR-0003's *join away* made
literal: the order stores no centre, and the partition row scoping compares it on
is the requisition's. Written once because :func:`_as_purchase_order` reads them
positionally, and two statements selecting *nearly* the same list is how a
positional read comes apart.
"""

_ORDER_JOINS: Final = """
    JOIN requisition ON requisition.id = purchase_order.requisition_id
    JOIN person ON person.subject = purchase_order.approved_by
"""
"""The two joins :data:`_ORDER_COLUMNS` needs, written once for the same reason."""

_SELECT_ORDER: Final = f"""
    SELECT {_ORDER_COLUMNS}
    FROM purchase_order
    {_ORDER_JOINS}
    WHERE purchase_order.id = %s
"""
"""One purchase order by identifier, and by identifier **alone**.

The cost centre is selected and never predicated on, which is the same design
:data:`_SELECT_ONE` keeps one entity up: a row in another partition is loaded and
then refused by the chain, so the empty join and the foreign row converge at
layer 2's single return site rather than in SQL.
"""

_INSERT_ORDER: Final = f"""
    WITH minted AS (
        INSERT INTO purchase_order (id, requisition_id, approved_by)
        SELECT
            {_next_identifier("po")},
            %s, %s
        FROM purchase_order
        RETURNING *
    )
    SELECT {_ORDER_COLUMNS}
    FROM minted AS purchase_order
    {_ORDER_JOINS}
"""
"""Emit the order an approval produces, minting its identifier the same way.

``status`` and ``id`` are the server's; the cost centre is **not written at all**,
which is ADR-0003's correction to ADR-0002 expressed in the statement rather than
only in the schema. It is *read back* through the join above, which is the other
half of the same correction: the centre is a join away, and this is the join.

**It re-selects the shared column list rather than a shorter one of its own.**
Until #42 this statement was the only reader of an order and named its own five
columns, and the decided requisition supplied the label from the row already in
hand — a fourth join avoided. A second reader ended that: :data:`_SELECT_ORDER`
cannot have the row in hand, so it must join, and two statements feeding one
positional reader must select one list. The join bought here is what stops that
reader having two shapes to agree with.
"""

_RECORD: Final = """
    UPDATE purchase_order
    SET status = 'invoiced'
    WHERE id = %s AND status = 'open'
"""
"""Move one purchase order to its terminal state, **if it is not in one already**.

``AND status = 'open'`` is what makes ``already_invoiced`` true rather than
usually true, and the argument is :data:`_DECIDE`'s exactly: the handler holds a
row loaded a moment earlier, a check against that row is a check against what was
true when it was read, and two callers recording at once would both pass it. The
predicate is evaluated by the database against the row it is about to write, so
one of the two updates matches and the loser is told ``already_invoiced``.

The ``UNIQUE`` on ``invoice.purchase_order_id`` is the backstop rather than the
mechanism. It would refuse the second insert too, but as an integrity error about
a constraint the caller cannot see — where this answers with the domain's own
word.
"""

_INSERT_INVOICE: Final = f"""
    WITH minted AS (
        INSERT INTO invoice (id, purchase_order_id, recorded_by)
        SELECT
            {_next_identifier("inv")},
            %s, %s
        FROM invoice
        RETURNING *
    )
    SELECT minted.id, minted.purchase_order_id, minted.recorded_by, person.name
    FROM minted
    JOIN person ON person.subject = minted.recorded_by
"""
"""Write the invoice, minting its identifier on the same terms as the other two.

One join and not three. The label the ``{id, label}`` pair needs is the
requisition's description, and the order this transaction has just billed is
already in hand carrying it — so joining back through ``purchase_order`` to
``requisition`` would be a second reading of a column already held. That is the
argument :data:`_INSERT_ORDER` used to make and gave up when it acquired a second
reader; this statement has one reader and keeps it.

``id`` is the server's, and there is no ``status``: an invoice has no states to
be in. It exists or it does not, which is what makes the order's own status the
whole of the terminal-state rule.
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

_INVOICE_MINT_LOCK: Final = 0x696E76
"""``inv`` in ASCII. The third key, on the third table, for the third mint.

Three keys rather than one for the same reason there are two: a submission, an
approval and a recording are independent, and one shared key would serialise
every write on the server for a race no pair of them is in.
"""


class Requisitions(Protocol):
    """What the requisition handlers need from a store, which is four methods.

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


class PurchaseOrders(Protocol):
    """What ``record_invoice``'s handler needs from a store, which is two methods.

    A second protocol rather than two more methods on :class:`Requisitions`,
    because a handler is written against what it uses and this one uses no
    requisition at all. It also makes :func:`~mcp_erp.purchase_to_pay.handlers.load`
    honest: that step is parameterised on the entity it hydrates, and the two
    protocols are what fix which entity each of its callers gets.

    The concrete stores share a pool and nothing else. Neither holds anything
    about who called.
    """

    async def by_id(self, identifier: str) -> PurchaseOrder | None:
        """The order with this identifier, whoever it belongs to, or ``None``.

        Unscoped for the same reason :meth:`Requisitions.by_id` is: the foreign
        row is returned rather than hidden, so ``decide_item`` refuses it at the
        same return site the absent row reaches.
        """
        ...

    async def bill(self, identifier: str, *, recorded_by: str) -> Recorded | None:
        """Bill one purchase order, and write the invoice that bills it.

        **``bill`` rather than ``record_invoice``**, on the rule
        :meth:`Requisitions.decide` already keeps: a store method is named for
        what the store does to the entity it owns, never for the tool that calls
        it. ``decide`` sits under ``approve_requisition`` and ``create`` under
        ``submit_requisition`` for the same reason — a store that wore a tool's
        name would read as though it knew what a caller was allowed to do, which
        is the one thing it must not know.

        The verb is ``CONTEXT.md``'s own — an invoice is *"the record that a
        purchase order has been billed"*. The word is barred as a **noun** for
        that record and is the right verb for this action.

        Returns ``None`` when the order was invoiced already — **the
        terminal-state rule, evaluated where the write happens**, on the same
        terms as :meth:`Requisitions.decide`.

        Authorization is not consulted here and must have been decided before
        this is called. The store answers *whether the order was still
        billable*, which is a domain precondition rather than a decision about a
        caller.

        Args:
            identifier: The order to bill, already hydrated and permitted.
            recorded_by: The recorder's subject, from the principal. The caller
                supplies no identity, which is what makes the second separation
                edge a check against a position on the chain.

        Returns:
            What the recording produced, or ``None`` if there was nothing left
            to bill.
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
            # The caller's word is a verb and the column's is a state, which are
            # two vocabularies rather than one written twice. This is the whole
            # of the translation, and it lives here because the column's values
            # are the store's to know.
            decided = await connection.execute(
                _DECIDE, ("approved" if approve else "rejected", identifier)
            )
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

            # **Inside the block, and that is the point of the claim above.**
            # Raised after it, the update has already committed and the refusal
            # ships exactly the missing link this docstring says is impossible:
            # a requisition marked `approved` with no order beside it. Here the
            # exception leaves the transaction, so nothing is written at all.
            if order is None:
                raise RuntimeError("the purchase order insert returned no row")

            return Decided(requisition=requisition, purchase_order=_as_purchase_order(order))


class PostgresPurchaseOrders:
    """The shipped order store, over the same pool the requisition store holds.

    A second instance rather than a second pool: the pool is a connection cache
    and holds nothing about who called, so sharing it costs no isolation and
    buys one place where connection limits are configured.
    """

    def __init__(self, pool: AsyncConnectionPool[AsyncConnection[TupleRow]]) -> None:
        """Hold the pool the lifespan opened."""
        self._pool = pool

    async def by_id(self, identifier: str) -> PurchaseOrder | None:
        """Read one order by identifier, without asking whose it is."""
        async with self._pool.connection() as connection:
            cursor = await connection.execute(_SELECT_ORDER, (identifier,))
            row = await cursor.fetchone()

        return None if row is None else _as_purchase_order(row)

    async def bill(self, identifier: str, *, recorded_by: str) -> Recorded | None:
        """Bill one order and write its invoice, inside one transaction.

        Three statements and one transaction, which is what makes the pair
        atomic: an order marked ``invoiced`` with no invoice beside it would be
        a chain with a missing link, and an invoice against an order still
        marked ``open`` would be one that could be written twice.

        Raises:
            RuntimeError: The billed order could not be read back, or the
                invoice insert returned nothing. Both mean a statement stopped
                being what it says it is — refused here rather than three
                assertions later, and refused **inside** the transaction, so the
                update leaves nothing behind.
        """
        async with self._pool.connection() as connection:
            recorded = await connection.execute(_RECORD, (identifier,))
            if recorded.rowcount != 1:
                # Nothing matched, so the order was billed already. Not an error
                # and not an authorization refusal: the handler turns it into
                # `already_invoiced`, which is the domain's word.
                return None

            cursor = await connection.execute(_SELECT_ORDER, (identifier,))
            row = await cursor.fetchone()
            if row is None:
                raise RuntimeError(f"the billed purchase order {identifier!r} could not be read")
            order = _as_purchase_order(row)

            await connection.execute("SELECT pg_advisory_xact_lock(%s)", (_INVOICE_MINT_LOCK,))
            cursor = await connection.execute(_INSERT_INVOICE, (identifier, recorded_by))
            written = await cursor.fetchone()

            # Inside the block, so the exception leaves the transaction and the
            # update above is never committed. Raised after it, the refusal
            # would ship the missing link this docstring says is impossible.
            if written is None:
                raise RuntimeError("the invoice insert returned no row")

            return Recorded(
                purchase_order=order,
                invoice=_as_invoice(written, label=order.requisition_label),
            )


def _as_purchase_order(row: TupleRow) -> PurchaseOrder:
    """One order row as the entity, read positionally against :data:`_ORDER_COLUMNS`."""
    return PurchaseOrder(
        id=str(row[0]),
        requisition_id=str(row[1]),
        requisition_label=str(row[2]),
        cost_centre=str(row[3]),
        approved_by=str(row[4]),
        approver_name=str(row[5]),
        status=str(row[6]),
    )


def _as_invoice(row: TupleRow, *, label: str) -> Invoice:
    """One invoice row as the entity, read positionally against :data:`_INSERT_INVOICE`.

    ``label`` comes from the order this transaction just billed rather than from
    two further joins: the row is in hand carrying the requisition's description,
    and joining back through it to read a column already held would be a second
    reading of the same fact.
    """
    return Invoice(
        id=str(row[0]),
        purchase_order_id=str(row[1]),
        purchase_order_label=label,
        recorded_by=str(row[2]),
        recorder_name=str(row[3]),
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

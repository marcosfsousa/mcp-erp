"""The handlers — the largest thing ejection deletes.

A handler takes a ``Principal`` and parsed arguments, calls the chain, and yields
a domain outcome or a refused ``Decision``. It never returns anything
protocol-shaped: no status code, no JSON-RPC error, no tool result. Layer 1 holds
the adapters and renders what comes back, keyed on the refusal's shape rather
than on its grounds (ADR-0013).

**Choosing the entry point is a handler obligation, and no signature closes it.**
Layer 2 splits ``decide_call`` from ``decide_item`` so a whole-call permit cannot
be *used* as an item permit, but a handler that calls only the first and returns
every row type-checks cleanly and fails open. That residual is structurally
untestable in ``tests/authorization/`` — handlers are layer 3, and that directory
survives ejection precisely by having none — so its falsifiers are at the wire,
in ``list_partition_scoped`` and ``row_probe_indistinguishable``.

**All three entry points are exercised here, one per handler**, which is what
makes the split visible in one file:

=======================  ====================  =========================================
Handler                  Entry point           Why it stops there
=======================  ====================  =========================================
``list_requisitions``    both                  a call gate, then a decision per row
``get_requisition``      ``decide_item``       one named row, hydrated before deciding
``submit_requisition``   ``decide_call``       no resource at all; the partition is ours
``approve_requisition``  both                  a call gate, then a decision per named row
``record_invoice``       ``decide_item``       one named row, of the other entity
=======================  ====================  =========================================

*Amended 2026-08-20 by #41, which made ``approve_requisition`` a batch.* It
stopped at ``decide_item`` while it decided one row, and a batch cannot:
``role_missing`` is a ``-31010``, a JSON-RPC error is the *response* rather than a
line inside one, and a handler reaching that refusal once per item would hand
layer 1 N answers it has no way to render. So the call gate runs once, ahead of
the items — which is ADR-0002's *caller-level refusals are whole-call; item-level
refusals are per-item*, arriving as a structural obligation rather than as
tidiness.

*Extended 2026-08-20 by #42, which added the last row.* ``record_invoice`` stops
at ``decide_item``, and that is the obligation above holding rather than being
skipped: it is not a batch, because ADR-0002's *Five tools* gives the list to
``approve_requisition`` alone. One item is one outcome, so the gate that has to
run once and the chain that has to run per item are the same call — which is the
degenerate case ADR-0002 says a single-item call is, not an exception to it.

**Hydration is a named step and it is shared.** :func:`load` is ADR-0013's
``load(action, arguments) -> Resource | None``, called by the three handlers that
decide against a named row and by nothing else. It is a step rather than a
collaborator of the policy function, which takes none — and it is one function
rather than three identical pairs of lines, so *the handler passes the store's
answer straight through* is a property of one place.

**The step selects an entity, and the type checker is what enforces the choice.**
``load`` is parameterised on the resource its store answers with, so
``hydrate(ACTION, arguments)`` type-checks only when the action was declared
against that same entity — hydrating a requisition for an action decided against
a purchase order is a red types job rather than a refusal nobody sees. That is
what ADR-0013 kept the ``action`` parameter for, and #42 is the call it named.

**An argument a schema forbade raises ``UnusableArgument``.** That is not a
refusal: nothing was authorized or denied, and giving it a ``Reason`` would amend
a closed vocabulary for a spelling mistake. Layer 1 renders it as *invalid
params*, which is what the protocol says about a request it cannot act on.

*Amended by #82, which found the catch on the other side of that sentence.* The
type is **layer 2's**, where it was the standard library's ``ValueError``. The
argument for ``ValueError`` was that a handler signals with it without importing
anything layer 1 owns, and layer 2 satisfies that as well — ``Action``,
``Decision`` and ``Principal`` all arrive from there already. What ``ValueError``
could not satisfy is the other end: layer 1 wraps a handler's *whole iteration*,
the store is awaited inside it, and a type the standard library shares with every
library below made any failure down there answer *the arguments are not ones the
declared schema permits*. A name only a handler raises is what keeps the claim
true.

The boundary is untouched — layers 1 and 3 still import nothing from each other,
which is why the name could not live here.
"""

import re
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from decimal import Decimal
from typing import Any, Protocol

from mcp_erp.authorization import (
    Action,
    Decision,
    Principal,
    Resource,
    UnusableArgument,
    decide_call,
    decide_item,
)
from mcp_erp.purchase_to_pay import vendors
from mcp_erp.purchase_to_pay.approve_requisition import ACTION as APPROVE_REQUISITION
from mcp_erp.purchase_to_pay.approve_requisition import APPROVE, DECISIONS, MAXIMUM_BATCH
from mcp_erp.purchase_to_pay.get_requisition import ACTION as GET_REQUISITION
from mcp_erp.purchase_to_pay.list_requisitions import ACTION as LIST_REQUISITIONS
from mcp_erp.purchase_to_pay.reasons import ALREADY_DECIDED, ALREADY_INVOICED
from mcp_erp.purchase_to_pay.record_invoice import ACTION as RECORD_INVOICE
from mcp_erp.purchase_to_pay.repository import PurchaseOrders, Requisitions
from mcp_erp.purchase_to_pay.submit_requisition import ACTION as SUBMIT_REQUISITION
from mcp_erp.purchase_to_pay.submit_requisition import AMOUNT_PATTERN, CURRENCY

Handler = Callable[[Principal, Mapping[str, Any]], AsyncIterator[Mapping[str, Any] | Decision]]
"""The shape layer 1 calls, written here as well as there.

Stated twice rather than imported, for the same reason the seed's path is: the
two packages import nothing from each other, and a shared alias would have to
live in layer 2 — which would then hold a type describing how layer 1 renders.
The composition root is where the two spellings meet, and a disagreement between
them fails the types job there.
"""


class ByIdentifier[R: Resource](Protocol):
    """The half of a store hydration uses: one row by identifier, or nothing.

    Narrower than either store protocol on purpose. :func:`load` is written
    against what it uses, and what it uses is one method — which is also what
    lets one function serve two entities without knowing that either exists.
    """

    async def by_id(self, identifier: str) -> R | None:
        """The row with this identifier, whoever it belongs to, or ``None``."""


type Load[R: Resource] = Callable[[Action[R], Mapping[str, Any]], Awaitable[R | None]]
"""ADR-0013's hydration step: ``load(action, arguments) -> Resource | None``.

The parameters are the ADR's, and the store is bound by the factory below rather
than passed — which is what makes this a *step* rather than a collaborator. The
policy function takes none, so a resource cannot arrive any way but pre-loaded.

**``action`` selects the entity, through the type rather than through a branch.**
It is still not *read*, and #40 said it was kept because *"the resource an action
is decided against is a property of the action"*. #42 is the call that made that
concrete: ``R`` is fixed by the store the factory binds, so passing an
``Action[Requisition]`` to a step built over the purchase orders does not
type-check. The alternative — one step that inspects the action at run time and
picks a store — would put a table of tools inside the layer whose whole point is
that a tool's identity is its module.
"""


def load[R: Resource](store: ByIdentifier[R]) -> Load[R]:
    """Build the hydration step over a store.

    A factory for the same reason the handlers are: the store is the composition
    root's to own, and hydration is a layer-3 step that reaches a database.

    Returns:
        The step, in ADR-0013's shape, hydrating whichever entity this store
        answers with.
    """

    async def loaded(action: Action[R], arguments: Mapping[str, Any]) -> R | None:
        """The row this action is decided against, or nothing at all.

        **Loaded by identifier alone, whoever it belongs to.** The partition is
        deliberately absent from the query: pushing it down would make the empty
        join and the foreign row converge *in SQL* rather than at layer 2's
        single return site, which is the same answer reached by a mechanism no
        test in ``tests/authorization`` can see.

        The result — ``None`` included — is what a handler hands to
        ``decide_item``. That is what makes a handler unable to tell an absent
        row from a foreign one: it never looks.

        Raises:
            UnusableArgument: No ``id`` was named, or it was not a string. Distinct
                from ``not_found`` on purpose — nothing was named, so nothing was
                looked for, and answering *not found* would claim a search that
                did not happen.
        """
        identifier = arguments.get("id")
        if not isinstance(identifier, str):
            raise UnusableArgument("'id' must be a string")

        return await store.by_id(identifier)

    return loaded


def list_requisitions(requisitions: Requisitions) -> Handler:
    """Build the ``list_requisitions`` handler over a store.

    A factory rather than a module-level function, because the store is the
    composition root's to own — the handler is the thing layer 1 calls, and
    layer 1 must not learn that a database exists.

    Returns:
        The handler, in the shape layer 1's registry declares.
    """

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """Every requisition in the caller's partition, and no others.

        ``arguments`` is unused and is not vestigial: the input schema declares
        no properties, because a filter here would either change no authorization
        decision or leak which cost centres exist. The parameter is the shape
        every handler has.

        **Two entry points, in the order the contract requires.**
        :func:`~mcp_erp.authorization.policy.decide_call` answers the
        caller-level question once — a refusal that depends on the caller cannot
        ride in a per-item result, because a listing is one call — and then every
        candidate row goes through
        :func:`~mcp_erp.authorization.policy.decide_item`, which is where row
        scoping and the auditing bypass are actually evaluated.

        **Omission, not refusal.** A resource discovered by listing is omitted; a
        resource named in the request is refused. So a row the chain declines is
        simply absent here, and there is no per-row reason anywhere in the
        result — the caller cannot learn that a row exists in another partition,
        which is the same non-disclosure ``get_requisition``'s ``not_found``
        keeps for named rows.
        """
        call = decide_call(principal, LIST_REQUISITIONS)
        if call.reason is not None:
            yield Decision(reason=call.reason)
            return

        rows = await requisitions.all()
        visible = [row for row in rows if decide_item(principal, LIST_REQUISITIONS, row).permitted]

        # One outcome containing many rows, which is why a list tool never
        # reaches layer 1's fold: result rows are not outcomes.
        yield {"requisitions": [row.as_row() for row in visible]}

    return handler


def get_requisition(requisitions: Requisitions) -> Handler:
    """Build the ``get_requisition`` handler over a store.

    Returns:
        The handler, in the shape layer 1's registry declares.
    """
    hydrate = load(requisitions)

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """One named requisition, or the refusal that says nothing about why.

        **Hydrate, then decide, and pass the result straight through.**
        :func:`load` answers with the row or with ``None``, and that answer goes
        to :func:`~mcp_erp.authorization.policy.decide_item` untouched. That is
        what makes the empty join and the foreign row converge on layer 2's
        single return site instead of on a branch here: this handler cannot tell
        the two apart, because it never looks.

        Raises:
            UnusableArgument: No ``id`` was named, or it was not a string. Raised by
                the hydration step, and distinct from ``not_found`` on purpose —
                nothing was named, so nothing was looked for, and answering *not
                found* would claim a search that did not happen.
        """
        resource = await hydrate(GET_REQUISITION, arguments)
        decision = decide_item(principal, GET_REQUISITION, resource)
        if decision.reason is not None:
            yield decision
            return

        # Reachable only on a permit, and a permit means the chain saw a row.
        assert resource is not None
        yield {"requisition": resource.as_row()}

    return handler


def submit_requisition(requisitions: Requisitions) -> Handler:
    """Build the ``submit_requisition`` handler over a store.

    Returns:
        The handler, in the shape layer 1's registry declares.
    """

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """Raise a requisition against the caller's own cost centre.

        **One entry point, because there is no resource.** Submitting is
        scope-only, so :func:`~mcp_erp.authorization.policy.decide_call` is the
        whole of the decision — and the partition is not decided at all. It is
        *supplied*, from the principal the directory resolved, which is what
        makes an out-of-partition write inexpressible rather than refused.

        The chain runs **before** the store is touched, so a refused call writes
        nothing. That ordering is the write path's half of fail-closed: a row
        minted and then refused would still have consumed an identifier.

        Raises:
            UnusableArgument: An argument the input schema forbade — an unknown vendor,
                a currency that is not the one legal value, or an amount that is
                not a positive decimal.
        """
        call = decide_call(principal, SUBMIT_REQUISITION)
        if call.reason is not None:
            yield Decision(reason=call.reason)
            return

        written = await requisitions.create(
            # The principal's, never the caller's. There is no argument to
            # prefer over it, which is the point of the schema having none.
            cost_centre=principal.partition,
            submitted_by=principal.subject,
            vendor=vendors.identifier_for(_string(arguments, "vendor")),
            amount=_amount(arguments),
            currency=_currency(arguments),
            description=_string(arguments, "description"),
        )

        yield {"requisition": written.as_row()}

    return handler


def approve_requisition(requisitions: Requisitions) -> Handler:
    """Build the ``approve_requisition`` handler over a store.

    Returns:
        The handler, in the shape layer 1's registry declares.
    """
    hydrate = load(requisitions)

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """Decide every requisition the call names, and emit the orders approvals produce.

        **One outcome per item named in the request** — permit or refusal, never
        a silent drop. That is the invariant layer 1's fold rests on, and it is a
        property of this loop: the items come from the caller's list, every one
        of them is answered, and nothing is filtered out on the way.

        **The call gate runs once, ahead of the items.** A refusal that depends
        on the caller replaces the whole response, so it is answered before the
        first row is looked at — and it *must* be, because ``role_missing`` is a
        JSON-RPC error and there is no rendering for one inside a result body
        (ADR-0002). Then the whole chain runs per item, which re-runs the two
        caller-level steps: the deliberate N+1 layer 2 documents, and what keeps
        the fixed order in one implementation.

        **The resource is hydrated per item and it is the requisition** — the
        thing acted against. The purchase order does not exist yet, and the chain
        never sees one. The hydration step's answer goes straight to
        :func:`~mcp_erp.authorization.policy.decide_item`, ``None`` included, so
        a row in another partition and a row that was never there converge on
        layer 2's single return site exactly as they do on the read path.

        **Authorization first, then the row's own state.** ``already_decided`` is
        answered only after the chain permits, which is what stops it being an
        existence oracle: a caller who may not decide this row learns nothing
        about whether it has been decided. And the terminal check is the write
        itself rather than a test against the row loaded a moment ago, because a
        check that is not the write is a race two callers both pass — which is
        also what makes an item named twice in one list answer once and refuse
        once, rather than being de-duplicated by anything here.

        **The chain runs before the rest of the arguments are read**, which is
        the order ``submit_requisition`` already keeps: a caller the chain
        refuses is answered without their other arguments being looked at, and a
        refused call cannot be told apart from a refused call that also had a
        typo in it. The identifiers are the exception and have to be, because
        hydration cannot happen without them — and ``decision`` is read per item,
        after that item's own permit, so the ordering holds per item as well as
        per call.

        **The consequence is that a call with nothing decidable in it never reads
        ``decision`` at all**, so an unknown value there answers with the
        refusals rather than with ``-32602``. That is the ordering rule doing
        exactly what it says rather than a hole in the enum: the alternative is
        validating the argument first, which would tell a caller the chain
        refuses that their *other* argument was wrong — and a refusal that
        varies with a typo is a refusal that discloses.

        Raises:
            UnusableArgument: An argument the input schema forbade — a list that is not
                one of strings, is empty, or is longer than the declared ceiling;
                or a ``decision`` that is not one of the two declared values.
        """
        call = decide_call(principal, APPROVE_REQUISITION)
        if call.reason is not None:
            yield Decision(reason=call.reason)
            return

        for identifier in _identifiers(arguments):
            # One item's arguments, which is what the single-item call handed
            # the hydration step whole. The step's parameters are ADR-0013's and
            # the batch does not change them; what changes is that the handler
            # names the item rather than passing the call's own mapping along.
            resource = await hydrate(APPROVE_REQUISITION, {"id": identifier})

            decision = decide_item(principal, APPROVE_REQUISITION, resource)
            if decision.reason is not None:
                yield decision
                continue

            # Reachable only on a permit, and a permit means the chain saw a row.
            assert resource is not None
            written = await requisitions.decide(
                resource.id,
                approve=_decision(arguments) == APPROVE,
                # The principal's, never the caller's: no argument names an
                # approver, which is what makes the submitter rule a check
                # against a position occupied on this chain.
                approved_by=principal.subject,
            )
            yield Decision(reason=ALREADY_DECIDED) if written is None else written.as_row()

    return handler


def _identifiers(arguments: Mapping[str, Any]) -> tuple[str, ...]:
    """The rows this call names, in the order it named them.

    **In order and with repetitions kept.** The order is what a caller maps
    answers back onto — a folded result carries no identifiers, because an answer
    that named its row would make a refusal on a foreign row distinguishable from
    one on a row that never existed — and a repetition is an item the caller
    asked about, so it is answered rather than collapsed. *Outcomes equal items
    requested* is a rule about the request, and de-duplicating here would quietly
    make it a rule about the rows.

    The ceiling is checked rather than only declared, for the reason
    :func:`_amount` matches a pattern rather than trusting :class:`Decimal`:
    nothing on this stack validates arguments against a published
    ``inputSchema``, so a rule a model reads and a rule the server keeps are two
    rules unless one of them is written twice.

    Raises:
        UnusableArgument: It is absent, is not a list of strings, is empty, or names
            more rows than the declaration permits. The empty list is refused
            rather than answered with nothing: a call that named no item and got
            no answer is indistinguishable from a batch that dropped every item
            it was given.
    """
    value = arguments.get("ids")
    if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
        raise UnusableArgument("'ids' must be an array of strings")
    if not value:
        raise UnusableArgument("'ids' must name at least one requisition")
    if len(value) > MAXIMUM_BATCH:
        raise UnusableArgument(f"'ids' names more than {MAXIMUM_BATCH} requisitions: {len(value)}")
    return tuple(value)


def record_invoice(orders: PurchaseOrders) -> Handler:
    """Build the ``record_invoice`` handler over a store.

    Returns:
        The handler, in the shape layer 1's registry declares.
    """
    hydrate = load(orders)

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """Bill one purchase order, and write the invoice that bills it.

        **The resource is the order, and it is the first that is not a
        requisition.** The invoice does not exist yet and the chain never sees
        one — *the thing acted against, never the thing created*. The step that
        hydrates the order is the same :func:`load` the two requisition handlers
        call, parameterised on the entity this one's store answers with.

        The hydration step's answer goes straight to
        :func:`~mcp_erp.authorization.policy.decide_item`, ``None`` included, so
        an order in another partition and an order that was never there converge
        on layer 2's single return site exactly as a requisition does. The
        partition is one link up the chain — an order has no centre of its own —
        which changes where the value is read and nothing about the comparison.

        **Authorization first, then the row's own state**, on the same two
        orderings ``approve_requisition`` keeps. ``already_invoiced`` is answered
        only after the chain permits, so a caller who may not bill this order
        learns nothing about whether it has been billed; and the terminal check
        is the write itself rather than a test against the row loaded a moment
        ago, because a check that is not the write is a race two callers both
        pass.

        **Yields exactly one outcome, and is not a batch.** ADR-0002's *Five
        tools* gives the list to ``approve_requisition`` alone, so this is one
        item by declaration rather than by deferral — the fold #41 built is
        untouched, and layer 1 renders one outcome directly because it folds on
        cardinality and never learns which tool produced it. Stopping at
        ``decide_item`` is therefore the neighbour's obligation holding rather
        than being skipped: with one item, running the call gate once and running
        the chain per item are the same call.

        Raises:
            UnusableArgument: No ``id`` was named, or it was not a string. Raised by
                the hydration step, and distinct from ``not_found`` on purpose.
        """
        resource = await hydrate(RECORD_INVOICE, arguments)

        decision = decide_item(principal, RECORD_INVOICE, resource)
        if decision.reason is not None:
            yield decision
            return

        # Reachable only on a permit, and a permit means the chain saw a row.
        assert resource is not None
        written = await orders.bill(
            resource.id,
            # The principal's, never the caller's: no argument names a recorder,
            # which is what makes the second separation edge a check against a
            # position occupied on this chain.
            recorded_by=principal.subject,
        )
        if written is None:
            yield Decision(reason=ALREADY_INVOICED)
            return

        yield written.as_row()

    return handler


def _decision(arguments: Mapping[str, Any]) -> str:
    """Which way the caller decided, as one of the two values the schema declares.

    Matched against :data:`~mcp_erp.purchase_to_pay.approve_requisition.DECISIONS`
    rather than against a second spelling of the same two words — the rule the
    caller reads is the rule this enforces, which is the same argument
    :func:`_amount` makes about a pattern.

    Raises:
        UnusableArgument: It is absent, is not a string, or is not one of the two.
    """
    value = _string(arguments, "decision")
    if value not in DECISIONS:
        raise UnusableArgument(f"'decision' must be one of {DECISIONS}: {value!r}")
    return value


def _string(arguments: Mapping[str, Any], name: str) -> str:
    """One required string argument.

    Raises:
        UnusableArgument: It is absent or is not a string.
    """
    value = arguments.get(name)
    if not isinstance(value, str):
        raise UnusableArgument(f"{name!r} must be a string")
    return value


def _currency(arguments: Mapping[str, Any]) -> str:
    """The currency, which has exactly one legal value.

    Checked rather than defaulted: the schema declares a one-member ``enum``, so
    a caller sending something else has sent something the declaration forbade,
    and silently substituting the legal value would charge them for a currency
    they did not name.

    Raises:
        UnusableArgument: It is absent or is not the one legal value.
    """
    value = _string(arguments, "currency")
    if value != CURRENCY:
        raise UnusableArgument(f"'currency' must be {CURRENCY!r}")
    return value


def _amount(arguments: Mapping[str, Any]) -> Decimal:
    """The amount, as the decimal string ADR-0002 fixed the shape as.

    A string on the wire and a ``Decimal`` here, never a float: the column is
    ``numeric(12, 2)`` and binary floating point cannot represent what an
    accounting amount means.

    **Matched against the declared pattern rather than against a second reading
    of it.** ``Decimal`` is far more permissive than
    :data:`~mcp_erp.purchase_to_pay.submit_requisition.AMOUNT_PATTERN` — it
    accepts ``1e2``, ``+5``, surrounding whitespace, Python's ``1_0`` digit
    separators, and any number of decimal places — so parsing alone would let
    through values the declaration forbids. Two of those reach the column and
    change what a caller gets: ``1.555`` is silently rounded by
    ``numeric(12, 2)``, and eleven integer digits overflow it and surface as a
    database error rather than as *invalid params*. So the constant a model reads
    is the constant this matches, and the rule is stated once.

    Raises:
        UnusableArgument: It is absent, is not a string, is not the shape the schema
            declares, or is not positive. The last is the one rule the pattern
            deliberately does not carry — the column's own ``CHECK (amount > 0)``,
            checked here so a caller gets a message about their argument rather
            than an integrity error about a constraint they cannot see.
    """
    value = _string(arguments, "amount")
    if re.fullmatch(AMOUNT_PATTERN, value) is None:
        raise UnusableArgument(f"'amount' is not a decimal amount: {value!r}")

    amount = Decimal(value)
    if amount <= 0:
        raise UnusableArgument(f"'amount' must be positive: {value!r}")
    return amount

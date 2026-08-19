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
``approve_requisition``  ``decide_item``       one named row, and the rules read it
=======================  ====================  =========================================

**Hydration is a named step and it is shared.** :func:`load` is ADR-0013's
``load(action, arguments) -> Resource | None``, called by the two handlers that
decide against a named row and by nothing else. It is a step rather than a
collaborator of the policy function, which takes none — and it is one function
rather than two identical pairs of lines, so *the handler passes the store's
answer straight through* is a property of one place.

**An argument a schema forbade raises ``ValueError``.** That is not a refusal:
nothing was authorized or denied, and giving it a ``Reason`` would amend a closed
vocabulary for a spelling mistake. Layer 1 renders it as *invalid params*, which
is what the protocol says about a request it cannot act on, and the exception
type is the standard library's rather than one this package invents — so a
handler signals it without importing anything layer 1 owns.
"""

import re
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from decimal import Decimal
from typing import Any

from mcp_erp.authorization import Action, Decision, Principal, decide_call, decide_item
from mcp_erp.purchase_to_pay import vendors
from mcp_erp.purchase_to_pay.approve_requisition import ACTION as APPROVE_REQUISITION
from mcp_erp.purchase_to_pay.approve_requisition import APPROVE, DECISIONS
from mcp_erp.purchase_to_pay.get_requisition import ACTION as GET_REQUISITION
from mcp_erp.purchase_to_pay.list_requisitions import ACTION as LIST_REQUISITIONS
from mcp_erp.purchase_to_pay.reasons import ALREADY_DECIDED
from mcp_erp.purchase_to_pay.repository import Requisitions
from mcp_erp.purchase_to_pay.requisition import Requisition
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

Load = Callable[[Action[Requisition], Mapping[str, Any]], Awaitable[Requisition | None]]
"""ADR-0013's hydration step: ``load(action, arguments) -> Resource | None``.

The parameters are the ADR's, and the store is bound by the factory below rather
than passed — which is what makes this a *step* rather than a collaborator. The
policy function takes none, so a resource cannot arrive any way but pre-loaded.

``action`` is not read yet, and it is here rather than dropped because the
resource an action is decided against is a property of the action: today both
callers name a requisition by identifier, and ``record_invoice`` (#42) is decided
against a ``PurchaseOrder``, which is the call that makes this parameter select
an entity. A signature that dropped it would have to grow it back, and the
narrower one would be a second shape for a step ADR-0013 already fixed.
"""


def load(requisitions: Requisitions) -> Load:
    """Build the hydration step over a store.

    A factory for the same reason the handlers are: the store is the composition
    root's to own, and hydration is a layer-3 step that reaches a database.

    Returns:
        The step, in ADR-0013's shape.
    """

    async def loaded(
        action: Action[Requisition], arguments: Mapping[str, Any]
    ) -> Requisition | None:
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
            ValueError: No ``id`` was named, or it was not a string. Distinct
                from ``not_found`` on purpose — nothing was named, so nothing was
                looked for, and answering *not found* would claim a search that
                did not happen.
        """
        identifier = arguments.get("id")
        if not isinstance(identifier, str):
            raise ValueError("'id' must be a string")

        return await requisitions.by_id(identifier)

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
            ValueError: No ``id`` was named, or it was not a string. Raised by
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
            ValueError: An argument the input schema forbade — an unknown vendor,
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
        """Decide one requisition, and emit the order an approval produces.

        **The resource is hydrated and it is the requisition** — the thing acted
        against. The purchase order does not exist yet, and the chain never sees
        one.

        The hydration step's answer goes straight to
        :func:`~mcp_erp.authorization.policy.decide_item`, ``None`` included, so
        a row in another partition and a row that was never there converge on
        layer 2's single return site here exactly as they do on the read path.

        **Authorization first, then the row's own state.** ``already_decided`` is
        answered only after the chain permits, which is what stops it being an
        existence oracle: a caller who may not decide this row learns nothing
        about whether it has been decided. And the terminal check is the write
        itself rather than a test against the row loaded a moment ago, because a
        check that is not the write is a race two callers both pass.

        Yields exactly one outcome, for one item. The batch and the fold that
        turns N outcomes into one result body are #41's.

        **The chain runs before the rest of the arguments are read**, which is
        the order ``submit_requisition`` already keeps: a caller the chain
        refuses is answered without their other arguments being looked at, and a
        refused call cannot be told apart from a refused call that also had a
        typo in it. The identifier is the exception and has to be, because
        hydration cannot happen without one.

        Raises:
            ValueError: An argument the input schema forbade — no identifier, or
                a ``decision`` that is not one of the two declared values.
        """
        resource = await hydrate(APPROVE_REQUISITION, arguments)

        decision = decide_item(principal, APPROVE_REQUISITION, resource)
        if decision.reason is not None:
            yield decision
            return

        # Reachable only on a permit, and a permit means the chain saw a row.
        assert resource is not None
        requested = _decision(arguments)
        written = await requisitions.decide(
            resource.id,
            approve=requested == APPROVE,
            # The principal's, never the caller's: no argument names an approver,
            # which is what makes the submitter rule a check against a position
            # occupied on this chain.
            approved_by=principal.subject,
        )
        if written is None:
            yield Decision(reason=ALREADY_DECIDED)
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
        ValueError: It is absent, is not a string, or is not one of the two.
    """
    value = _string(arguments, "decision")
    if value not in DECISIONS:
        raise ValueError(f"'decision' must be one of {DECISIONS}: {value!r}")
    return value


def _string(arguments: Mapping[str, Any], name: str) -> str:
    """One required string argument.

    Raises:
        ValueError: It is absent or is not a string.
    """
    value = arguments.get(name)
    if not isinstance(value, str):
        raise ValueError(f"{name!r} must be a string")
    return value


def _currency(arguments: Mapping[str, Any]) -> str:
    """The currency, which has exactly one legal value.

    Checked rather than defaulted: the schema declares a one-member ``enum``, so
    a caller sending something else has sent something the declaration forbade,
    and silently substituting the legal value would charge them for a currency
    they did not name.

    Raises:
        ValueError: It is absent or is not the one legal value.
    """
    value = _string(arguments, "currency")
    if value != CURRENCY:
        raise ValueError(f"'currency' must be {CURRENCY!r}")
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
        ValueError: It is absent, is not a string, is not the shape the schema
            declares, or is not positive. The last is the one rule the pattern
            deliberately does not carry — the column's own ``CHECK (amount > 0)``,
            checked here so a caller gets a message about their argument rather
            than an integrity error about a constraint they cannot see.
    """
    value = _string(arguments, "amount")
    if re.fullmatch(AMOUNT_PATTERN, value) is None:
        raise ValueError(f"'amount' is not a decimal amount: {value!r}")

    amount = Decimal(value)
    if amount <= 0:
        raise ValueError(f"'amount' must be positive: {value!r}")
    return amount

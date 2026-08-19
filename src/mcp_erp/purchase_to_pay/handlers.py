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

======================  ====================  =========================================
Handler                 Entry point           Why it stops there
======================  ====================  =========================================
``list_requisitions``   both                  a call gate, then a decision per row
``get_requisition``     ``decide_item``       one named row, hydrated before deciding
``submit_requisition``  ``decide_call``       no resource at all; the partition is ours
======================  ====================  =========================================

**An argument a schema forbade raises ``ValueError``.** That is not a refusal:
nothing was authorized or denied, and giving it a ``Reason`` would amend a closed
vocabulary for a spelling mistake. Layer 1 renders it as *invalid params*, which
is what the protocol says about a request it cannot act on, and the exception
type is the standard library's rather than one this package invents — so a
handler signals it without importing anything layer 1 owns.
"""

from collections.abc import AsyncIterator, Callable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from mcp_erp.authorization import Decision, Principal, decide_call, decide_item
from mcp_erp.purchase_to_pay import vendors
from mcp_erp.purchase_to_pay.get_requisition import ACTION as GET_REQUISITION
from mcp_erp.purchase_to_pay.list_requisitions import ACTION as LIST_REQUISITIONS
from mcp_erp.purchase_to_pay.repository import Requisitions
from mcp_erp.purchase_to_pay.submit_requisition import ACTION as SUBMIT_REQUISITION
from mcp_erp.purchase_to_pay.submit_requisition import CURRENCY

Handler = Callable[[Principal, Mapping[str, Any]], AsyncIterator[Mapping[str, Any] | Decision]]
"""The shape layer 1 calls, written here as well as there.

Stated twice rather than imported, for the same reason the seed's path is: the
two packages import nothing from each other, and a shared alias would have to
live in layer 2 — which would then hold a type describing how layer 1 renders.
The composition root is where the two spellings meet, and a disagreement between
them fails the types job there.
"""


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

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """One named requisition, or the refusal that says nothing about why.

        **Hydrate, then decide, and pass the result straight through.** The row
        is loaded by identifier alone and handed to
        :func:`~mcp_erp.authorization.policy.decide_item` exactly as the store
        answered — ``None`` included. That is what makes the empty join and the
        foreign row converge on layer 2's single return site instead of on a
        branch here: this handler cannot tell the two apart, because it never
        looks.

        Raises:
            ValueError: No ``id`` was named, or it was not a string. Distinct
                from ``not_found`` on purpose — nothing was named, so nothing was
                looked for, and answering *not found* would claim a search that
                did not happen.
        """
        identifier = arguments.get("id")
        if not isinstance(identifier, str):
            raise ValueError("get_requisition requires an 'id' argument")

        resource = await requisitions.by_id(identifier)
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

    Raises:
        ValueError: It is absent, is not a string, is not a decimal, or is not
            positive. The last is the column's own ``CHECK (amount > 0)``,
            checked here so a caller gets a message about their argument rather
            than an integrity error about a constraint they cannot see.
    """
    value = _string(arguments, "amount")
    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"'amount' is not a decimal: {value!r}") from None

    if not amount.is_finite() or amount <= 0:
        raise ValueError(f"'amount' must be positive: {value!r}")
    return amount

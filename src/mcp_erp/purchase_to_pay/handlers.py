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
survives ejection precisely by having none — so its falsifier is at the wire, in
``list_partition_scoped``.
"""

from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any

from mcp_erp.authorization import Decision, Principal, decide_call, decide_item
from mcp_erp.purchase_to_pay.repository import Requisitions
from mcp_erp.purchase_to_pay.requisition import LIST_REQUISITIONS

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

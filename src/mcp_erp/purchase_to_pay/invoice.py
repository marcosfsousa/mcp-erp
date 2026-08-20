"""The third entity — the record that a purchase order has been billed, and the last one.

**Created, never decided against.** ADR-0013 fixes the resource as *"the thing
acted against, never the thing created"*, and an invoice is the created half: it
does not exist when ``record_invoice`` is decided, so it satisfies no protocol
here and layer 2 never sees it. What that tool *is* decided against is the
:class:`~mcp_erp.purchase_to_pay.purchase_order.PurchaseOrder` beside this
module, through its ``approved_by``.

**Where the governing rule bites hardest** (ADR-0003). No amount, no vendor, no
supplier reference: the purchase order fixes all three, and since an order takes
exactly one invoice at full value an amount field could only restate one. What is
left is a reference and an identity — which order was billed, and who recorded
it — and ``recorded_by`` is there because it is the far side of the second
segregation-of-duties edge rather than because an invoice is expected to name who
handled it.

The tool that creates one is declared in a module of its own beside this,
:mod:`~mcp_erp.purchase_to_pay.record_invoice`, on the rule ADR-0013 states: the
entity is here and the tools are not.

**Nothing here is protocol-shaped.** The schemas are plain JSON Schema documents
and the rows are plain mappings; layer 1 wraps them in whatever the protocol
package's types are.
"""

from dataclasses import dataclass
from typing import Any, Final

from mcp_erp.purchase_to_pay.purchase_order import ORDER_SCHEMA, PurchaseOrder
from mcp_erp.purchase_to_pay.requisition import REFERENCE_SCHEMA

INVOICE_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        # The order it bills, as the `{id, label}` pair every reference here
        # takes. The label is the requisition's description — the same named
        # legibility exception the order's own reference spends, one link
        # further down: `inv_0001 → po_0001` narrates nothing, and this reads.
        "purchase_order": REFERENCE_SCHEMA,
        "recorded_by": REFERENCE_SCHEMA,
    },
    "required": ["id", "purchase_order", "recorded_by"],
    "additionalProperties": False,
}
"""One invoice on the wire: a reference, an identity, and its own handle.

Three fields, and the absences are the entity. No `amount`, no `vendor` and no
`cost_centre` — every one of them is the order's or the requisition's, a join
away, and a field earns its place only if it changes an authorization decision.
`recorded_by` is the one here that does: it is the position a third step on this
chain would be checked against, on the same terms as `approved_by` one link up.

**The label repeats the one the order carries, and that is the chain reading
rather than a fact stored twice.** A whole result body shows
`{"id": "inv_0001", "purchase_order": {"id": "po_0001", "label": "…"}}` beside
`{"id": "po_0001", "requisition": {"id": "req_0007", "label": "…"}}`, with the
same string against two different identifiers. Nothing else would be true: an
order has no name of its own, so its only narratable content is the
requisition's, and the alternative is a reference whose reader's half is
`req_0007`. ADR-0003 grants `description` as the one legibility exception, and
this spends the same grant one link further down rather than widening it — the
column is still on `requisition` and only there, and the invoice table has no
label column at all. Two references sharing a label is what a reader uses to see
that all three records belong to one chain.
"""

RECORDED_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"purchase_order": ORDER_SCHEMA, "invoice": INVOICE_SCHEMA},
    "required": ["purchase_order", "invoice"],
    "additionalProperties": False,
}
"""What one recording answers with: the order as billed, and the invoice it produced.

**Both are required, which is where this differs from the decision's document.**
A rejection produces no purchase order, so
:data:`~mcp_erp.purchase_to_pay.purchase_order.DECISION_SCHEMA` makes that half
optional. Recording goes one way only: it creates an invoice or it is refused, so
a caller who gets a result gets both halves of it.

The order is here because its status is the thing that moved. Nothing anywhere
reads a purchase order back: ADR-0002 cut `list_purchase_orders` and
`list_invoices` for demonstrating no authorization behaviour the surviving tools
do not, so `open` becoming `invoiced` would otherwise be a terminal state with
nothing in the tool set able to observe it.
"""


@dataclass(frozen=True, slots=True)
class Invoice:
    """The record that a purchase order has been billed.

    Attributes:
        id: The opaque prefixed handle, sequential and legible on the same terms
            as a requisition's and an order's — the normative register's
            *Legible identifiers* deviation.
        purchase_order_id: The order it bills. Unique in the schema, which is
            what makes a second recording answer ``already_invoiced`` rather
            than mint a second invoice.
        purchase_order_label: The requisition's description, for the
            ``{id, label}`` pair — the same label the order's own reference to
            that requisition carries.
        recorded_by: The recorder's subject — an identity, not a role, because a
            position is occupied once on one chain while a role is held standing.
        recorder_name: The recorder's display name, the other half of the pair.
    """

    id: str
    purchase_order_id: str
    purchase_order_label: str
    recorded_by: str
    recorder_name: str

    def as_row(self) -> dict[str, Any]:
        """The wire shape of one invoice, matching :data:`INVOICE_SCHEMA`."""
        return {
            "id": self.id,
            "purchase_order": {"id": self.purchase_order_id, "label": self.purchase_order_label},
            "recorded_by": {"id": self.recorded_by, "label": self.recorder_name},
        }


@dataclass(frozen=True, slots=True)
class Recorded:
    """What one recording produced, and the only thing a recorded call answers with.

    The counterpart of :class:`~mcp_erp.purchase_to_pay.purchase_order.Decided`,
    making the same distinction it does: this is a fact about the **rows**, not
    about a caller. ``CONTEXT.md`` gives *Decision* to what the chain answers for
    one item — a permit, or the reason it refuses on — and a handler holds both
    within four lines of each other.

    Two entities in one record because a recording touches two: the order moves
    to a terminal state, and the invoice is created. Neither half is nullable,
    which is where this differs from ``Decided``: a decision can go either way
    and only one of the two emits an order.

    It lives beside the invoice rather than beside the order because the invoice
    is the thing a recording *creates*; the order already existed and is answered
    with rather than produced.

    Attributes:
        purchase_order: The order as billed, carrying its new status.
        invoice: The invoice the recording created.
    """

    purchase_order: PurchaseOrder
    invoice: Invoice

    def as_row(self) -> dict[str, Any]:
        """The whole result body, matching :data:`RECORDED_SCHEMA`.

        Rendered here rather than in the handler, so the type that knows what a
        recording produced is the type that renders it — the same rule
        :meth:`Invoice.as_row` already keeps one level down.
        """
        return {"purchase_order": self.purchase_order.as_row(), "invoice": self.invoice.as_row()}

"""The second entity — the record an approval emits, and what one decision answers with.

**Emitted, never decided against.** ADR-0013 fixes the resource as *"the thing
acted against, never the thing created"*, and a purchase order is the created
half: it does not exist when ``approve_requisition`` is decided, so it satisfies
no protocol here and layer 2 never sees it. It becomes a resource at #42, where
``record_invoice`` is decided against it — and the field that makes that decision
possible, :attr:`PurchaseOrder.approved_by`, is the whole reason this entity
exists.

**It does not copy the cost centre forward.** ADR-0002 described it as carrying
"the approver identity and cost centre forward"; ADR-0003 corrected that — the
identity is load-bearing and the centre is a join away, so denormalising it would
buy a shorter query and a second copy of a fact that can disagree with the first.

The tool that emits one is declared in a module of its own beside this,
:mod:`~mcp_erp.purchase_to_pay.approve_requisition`, on the rule ADR-0013 states:
the entity is here and the tools are not.

**Nothing here is protocol-shaped.** The schemas are plain JSON Schema documents
and the rows are plain mappings; layer 1 wraps them in whatever the protocol
package's types are.
"""

from dataclasses import dataclass
from typing import Any, Final

from mcp_erp.purchase_to_pay.requisition import REFERENCE_SCHEMA, ROW_SCHEMA, Requisition

ORDER_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        # The row it was raised from, as the `{id, label}` pair every reference
        # here takes. The label is the requisition's description, which is the
        # named legibility exception doing the work it was granted for: `po_0001
        # → req_0007` narrates nothing, and this reads.
        "requisition": REFERENCE_SCHEMA,
        "approved_by": REFERENCE_SCHEMA,
        "status": {"enum": ["open", "invoiced"]},
    },
    "required": ["id", "requisition", "approved_by", "status"],
    "additionalProperties": False,
}
"""One purchase order on the wire.

No `cost_centre` and no `amount`. Both are the requisition's, one join away, and
a field earns its place here only if it changes an authorization decision — which
`approved_by` does and neither of those would.
"""

DECISION_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"requisition": ROW_SCHEMA, "purchase_order": ORDER_SCHEMA},
    "required": ["requisition"],
    "additionalProperties": False,
}
"""What one decision answers with: the row as decided, and the order if one was emitted.

**``purchase_order`` is absent rather than null on a rejection**, because the
record does not exist — a null would say it exists and is empty. The requisition
is always there, so a caller learns the state their own call produced without a
second read, and a rejection is not a result with nothing in it.

The row description is shared with the three tools that answer with a
requisition, so the tool that *changes* a row's status cannot describe that row
differently from the tools that read it.
"""


@dataclass(frozen=True, slots=True)
class PurchaseOrder:
    """The record emitted when a requisition is approved.

    Attributes:
        id: The opaque prefixed handle, sequential and legible on the same terms
            as a requisition's — the normative register's *Legible identifiers*
            deviation.
        requisition_id: The row it was raised from. Unique in the schema, which
            is what makes a second decision answer ``already_decided`` rather
            than mint a second order.
        requisition_label: The requisition's description, for the ``{id, label}``
            pair. Carried rather than joined at render time for the same reason
            ``Requisition`` carries its vendor's name.
        approved_by: The approver's subject — an identity, not a role, because a
            position is occupied once on one chain while a role is held standing.
            This is what the second segregation-of-duties edge is tested against.
        approver_name: The approver's display name, the other half of the pair.
        status: ``open`` or ``invoiced``.
    """

    id: str
    requisition_id: str
    requisition_label: str
    approved_by: str
    approver_name: str
    status: str

    def as_row(self) -> dict[str, Any]:
        """The wire shape of one purchase order, matching :data:`ORDER_SCHEMA`."""
        return {
            "id": self.id,
            "requisition": {"id": self.requisition_id, "label": self.requisition_label},
            "approved_by": {"id": self.approved_by, "label": self.approver_name},
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class Decided:
    """What one decision produced, and the only thing a decided call answers with.

    **Not a ``Decision`` by another name**, and the near-miss is worth stating in
    the exhibit built to keep exactly this vocabulary straight. ``CONTEXT.md``
    gives *Decision* to what the chain answers for one item — a permit or the
    reason it refuses on — which is a fact about a **caller**. This is a fact
    about the **rows**: what was written once a decision had already been
    permitted. A handler holds both within four lines of each other, and they
    never stand in for one another.

    Two entities in one record because a decision touches two: the requisition
    moves to a terminal state, and an approval additionally emits an order. A
    rejection produces the first alone, which is why :attr:`purchase_order` is
    nullable here and absent from the rendered row rather than null in it.

    It lives beside the order rather than beside the requisition because the
    order is the thing a decision *creates*; the requisition already existed and
    is answered with rather than produced.

    Attributes:
        requisition: The row as decided, carrying its new status.
        purchase_order: The order an approval emitted, or ``None`` on a rejection.
    """

    requisition: Requisition
    purchase_order: PurchaseOrder | None

    def as_row(self) -> dict[str, Any]:
        """The whole result body, matching :data:`DECISION_SCHEMA`.

        Rendered here rather than in the handler, so the type that knows what a
        decision produced is the type that renders it — the same rule
        :meth:`Requisition.as_row` already keeps one level down.
        """
        row: dict[str, Any] = {"requisition": self.requisition.as_row()}
        if self.purchase_order is not None:
            row["purchase_order"] = self.purchase_order.as_row()
        return row

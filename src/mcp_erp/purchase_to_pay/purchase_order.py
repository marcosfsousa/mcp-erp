"""The second entity — emitted by one tool, and the resource the next one is decided against.

**Emitted by an approval, never decided against by one.** ADR-0013 fixes the
resource as *"the thing acted against, never the thing created"*, and a purchase
order is the created half of ``approve_requisition``: it does not exist when that
tool is decided, so the chain never sees one there.

**It is a resource on the other tool, and that is what this entity is for.**
``record_invoice`` is decided against it, and the field that makes the decision
possible — :attr:`PurchaseOrder.approved_by` — is the whole reason the entity
exists. Being on both sides of ADR-0013's rule is not a contradiction in it: the
rule is about one tool at a time, and *created here, acted against there* is what
a chain is.

**It does not copy the cost centre forward, and being a resource does not change
that.** ADR-0002 described it as carrying "the approver identity and cost centre
forward"; ADR-0003 corrected that — the identity is load-bearing and the centre
is a join away, so denormalising it would buy a shorter query and a second copy
of a fact that can disagree with the first. :attr:`PurchaseOrder.cost_centre` is
that join's answer held in the entity, not a column: the row scoping
``record_invoice`` runs needs a partition, and it reads the requisition's own
rather than a second copy of it. The wire shape is unchanged, because no
authorization decision anywhere is taken on what a *caller* was told the centre
is.

The tool that emits one is declared in a module of its own beside this,
:mod:`~mcp_erp.purchase_to_pay.approve_requisition`, and the tool decided against
one in :mod:`~mcp_erp.purchase_to_pay.record_invoice`, on the rule ADR-0013
states: the entity is here and the tools are not.

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

OUTCOMES_KEY: Final = "outcomes"
"""Layer 1's key for the N answers a folded result carries.

Spelled here as well as in :data:`mcp_erp.transport.dispatch.FOLD_KEY`, on the
same terms as ``Handler``: the two packages import nothing from each other, and a
constant they shared would have to live in layer 2 — which would then hold a
value describing how layer 1 renders. Nothing on either side can catch the two
drifting apart — this half would publish a schema describing a body no call
produces — so the equality is asserted at the one altitude that sees both:
``tests/wire/test_the_fold.py::test_the_declared_key_and_the_rendered_one_are_one_key``.
"""

DECISIONS_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        # The one-item body's own properties, spread rather than restated: the
        # two cardinalities describe the same decision and must not grow two
        # descriptions of it.
        **DECISION_SCHEMA["properties"],
        OUTCOMES_KEY: {"type": "array", "items": DECISION_SCHEMA},
    },
    "additionalProperties": False,
    "oneOf": [{"required": DECISION_SCHEMA["required"]}, {"required": [OUTCOMES_KEY]}],
}
"""What one **call** answers with, which is one decision or a list of them.

**Two bodies in one declaration, and that is the price of a guarantee rather
than an accident.** Layer 1 folds on outcome cardinality because cardinality is
the only thing it is permitted to know — it never learns the tool's name nor
which argument carried the batch — so a one-item call is indistinguishable there
from ``get_requisition``, and it renders the same way: the decision itself. Two
items fold. The tool that can be called either way therefore publishes both, and
the `oneOf` is what keeps that a choice of two bodies rather than one body with
optional halves.

**It describes the body of a result that is not marked in error**, which is what
an ``outputSchema`` has described here since the first refusal shipped. Declaring
the refusal's shape would put layer 1's rendering in a layer-3 document — the
coupling ADR-0004's first entry exists to refuse — and a reason's wire shape is
already stated once, at the point each reason is declared.

**A folded body with a refusal in it therefore matches the shape and not the
items**, which is new and is worth saying rather than leaving to be discovered. A
single-item refusal matched nothing here at all; a mixed batch matches the
``outcomes`` branch and then fails on the entry that is a refusal. Both are out
of this document's remit for the same reason — they are marked in error — and the
rule is stated as *not marked in error* above rather than as *permitted* so that
the mixed case is inside the sentence rather than beside it.
"""


@dataclass(frozen=True, slots=True)
class PurchaseOrder:
    """The record emitted when a requisition is approved, and what an invoice bills.

    The second type here to satisfy layer 2's one-member
    :class:`~mcp_erp.authorization.action.Resource` protocol, through
    :attr:`partition` alone. ``approved_by`` is what the second
    segregation-of-duties edge reads, and it is read by a relationship rule
    declared beside ``record_invoice`` rather than by layer 2 (ADR-0013).

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
        cost_centre: The requisition's, read through the join rather than stored
            on the order — see the module docstring. It appears in no schema and
            on no wire: it is here because row scoping needs a partition, and
            :attr:`partition` is the whole of what reads it.
        approved_by: The approver's subject — an identity, not a role, because a
            position is occupied once on one chain while a role is held standing.
            This is what the second segregation-of-duties edge is tested against.
        approver_name: The approver's display name, the other half of the pair.
        status: ``open`` or ``invoiced``.
    """

    id: str
    requisition_id: str
    requisition_label: str
    cost_centre: str
    approved_by: str
    approver_name: str
    status: str

    @property
    def partition(self) -> str:
        """The partition row scoping compares, which here is the requisition's centre.

        The same translation :attr:`Requisition.partition` makes, reaching one
        link further up the chain for the value: an order has no centre of its
        own, and the one it is scoped by is the one the requisition was charged
        to. That is the join ADR-0003 chose over a denormalised column, arriving
        where the decision is taken rather than where the row is rendered.
        """
        return self.cost_centre

    def as_row(self) -> dict[str, Any]:
        """The wire shape of one purchase order, matching :data:`ORDER_SCHEMA`.

        No ``cost_centre``, and the field above is not an omission from here: the
        centre is the requisition's to state, the row this points at states it,
        and a second copy on the wire is the disagreement ADR-0003 declined.
        """
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

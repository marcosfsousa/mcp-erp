"""The first entity, the first ``Action``, and the wire shape they render as.

``Requisition`` is the first type in this repository to satisfy layer 2's
one-member :class:`~mcp_erp.authorization.action.Resource` protocol, and
``LIST_REQUISITIONS`` is the first ``Action`` any layer declares. Everything
that crosses into the authorization layer from here is in that one constant;
the rest of this module is the domain talking to itself and to the wire.

**Nothing here is protocol-shaped.** The schemas below are plain JSON Schema
documents and the rows are plain mappings — layer 1 wraps them in whatever the
protocol package's types are, and layer 3 never imports that package (ADR-0013).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

from mcp_erp.authorization import Action, Capability

NAME: Final = "list_requisitions"
"""The tool's name on the wire.

Layer 1 keys its registry on this and the composition root is what pairs it
with the declaration below. Nothing derives a scope string from it — the scope
comes from the capability, which is the single declaration ADR-0012 made three
artifacts derive from.
"""

TITLE: Final = "List requisitions"

DESCRIPTION: Final = (
    "List the purchase requisitions the caller may see. "
    "Which rows come back is decided per caller and is not a filter the caller sets."
)
"""What a model reads before calling.

The second sentence is doing work rather than narrating: row scoping is
invisible in the input schema — there is nothing to pass — so a model with no
argument to vary can otherwise read an empty result as a malformed call and
retry it identically.
"""

INPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}
"""No inputs at all, which is the governing rule holding rather than an omission.

A ``cost_centre`` filter would be a field that changes no authorization
decision — the caller's partition already decides which rows come back — and a
free-text one would leak which centres exist, which is the probing surface
ADR-0002 designed out of ``submit_requisition`` for the same reason. A
``status`` filter would be convenience, and this is not a product.
"""

_REFERENCE_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"id": {"type": "string"}, "label": {"type": "string"}},
    "required": ["id", "label"],
    "additionalProperties": False,
}
"""An ``{id, label}`` pair, which is ADR-0002's shape for every reference.

One level deep and no deeper. The label is the reader's half and the identifier
is the machine's; a bare identifier would make the walkthrough unreadable and a
bare label would make the next tool call a guess.
"""

OUTPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "requisitions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "cost_centre": {"type": "string"},
                    "vendor": _REFERENCE_SCHEMA,
                    # A decimal string plus an explicit currency, never a float.
                    # ADR-0002 fixed the shape; the currency has one legal value
                    # and is carried anyway, because an amount without one is a
                    # defect waiting for a second currency.
                    "amount": {"type": "string"},
                    "currency": {"type": "string"},
                    "description": {"type": "string"},
                    "submitted_by": _REFERENCE_SCHEMA,
                    "status": {"enum": ["submitted", "approved", "rejected"]},
                },
                "required": [
                    "id",
                    "cost_centre",
                    "vendor",
                    "amount",
                    "currency",
                    "description",
                    "submitted_by",
                    "status",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["requisitions"],
    "additionalProperties": False,
}
"""Declared, because every tool declares one (ADR-0002).

The matrix asserts on the structured half and the model reads the text half, so
the two audiences are served by one result rather than by a choice between them.
"""


@dataclass(frozen=True, slots=True)
class Requisition:
    """A request to buy something from a vendor, charged to the submitter's own cost centre.

    Satisfies layer 2's :class:`~mcp_erp.authorization.action.Resource` protocol
    through :attr:`partition` alone. Everything else here is the domain's, and
    the authorization layer never reads it — ``submitted_by`` is the exception
    waiting to happen, and it will be read by a relationship rule declared
    beside this type rather than by layer 2 (ADR-0013).

    Attributes:
        id: The opaque prefixed handle, sequential and legible against a
            specification ``SHOULD`` — normative register row 3, taken so that
            the probe scenario can *guess* a foreign identifier rather than be
            handed one.
        cost_centre: The submitter's own, stamped at submission. Layer 3's name
            for what layer 2 compares as the partition.
        vendor: The vendor's identifier.
        vendor_name: The vendor's display name, for the ``{id, label}`` pair.
        amount: A decimal, rendered as a string on the wire.
        currency: One legal value, carried explicitly.
        description: The named legibility exception (ADR-0003).
        submitted_by: The submitter's subject — an identity, not a role, because
            a position is occupied once on one chain while a role is held
            standing.
        submitter_name: The submitter's display name, the other half of the pair.
        status: ``submitted``, ``approved`` or ``rejected``.
    """

    id: str
    cost_centre: str
    vendor: str
    vendor_name: str
    amount: Decimal
    currency: str
    description: str
    submitted_by: str
    submitter_name: str
    status: str

    @property
    def partition(self) -> str:
        """The partition row scoping compares, which here is the cost centre.

        The one point where layer 2's word and layer 3's word meet. Layer 2 says
        *partition* because the mechanism has to survive a domain with no
        accounting in it; this property is the whole of the translation.
        """
        return self.cost_centre

    def as_row(self) -> dict[str, Any]:
        """The wire shape of one requisition, matching :data:`OUTPUT_SCHEMA`.

        Built here rather than in the handler so that the type that knows the
        fields is the type that renders them, and so a second read tool cannot
        grow a second rendering of the same row.
        """
        return {
            "id": self.id,
            "cost_centre": self.cost_centre,
            "vendor": {"id": self.vendor, "label": self.vendor_name},
            "amount": str(self.amount),
            "currency": self.currency,
            "description": self.description,
            "submitted_by": {"id": self.submitted_by, "label": self.submitter_name},
            "status": self.status,
        }


LIST_REQUISITIONS: Action[Requisition] = Action(
    namespace="erp",
    capability=Capability.READ,
    required_roles=frozenset(),
    rules=(),
    partition_bypass=frozenset({"auditor"}),
)
"""What ``list_requisitions`` declares, and the first ``Action`` in the repository.

The explicit annotation is required rather than stylistic: with no relationship
rules there is nothing for a type checker to infer ``R`` from.

``required_roles`` is empty because reading is gated by scope alone — ``auditor``
widens which rows come back and grants no reading of its own (ADR-0007), so
putting it here would refuse every other member of the cast.

``partition_bypass`` carries the **positive** half of ADR-0013's non-uniform
field: ``{auditor}`` on the two read tools, and **empty on the three writes**.
Breadth is a read widening, never a write grant, and nothing in the type will
object to the wrong value — which is why the value is stated at the first
declaration rather than a slice later. Here the wrong value is caught, because a
read row asserts set equality over returned identifiers and an auditor reading
three cost centres of three fails loudly against an empty bypass. On the write
tools the same mistake is invisible: row scoping runs after the role gate and
nobody in the cast holds ``auditor`` beside a deciding role, so no matrix row
reaches it. The read side is guarded by a test; the write side is guarded by
review.
"""

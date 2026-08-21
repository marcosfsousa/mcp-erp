"""The first entity, and the wire shape one row renders as.

``Requisition`` is the first type in this repository to satisfy layer 2's
one-member :class:`~mcp_erp.authorization.action.Resource` protocol. Everything
that crosses into the authorization layer from here is an ``Action``, and the
three that name this entity are declared in a module each beside this one:
:mod:`~mcp_erp.purchase_to_pay.list_requisitions`,
:mod:`~mcp_erp.purchase_to_pay.get_requisition` and
:mod:`~mcp_erp.purchase_to_pay.submit_requisition`.

**The entity is here and the tools are not**, which is what the second and third
tool made necessary rather than merely tidy. A tool declares five module-level
names — ``NAME``, ``TITLE``, ``DESCRIPTION``, ``INPUT_SCHEMA``, ``OUTPUT_SCHEMA``
— and the three named just above, sharing one module, would have to prefix every
one of them. That is the same flattening layer 3's ``__init__`` refuses at the
package level, arriving one level down.

**Nothing here is protocol-shaped.** The schemas below are plain JSON Schema
documents and the rows are plain mappings — layer 1 wraps them in whatever the
protocol package's types are, and layer 3 never imports that package (ADR-0013).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

REFERENCE_SCHEMA: Final[dict[str, Any]] = {
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

ROW_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "cost_centre": {"type": "string"},
        "vendor": REFERENCE_SCHEMA,
        # A decimal string plus an explicit currency, never a float. ADR-0002
        # fixed the shape; the currency has one legal value and is carried
        # anyway, because an amount without one is a defect waiting for a second
        # currency.
        "amount": {"type": "string"},
        "currency": {"type": "string"},
        "description": {"type": "string"},
        "submitted_by": REFERENCE_SCHEMA,
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
}
"""One requisition on the wire, shared by every tool that answers with one.

Which is ``list_requisitions``, ``get_requisition``, ``submit_requisition`` and —
through :data:`mcp_erp.purchase_to_pay.purchase_order.DECISION_SCHEMA` —
``approve_requisition``. ``record_invoice`` is the one tool that answers with no
requisition at all.

Declared once for the same reason :meth:`Requisition.as_row` is written once: the
type that knows the fields is the type that renders them, and tools returning the
same row must not grow four descriptions of it that only nearly agree.
"""

SINGLE_ROW_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"requisition": ROW_SCHEMA},
    "required": ["requisition"],
    "additionalProperties": False,
}
"""A result carrying exactly one requisition.

The output of ``get_requisition`` and of ``submit_requisition``. The named read
answers with the row it was asked for and the write answers with the row it
created, and those are the same document. Shared for the same reason
:data:`ROW_SCHEMA` is, one level up: the wrapper is as much a description of the
row as the row's own properties are, and two copies of it is two places for
``required`` to disagree.

Not shared with ``list_requisitions``, which returns an array under a plural key
— a different shape rather than the same one written twice.
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
            specification ``SHOULD`` — the normative register's *Legible
            identifiers* deviation, taken so that the probe scenario can
            *guess* a foreign identifier rather than be handed one.
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
        """The wire shape of one requisition, matching :data:`ROW_SCHEMA`.

        Built here rather than in a handler so that the type that knows the
        fields is the type that renders them, and so the tools that answer with
        this row cannot grow a rendering each.
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

"""``list_requisitions`` — the discovered half of the refusal contract.

The first ``Action`` this repository declared, and the tool the *omitted, never
refused* half of ADR-0013's contract belongs to:

    A resource **named** in the request is refused, never omitted.
    A resource **discovered** by listing is omitted, never refused.

Its named counterpart is :mod:`~mcp_erp.purchase_to_pay.get_requisition`.
"""

from typing import Any, Final

from mcp_erp.authorization import Action, Capability
from mcp_erp.purchase_to_pay.requisition import ROW_SCHEMA, Requisition

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

OUTPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"requisitions": {"type": "array", "items": ROW_SCHEMA}},
    "required": ["requisitions"],
    "additionalProperties": False,
}
"""Declared, because every tool declares one (ADR-0002).

The matrix asserts on the structured half and the model reads the text half, so
the two audiences are served by one result rather than by a choice between them.
"""

ACTION: Action[Requisition] = Action(
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
object to the wrong value. Here the wrong value is caught, because a read row
asserts set equality over returned identifiers and an auditor reading three cost
centres of three fails loudly against an empty bypass. On the write tools the
same mistake is invisible: row scoping runs after the role gate and nobody in
the cast holds ``auditor`` beside a deciding role, so no matrix row reaches it.
The read side is guarded by a test; the write side is guarded by review.
"""

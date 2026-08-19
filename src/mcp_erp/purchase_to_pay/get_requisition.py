"""``get_requisition`` — a named resource, and the entry point that scopes a row.

The named half of ADR-0013's refusal contract, and the first tool to exercise
:func:`~mcp_erp.authorization.policy.decide_item` with a row rather than with
``None``:

    A resource **named** in the request is refused, never omitted.
    A resource **discovered** by listing is omitted, never refused.

**A foreign row and a row that never existed are one refusal.** Both answer
``not_found``, byte-identically, reached through the single return site in
:mod:`mcp_erp.authorization.policy` — the handler passes the hydration result
straight through, so the empty join and the out-of-partition row converge inside
layer 2 rather than being made to agree here. Two return sites would make the
refusal an existence oracle, which is the finding ADR-0002 declined to ship, and
ADR-0002's option 3 rejected an explicit ``row_out_of_scope`` on this exact tool
for the same reason.

Identifiers are sequential and legible against a specification ``SHOULD``, so
the probe scenario can *guess* a foreign identifier rather than be handed one.
That deviation is what makes the refusal above demonstrated rather than asserted.
"""

from typing import Any, Final

from mcp_erp.authorization import Action, Capability
from mcp_erp.purchase_to_pay.requisition import ROW_SCHEMA, Requisition

NAME: Final = "get_requisition"
"""The tool's name on the wire, and the key layer 1's registry holds it under."""

TITLE: Final = "Get requisition"

DESCRIPTION: Final = (
    "Fetch one purchase requisition by its identifier. "
    "An identifier the caller may not see and an identifier that does not exist "
    "answer identically, so a refusal here says nothing about whether the row exists."
)
"""What a model reads before calling.

The second sentence is the same kind of work ``list_requisitions``'s is: a model
that reads ``not_found`` as *wrong identifier* will otherwise enumerate, and the
whole point of the refusal is that enumerating learns nothing. Saying so costs a
sentence and is not a disclosure — it describes the shape of the API, which is
public, rather than the contents of the database, which are not.
"""

INPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"id": {"type": "string"}},
    "required": ["id"],
    "additionalProperties": False,
}
"""One argument: the identifier the caller names.

No ``cost_centre`` beside it, and the absence is the design rather than an
omission. The caller's partition is server-derived, so a second input could only
either change nothing or become the enumeration primitive ADR-0002 designed out
of ``submit_requisition``.
"""

OUTPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"requisition": ROW_SCHEMA},
    "required": ["requisition"],
    "additionalProperties": False,
}
"""One row, in the shape the listing returns many of.

Shared with :mod:`~mcp_erp.purchase_to_pay.list_requisitions` rather than
restated, so the single-row read and the listing cannot describe the same row
two ways.
"""

ACTION: Action[Requisition] = Action(
    namespace="erp",
    capability=Capability.READ,
    required_roles=frozenset(),
    rules=(),
    partition_bypass=frozenset({"auditor"}),
)
"""What ``get_requisition`` declares — the **second** of ADR-0013's two read tools.

Identical to ``list_requisitions``'s declaration, and that identity is the
claim rather than a copy waiting to be factored out: the two tools differ in what
they do with a refused row, never in how a row is decided. One shared constant
would say the two Actions are the same object, which is a stronger statement than
the one the trail makes and the one a fourth tool would have to break.

``partition_bypass`` holds ``{auditor}`` because this is a read — the positive
half of ADR-0013's non-uniform field, and the reason this ticket declares one of
each: :mod:`~mcp_erp.purchase_to_pay.submit_requisition` is the empty half, and
the asymmetry is visible in one diff here and nowhere else. Breadth is a read
widening, never a write grant.

``required_roles`` is empty because reading is gated by scope alone. A
consequence worth stating: the ``role_missing`` denial class is therefore not
reachable through this tool or through ``submit_requisition``, and it stays that
way until a role-gated tool exists (#40).
"""

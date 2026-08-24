"""``approve_requisition`` — the role gate, the threshold, and the first hydrated resource.

The tool the whole authorization design was drawn for. It is the first to declare
a role, the first with relationship rules, and the first whose resource has to be
**loaded before the decision is taken** — the policy function has no
collaborators, so the row cannot arrive any other way (ADR-0013).

**The resource is the ``Requisition``, never the ``PurchaseOrder``.** The order is
what approval *emits*; it does not exist when the decision is taken, and *the
resource is the thing acted against, never the thing created*.

**The batch, restored at #41.** ADR-0002 specified this tool as taking a list and
#40 deferred it until layer 1 could render more than one answer; the fold landed
with this, so the list is back. It is the only tool of the five that is a batch,
which is ADR-0002's reading of what a batch *is* — a call that yields N
independent outcomes — rather than a convenience: every other tool answers one
question, and a list of them would be one outcome carrying rows.

**One decision for the whole list.** The decision is what the caller intends and
the list is the set of rows they intend it for; a list of ``{id, decision}``
pairs would be a second way to spell the same call, buying no authorization
behaviour and doubling what a model has to get right.

**And both entry points, because of the batch.** ``decide_call`` runs once ahead
of the items and ``decide_item`` once per item. That is ADR-0002's *caller-level
refusals are whole-call; item-level refusals are per-item*, and with more than
one item on the call it is mechanical rather than stylistic: ``role_missing`` is
a ``-31010``, a JSON-RPC error is the response rather than a line inside one, and
a batch that reached it per item would produce N answers layer 1 cannot render.

**Rejection is the same authorization decision as approval**, so it is a
``decision`` argument rather than a second tool: a separate one would add a
``tools/list`` row and no authorization behaviour, and both outcomes are equally
terminal.
"""

from decimal import Decimal
from typing import Any, Final

from mcp_erp.authorization import Action, Capability, Principal, Reason
from mcp_erp.purchase_to_pay.purchase_order import DECISIONS_SCHEMA
from mcp_erp.purchase_to_pay.reasons import OVER_THRESHOLD, SEGREGATION_OF_DUTIES
from mcp_erp.purchase_to_pay.requisition import Requisition

NAME: Final = "approve_requisition"
"""The tool's name on the wire, and the key layer 1's registry holds it under."""

TITLE: Final = "Approve requisition"

DESCRIPTION: Final = (
    "Approve or reject one or more purchase requisitions, each decided on its own. "
    "Deciding requires a role the server resolves for itself, the amount decides "
    "which role suffices, and nobody may decide a requisition they raised. "
    "A decision is final: a requisition that has been decided cannot be decided again."
)
"""What a model reads before calling.

Four sentences of authorization behaviour, because all four are things a model
will otherwise discover by retrying. Naming *each decided on its own* is what
stops a client reading a result marked in error as a call that did nothing;
naming *a role the server resolves* is what stops it treating the missing-role
refusal as a scope problem; naming the submitter rule is what makes *route to a
different person* the obvious move rather than a discovery; and naming finality
is what stops a retry loop against a decided row.

It describes the shape of the API and not the contents of the database: no
threshold value, no centre, no names.
"""

APPROVE: Final = "approve"
REJECT: Final = "reject"

DECISIONS: Final = (APPROVE, REJECT)
"""The two legal values, in the order the schema publishes them.

A tuple rather than two literals in a schema, because the handler enforces this
rule and must enforce **the declared one**: nothing on this stack validates
arguments against a declared ``inputSchema``, so a second reading of the same
vocabulary is a second place for it to drift.
"""

THRESHOLD: Final = Decimal("5000.00")
"""ADR-0003's €5,000. **At or below**, ``approver`` suffices; above, it does not.

A ``Decimal`` because the amount it is compared against is one — the column is
``numeric(12, 2)`` and binary floating point cannot represent what an accounting
amount means, least of all at a boundary a role changes on.

The comparison is ``>``, so the boundary is inclusive on the cheaper side. That
is ADR-0003's wording rather than an interpretation of it, and one cent is the
whole of what separates the two roles.
"""

MAXIMUM_BATCH: Final = 20
"""The most rows one call may name, and the one constraint here ADR-0002 did not set.

A batch is N writes inside one request, and a declared list with no upper bound
is a request whose cost the caller chooses. The ceiling is not a capacity claim —
it is a bound, stated where the rule that generates rows is stated, and it is
generous enough that nothing this exhibit demonstrates comes near it: the seed
renders one requisition per matrix row that names a ``given``, seventeen rows in
the whole organisation. The one call that exceeds the ceiling is the one written
to: ``test_a_list_the_schema_forbids_is_a_protocol_error_and_not_a_refusal``
posts twenty-one identifiers, and expects ``-32602``.

Declared in the schema *and* enforced by the handler, because nothing on this
stack validates arguments against a published ``inputSchema`` — the same reason
:data:`DECISIONS` is a tuple the handler matches against rather than two literals
in a document.
"""

INPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "ids": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": MAXIMUM_BATCH,
        },
        "decision": {"enum": list(DECISIONS)},
    },
    "required": ["ids", "decision"],
    "additionalProperties": False,
}
"""Which rows, and which way. Nothing else, and the absences are the design.

No ``amount``: it is a fact about the row the server already holds, and a caller
who could restate it could restate it wrongly — the threshold would then be
decided on an argument rather than on the requisition. No ``cost_centre``, for
the reason every schema here omits one: the partition is server-derived, and no
schema anywhere enumerates the organisation's centres. No approver identity: it
is the token's subject, which is what makes the submitter rule a check against a
position on the chain rather than against something the caller supplied.

And no per-item ``decision``: see the module docstring. One decision for the
whole list is what makes this one call rather than N calls posted together.
"""

OUTPUT_SCHEMA: Final[dict[str, Any]] = DECISIONS_SCHEMA
"""The rows as decided, and the purchase orders the approvals emitted.

Declared beside the entity it renders rather than here, so the tool that changes
a requisition's status describes that row with the same document
``list_requisitions`` and ``get_requisition`` read one through — and so that the
two bodies a call can answer with are declared once, from the same description of
one decision.
"""


def refuse_over_threshold(principal: Principal, resource: Requisition) -> Reason | None:
    """Refuse an amount above the threshold unless the caller's role has no limit.

    Reads ``amount``, which layer 2 never sees — the rule is parameterised on
    ``Requisition`` precisely so it can, and layer 2 still reads only the one
    member of the ``Resource`` protocol.

    ``unlimited_approver`` rather than *a more senior role*: the role has no upper
    limit, which is why it also covers the small ones and why nobody in the cast
    needs to hold both.
    """
    if resource.amount > THRESHOLD and "unlimited_approver" not in principal.roles:
        return OVER_THRESHOLD
    return None


def refuse_own_requisition(principal: Principal, resource: Requisition) -> Reason | None:
    """Refuse the person who raised this requisition — the first separation edge.

    Tested against ``submitted_by``, which is a **position occupied once on one
    chain** rather than a role held standing. That distinction is the reason the
    check is an identity comparison and not a role one: an approver is refused on
    exactly one row, the one they raised, and holding every role in the
    organisation would not change it.
    """
    if principal.subject == resource.submitted_by:
        return SEGREGATION_OF_DUTIES
    return None


ACTION: Action[Requisition] = Action(
    namespace="erp",
    capability=Capability.DECIDE,
    required_roles=frozenset({"approver", "unlimited_approver"}),
    rules=(refuse_over_threshold, refuse_own_requisition),
    partition_bypass=frozenset(),
)
"""What ``approve_requisition`` declares — the most configured of the five.

``capability`` is ``decide`` rather than ``approve``: all three capability words
are domain-free, and ``approve`` would have been layer 3 wearing a layer-2 label
(ADR-0012). It is also what makes ``erp.decide`` cover rejection without a second
scope.

``required_roles`` holds **both** deciding roles, because the gate is satisfied by
holding *at least one* — the same semantics the realm's own scope mapping uses,
where ``erp.decide`` maps to ``approver`` and ``unlimited_approver`` alike.
Naming only ``approver`` would refuse Ingrid Holm, who holds the unlimited role
and not that one, and the above-threshold branch she exists to make reachable
would be unreachable through the tool that owns it.

``rules`` **in the order they are evaluated**, and the order is a declaration
about which refusal a caller sees rather than a detail. The threshold is declared
first, and CC-4300 is why: it holds one Person, so every requisition charged to
it is submitted by the only Person who could decide it. Declaring the submitter
edge first would answer ``segregation_of_duties`` there for ever, and the
capability hole ADR-0003 put in that centre — a remedy naming a class of action
with no available human to fill it — would be unreachable, hidden by the order
two rules happen to be written in rather than by anything the design says.

``partition_bypass`` is **empty**, and it is empty because ``decide`` is not
``read``. ADR-0013 states the rule directly — the field *"holds `{auditor}` on
the two read tools and is empty on the three writes"* — and ADR-0007 gives the
reason: ``auditor`` *"widens which rows are returned, it does not grant reading"*,
so breadth is a read widening and never a write grant. **The wrong value here
would be invisible to every test this project will run.** Row scoping runs after
the role gate, and nobody in the cast holds ``auditor`` together with a deciding
role, so ``{auditor}`` here grants nothing to anybody today and would ship green
and stay green until somebody's roles changed. Nothing in the type objects
either; ADR-0013 records that as a known cost and #34 declined to close it in
layer 2, because a check reading *bypass is legal only on a read* would be layer
2 legislating a rule the ADR deliberately left open on a field layer 3 owns.

The explicit annotation fixes ``R``. Here the rules would infer it, and it is
written anyway so that the three shipped declarations read the same.
"""

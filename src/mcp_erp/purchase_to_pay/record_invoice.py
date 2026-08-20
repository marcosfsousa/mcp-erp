"""``record_invoice`` — the second separation edge, and where scope meets role.

The smallest of the five and the last of them. It earns its place on one
authorization behaviour: ADR-0003 records that with a single separation edge this
tool *"stops earning its place"*, and the second edge is what it is here for.

**The resource is the ``PurchaseOrder``** — what ADR-0003 already tests against —
and the invoice does not exist at decision time, which is ADR-0013's *the thing
acted against, never the thing created* on the last tool to state it. This is
also the call that makes the hydration step's ``action`` parameter select an
entity: every earlier caller named a ``Requisition``, and #40 kept the parameter
against exactly this ticket.

**Where the scope and the role visibly intersect.** ``erp.write`` is ungated by
any role mapping and had to be — ADR-0003 gates submitting by scope alone, so a
mapping there would lock every submitter out of a scope they are entitled to. The
consequence lands here: one coarse scope covers both writes, and the ERP role
decides which of the two a caller reaches. What stops the write on this tool is
the role check, not the scope.

**Terminal, and the second half of a promise.** An order takes exactly one
invoice at full value, so a second recording answers ``already_invoiced`` and
writes nothing — the other end of ADR-0002's guarantee that a model retrying a
whole batch cannot double-write, whose first end is ``already_decided``.

**There is no threshold, and no rule order to decide.** An invoice carries no
amount, because the order fixes one; there is one relationship rule, so the
tuple's order is not a declaration about which refusal a caller sees. That is the
one thing :mod:`~mcp_erp.purchase_to_pay.approve_requisition` has that this does
not.
"""

from typing import Any, Final

from mcp_erp.authorization import Action, Capability, Principal, Reason
from mcp_erp.purchase_to_pay.invoice import RECORDED_SCHEMA
from mcp_erp.purchase_to_pay.purchase_order import PurchaseOrder
from mcp_erp.purchase_to_pay.reasons import SEGREGATION_OF_DUTIES

NAME: Final = "record_invoice"
"""The tool's name on the wire, and the key layer 1's registry holds it under."""

TITLE: Final = "Record invoice"

DESCRIPTION: Final = (
    "Record the invoice for one approved purchase order. "
    "Recording requires a role the server resolves for itself, and nobody may "
    "record the invoice for a purchase order they approved. "
    "An order takes exactly one invoice: an order already invoiced cannot be invoiced again."
)
"""What a model reads before calling.

Three sentences of authorization behaviour, on the same rule
``approve_requisition``'s description keeps: name what a model would otherwise
discover by retrying. Naming *a role the server resolves* is what stops a client
reading the role refusal as a scope problem — the trap is sharper here than
anywhere, because the scope really was granted and really does reach another
tool. Naming the approver rule makes *route to a different person* the obvious
move. Naming finality stops a retry loop against a billed order.

It describes the shape of the API and not the contents of the database: no role
names, no centres, no people.
"""

INPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"id": {"type": "string"}},
    "required": ["id"],
    "additionalProperties": False,
}
"""One argument, and this schema is where the governing rule shows most.

No ``amount``: the order it bills fixes one, and an order takes exactly one
invoice at full value, so a caller could only restate it — wrongly, if they chose.
ADR-0003 considered checking one and rejected both readings, the cap as domain
fraud rather than authorization and the exact match as input validation wearing an
authorization costume. No ``vendor`` and no supplier reference, for the same
reason. No ``cost_centre``, for the reason every schema here omits one. And no
recorder identity: it is the token's subject, which is what makes the second edge
a check against a position on the chain rather than against something the caller
supplied.
"""

OUTPUT_SCHEMA: Final[dict[str, Any]] = RECORDED_SCHEMA
"""The order as billed, and the invoice the recording created.

Declared beside the entity it renders rather than here, on the same rule
``approve_requisition``'s output follows: the tool that changes an order's status
describes that order with the same document that emitted it.
"""


def refuse_own_approval(principal: Principal, resource: PurchaseOrder) -> Reason | None:
    """Refuse the person who approved this order — the second separation edge.

    Tested against ``approved_by``, which is a **position occupied once on one
    chain** rather than a role held standing, exactly as ``submitted_by`` is one
    link up. That distinction is why the check is an identity comparison and not
    a role one, and here it is load-bearing rather than merely principled:
    ADR-0003's cast gives Ingrid Holm ``unlimited_approver`` and ``invoice_clerk``
    together, so a rule reading *does the caller hold the approving role* would
    refuse her on every order in her centre instead of on the one she approved.

    It reads a member layer 2 never sees. The rule is parameterised on
    ``PurchaseOrder`` precisely so it can, and layer 2 still reads only the one
    member of the ``Resource`` protocol.

    **The same ``Reason`` as the first edge, deliberately.** Both are the same
    requirement — two steps that check each other are performed by different
    people — and a caller's remedy is identical: a different person acts. A
    second value would name the rule that fired rather than what would fix it,
    which is the division ADR-0002 built the vocabulary around.
    """
    if principal.subject == resource.approved_by:
        return SEGREGATION_OF_DUTIES
    return None


ACTION: Action[PurchaseOrder] = Action(
    namespace="erp",
    capability=Capability.WRITE,
    required_roles=frozenset({"invoice_clerk"}),
    rules=(refuse_own_approval,),
    partition_bypass=frozenset(),
)
"""What ``record_invoice`` declares — the tool where scope and role visibly intersect.

``capability`` is ``write``, the **same capability ``submit_requisition``
declares**, and that is the design rather than a collision. ADR-0012 chose coarse
verbs so that precision moves to the side that can carry it: ``erp.write`` covers
both writes, and the ERP role decides which of the two a caller actually reaches.

``required_roles`` holds ``invoice_clerk`` alone, and it is the half of that
intersection that does the work. ADR-0007 records why the scope could not carry
it: ``erp.write`` *"cannot be gated"* at issuance, because ADR-0003 gates
submitting by scope alone and a role mapping there would lock every submitter out
of a scope they are entitled to. Ungated is therefore not a concession — it is
what leaves this tool with a role check that is observably the thing stopping the
write. Priya Raman holds the scope, submits with it, and is refused here.

``rules`` is one rule long, where ``approve_requisition`` declares two. There is
no threshold here: an order takes exactly one invoice at full value, so there is
no amount to compare and nothing for a second rule to read. With one rule the
tuple's order is not a decision, which is the one thing the neighbouring
declaration has that this does not.

``partition_bypass`` is **empty**, and ADR-0013 names *this tool by name* as the
one a reader gets wrong: *"A reader who adds `{auditor}` to `record_invoice` for
symmetry grants cross-partition invoice recording, and nothing in the type would
object."* The field holds ``{auditor}`` on the two read tools and is empty on the
three writes, because breadth is a read widening and never a write grant —
ADR-0007 puts it as ``auditor`` *"widens which rows are returned, it does not
grant reading"*, and ADR-0003 as *"`auditor` reads all three and writes nothing."*

**The wrong value here would be invisible to the decision matrix**, which is why
the reasoning is in the declaration rather than in a test. Row scoping runs after
the role gate, so a non-empty bypass does not by itself let Anna Lindqvist record
an invoice: she holds ``auditor`` and not ``invoice_clerk``. Rafael Costa holds
``invoice_clerk`` and not ``auditor``. Nobody in the cast holds both, so no matrix
row reaches the defect — it would ship green and stay green until somebody's roles
changed. #34 declined to close it in layer 2 with a constructor check, because
*bypass is legal only on a read* would be layer 2 legislating a rule the ADR
deliberately left open on a field whose whole point is that layer 3 owns it.

The explicit annotation fixes ``R``, as the other four declarations do. Here it
is doing more than matching them: it is what makes
:func:`~mcp_erp.purchase_to_pay.handlers.load` hydrate a purchase order for this
tool, and a requisition for the two decided against one.
"""

"""Layer 3's own refusal values, declared in the record layer 2 owns.

ADR-0013: *"Each layer declares its own instances — layer 2 its three, layer 3
its four. There is no lookup table anywhere."* This is layer 3's half. Nothing in
:mod:`mcp_erp.authorization` enumerates these values, nothing had to be
registered anywhere for them to work, and every one of them states its own wire
shape, its own remedy and both retry booleans at the point of declaration.

**Three of the four are here.** ``already_invoiced`` is ``record_invoice``'s and
arrives with it (#42); declaring it early would be a value in the closed
vocabulary that no tool can produce, which is the thing an exhibit about
authorization can least afford.

``Remedy``, ``DenialClass`` and both retry booleans stay wholly in layer 2 — they
describe client behaviour rather than domain facts, and ADR-0004's first coupling
is what keeps them there. What layer 3 supplies is the *value* and the choice of
which shape it takes.
"""

from mcp_erp.authorization import DenialClass, Reason, Remedy

SEGREGATION_OF_DUTIES = Reason(
    value="segregation_of_duties",
    denial_class=DenialClass.TOOL_RESULT,
    remedy=Remedy.DIFFERENT_PERSON,
    retry_identical_helps=False,
    retry_as_other_person_helps=True,
)
"""The caller occupies another position on this chain already.

**The reason the vocabulary has two retry booleans.** *Do not retry* is right for
every other refusal here and wrong for this one: retrying as a different person
is the correct move, and a single boolean would have flattened the one case the
domain exists to demonstrate.

A tool result rather than a protocol error, because it is precisely what a model
should act on by routing elsewhere — the specification's own division of labour,
where a tool execution error is *"actionable feedback that language models can
use to self-correct and retry."*
"""

OVER_THRESHOLD = Reason(
    value="over_threshold",
    denial_class=DenialClass.TOOL_RESULT,
    remedy=Remedy.DIFFERENT_PERSON,
    retry_identical_helps=False,
    retry_as_other_person_helps=True,
)
"""The amount is above what the caller's role decides at.

**The remedy names a class of action, not an available human**, and this is the
value that proves the distinction is real rather than described: ADR-0003 leaves
two cost centres with nobody holding ``unlimited_approver``, so this refusal
truthfully reports ``retry_as_other_person_helps: true`` in a centre where no such
person exists. Promising otherwise is how an authorization system comes to
promise what the organisation cannot deliver.

Byte-identical in shape to :data:`SEGREGATION_OF_DUTIES` and a different value,
which is the point of a reason being a record: two refusals a client handles the
same way, and a caller can still tell which rule fired.
"""

ALREADY_DECIDED = Reason(
    value="already_decided",
    denial_class=DenialClass.TOOL_RESULT,
    remedy=Remedy.NONE,
    retry_identical_helps=False,
    retry_as_other_person_helps=False,
)
"""The requisition has been approved or rejected already.

Named for the decision rather than for approval: ``approve_requisition`` carries
``decision: "reject"``, rejection is equally terminal, and ``already_approved``
did not cover it (ADR-0003 §Consequences).

**Both retry booleans are false and the remedy is ``none``**, because a decided
row is decided for everybody — there is no person and no token that makes it
decidable again. That is what ADR-0002's promise rests on: a model that ignores
every field and retries cannot double-approve.
"""

REASONS: frozenset[Reason] = frozenset({SEGREGATION_OF_DUTIES, OVER_THRESHOLD, ALREADY_DECIDED})
"""Layer 3's declared set, in full.

ADR-0003's *exactly one dedicated test* enumerates the union of this and layer
2's three. Because this half lives in the package the ejection command deletes,
that test belongs in ``tests/matrix/`` and arrives with #43.
"""

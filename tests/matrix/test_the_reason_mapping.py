"""ADR-0002's reason-to-shape mapping, asserted exactly once and over both layers.

ADR-0003 asked for *"exactly one dedicated test"*: rows state a `reason` and
nothing else, wire shape and remedy and both retry booleans are derived from it,
and the derivation is checked in one place so that changing the mapping is a
one-line change rather than a sweep through every expectation the table carries.
How many that is lives in `matrix.yaml`'s `meta` block and is asserted against
the rows by `test_the_matrix_holds_together.py`, which is why it is not written
out here.

**It lives here rather than in `tests/authorization/`** because the union has two
halves and only one of them survives ejection. Layer 2 declares three reasons and
layer 3 four, with **no lookup table anywhere** — every instance states its own
shape at the point of declaration — so a test over the union necessarily imports
the package `rm -rf src/mcp_erp/purchase_to_pay` deletes. Putting it in the
directory the ejection job runs would either break that job or quietly narrow the
test to three of seven.

`tests/authorization/test_reasons.py` gave up two assertions to this file in the
same commit, for the same reason ADR-0003 wanted one test: two places asserting a
mapping is two places for it to disagree with itself.

**The table below is where ADR-0002's mapping is checked against the
declarations**, and it is the only place that comparison is made. It is not the
only place the mapping is written down: `tests/wire/test_approve_requisition.py`
and `tests/wire/test_record_invoice.py` spell refusal bodies out as literals, so
a change to a remedy or a retry boolean reddens them too. That is a cost each of
those modules records and accepts — a suite that exists to show what the wire
looks like shows nothing if the body is a lookup. Every other suite reads the
body off the records (#87).
"""

from mcp_erp.authorization import REASONS as AUTHORIZATION_REASONS
from mcp_erp.authorization import DenialClass, Reason, Remedy
from mcp_erp.purchase_to_pay.reasons import REASONS as DOMAIN_REASONS

UNION = AUTHORIZATION_REASONS | DOMAIN_REASONS
"""Every reason either layer declares. Seven, and the count is derived here."""

MAPPING: dict[str, tuple[DenialClass, Remedy, bool, bool]] = {
    # value                   denial class                remedy                    identical  other
    "insufficient_scope": (DenialClass.CHALLENGE, Remedy.REAUTHORIZE, False, False),
    "role_missing": (DenialClass.PROTOCOL_ERROR, Remedy.ADMINISTRATOR_GRANT, False, False),
    "not_found": (DenialClass.TOOL_RESULT, Remedy.NONE, False, False),
    "segregation_of_duties": (DenialClass.TOOL_RESULT, Remedy.DIFFERENT_PERSON, False, True),
    "over_threshold": (DenialClass.TOOL_RESULT, Remedy.DIFFERENT_PERSON, False, True),
    "already_decided": (DenialClass.TOOL_RESULT, Remedy.NONE, False, False),
    "already_invoiced": (DenialClass.TOOL_RESULT, Remedy.NONE, False, False),
}
"""ADR-0002's table as this repository ships it, keyed by the value a row states.

Read down the third column and the vocabulary earns its second boolean:
*different person* is the remedy for exactly two of the seven, and both of them
are relationship rules — which is what a single `retry` boolean would have
flattened, in the one case the domain exists to demonstrate.

Read down the second and the three shapes are each reached: a `403` carrying a
challenge, a `-31010` a `403` would lie about, and a tool result a model can
self-correct on. A shape no reason reaches would be a rendering in layer 1 that
nothing can produce.
"""


def _shape(reason: Reason) -> tuple[DenialClass, Remedy, bool, bool]:
    """The four derived fields of one reason, as the record states them."""
    return (
        reason.denial_class,
        reason.remedy,
        reason.retry_identical_helps,
        reason.retry_as_other_person_helps,
    )


def test_the_union_of_both_layers_maps_to_the_shapes_adr_0002_fixed() -> None:
    """The whole mapping, in both directions, over both declared sets.

    Set equality on the keys is what makes this a closed vocabulary rather than a
    checklist: a reason declared and left out of the table fails here, and a row
    in the table that no layer declares fails here too. A one-directional
    assertion would let either half rot.
    """
    assert {reason.value for reason in UNION} == set(MAPPING)

    for reason in UNION:
        assert _shape(reason) == MAPPING[reason.value], reason.value


def test_the_two_declared_sets_are_disjoint_and_neither_registers_with_the_other() -> None:
    """Seven values, three from layer 2 and four from layer 3, and no value twice.

    A value declared in both layers would type-check, ship, and give one of the
    two records the last word depending on which set a reader consulted. Nothing
    registers anything anywhere, so there is no registry for a duplicate to be
    caught by — which is why it is caught here.
    """
    assert len(AUTHORIZATION_REASONS) == 3
    assert len(DOMAIN_REASONS) == 4
    assert not AUTHORIZATION_REASONS & DOMAIN_REASONS
    assert len({reason.value for reason in UNION}) == 7


def test_every_denial_class_and_every_remedy_is_reached() -> None:
    """Layer 1 renders on the shape alone, so a shape nothing reaches is dead code.

    The same argument one column along for `Remedy`: a class of action no refusal
    ever names is a word in a closed vocabulary that the exhibit cannot
    demonstrate, which is the thing ADR-0003 refused to let `already_invoiced` be
    until the tool that produces it shipped.
    """
    assert {reason.denial_class for reason in UNION} == set(DenialClass)
    assert {reason.remedy for reason in UNION} == set(Remedy)

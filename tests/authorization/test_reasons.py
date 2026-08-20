"""A reason is a record, the vocabularies are closed, and nothing maps between them.

These tests assert the *construction*: that a reason is a five-field frozen
record, that layer 2 declares three of them, that the two enumerations it owns
are closed, and that a domain can declare its own without registering it
anywhere.

**What each reason maps to is deliberately not here, since #43.** ADR-0003 asked
for the reason-to-shape mapping in *exactly one dedicated test*, and the set it
has to be asserted over is the **union** of layer 2's three and layer 3's four —
which cannot be enumerated from a directory that survives ejection. So
`tests/matrix/test_the_reason_mapping.py` owns it whole, and the two assertions
that used to stand here — the three denial classes and their remedies, and both
retry booleans on all three — went with it. Two places asserting a mapping is two
places for it to disagree with itself, and the cost is stated plainly: the
ejected run no longer checks the shapes, because the shapes are not a layer-2
fact on their own.
"""

from dataclasses import fields, is_dataclass

from declarations import SAME_PERSON

from mcp_erp.authorization import (
    INSUFFICIENT_SCOPE,
    NOT_FOUND,
    REASONS,
    ROLE_MISSING,
    DenialClass,
    Reason,
    Remedy,
)


def test_a_reason_is_a_frozen_record_of_five_fields() -> None:
    """Nothing can name a reason without also stating what it does to a client."""
    assert is_dataclass(Reason)
    assert [field.name for field in fields(Reason)] == [
        "value",
        "denial_class",
        "remedy",
        "retry_identical_helps",
        "retry_as_other_person_helps",
    ]


def test_layer_2_declares_exactly_three_reasons() -> None:
    """The set that survives ejection. Layer 3's four are declared in layer 3."""
    assert REASONS == {INSUFFICIENT_SCOPE, ROLE_MISSING, NOT_FOUND}
    assert {reason.value for reason in REASONS} == {
        "insufficient_scope",
        "role_missing",
        "not_found",
    }


def test_the_remedy_vocabulary_is_closed_at_four() -> None:
    """A remedy names a class of action, never an available human."""
    assert [remedy.value for remedy in Remedy] == [
        "reauthorize",
        "administrator_grant",
        "different_person",
        "none",
    ]


def test_the_denial_class_vocabulary_is_closed_at_three() -> None:
    """Layer 1 keys on this and learns nothing else about why a refusal happened."""
    assert [denial_class.value for denial_class in DenialClass] == [
        "challenge",
        "protocol_error",
        "tool_result",
    ]


def test_a_domain_declares_its_own_reason_without_registering_it() -> None:
    """The stand-in domain's reason works unchanged, and layer 2 does not know it.

    A registry of rows contributed at composition would put this failure at
    request time rather than import time; there is no registry, so there is
    nothing to be missing from.
    """
    assert SAME_PERSON not in REASONS
    assert SAME_PERSON.remedy is Remedy.DIFFERENT_PERSON
    assert SAME_PERSON.retry_as_other_person_helps

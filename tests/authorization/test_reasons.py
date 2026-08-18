"""A reason is a record, the vocabularies are closed, and nothing maps between them.

The mapping from a reason to its wire shape was a derivation in ADR-0002; here
it is a construction invariant. These tests assert the invariant rather than
re-deriving the table: that each reason states its own shape, that layer 2
declares three of them, and that no lookup exists anywhere for a fourth to be
missing from.
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


def test_the_three_records_are_the_three_denial_classes() -> None:
    """Refusal shape follows the remedy, and the three shapes are all reachable."""
    assert INSUFFICIENT_SCOPE.denial_class is DenialClass.CHALLENGE
    assert INSUFFICIENT_SCOPE.remedy is Remedy.REAUTHORIZE

    assert ROLE_MISSING.denial_class is DenialClass.PROTOCOL_ERROR
    assert ROLE_MISSING.remedy is Remedy.ADMINISTRATOR_GRANT

    assert NOT_FOUND.denial_class is DenialClass.TOOL_RESULT
    assert NOT_FOUND.remedy is Remedy.NONE


def test_no_layer_2_reason_is_worth_retrying() -> None:
    """Both booleans false on all three, and ``not_found`` is the load-bearing one.

    ``retry_as_other_person_helps`` true on ``not_found`` would confirm that the
    row exists and somebody else can see it, which is the existence oracle the
    indistinguishable refusal is there to prevent.
    """
    for reason in REASONS:
        assert not reason.retry_identical_helps
        assert not reason.retry_as_other_person_helps


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

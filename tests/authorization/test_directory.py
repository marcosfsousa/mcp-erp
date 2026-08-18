"""The directory resolves the two stages into one principal, and a miss yields none.

After ejection an empty directory is the normal state, which is why the miss is
asserted here rather than at the wire — it is the case this suite meets most
often once the rows are gone.
"""

import pytest
from declarations import (
    ALL_SCOPES,
    DIRECTORY_ROWS,
    ISSUER,
    OBSERVER,
    REVIEWER,
    claims_for,
)

from mcp_erp.authorization import (
    DIRECTORY_MISS,
    ROLE_MISSING,
    Claims,
    DenialClass,
    DirectoryEntry,
    Principal,
    PrincipalDirectory,
    Remedy,
)


def test_a_hit_resolves_both_stages_into_one_principal() -> None:
    """Scopes come from the token; roles and partition come from the directory."""
    directory = PrincipalDirectory(DIRECTORY_ROWS)

    principal = directory.lookup(claims_for(REVIEWER.subject))

    assert principal == REVIEWER


def test_the_same_person_under_a_narrower_token_is_a_different_principal() -> None:
    """The two halves vary independently, which is why they are one record."""
    directory = PrincipalDirectory(DIRECTORY_ROWS)

    narrow = directory.lookup(claims_for(REVIEWER.subject, frozenset({"review.read"})))
    wide = directory.lookup(claims_for(REVIEWER.subject, ALL_SCOPES))

    assert narrow != wide
    assert narrow is not None and wide is not None
    assert narrow.roles == wide.roles
    assert narrow.granted_scopes < wide.granted_scopes


def test_a_miss_produces_no_principal_at_all() -> None:
    """Not a principal with no roles — the shortcut that fails open."""
    directory = PrincipalDirectory(DIRECTORY_ROWS)

    assert directory.lookup(claims_for("nobody-in-the-directory")) is None


def test_an_empty_directory_misses_everyone() -> None:
    """The state layer 2 is in the moment the domain is deleted."""
    assert PrincipalDirectory(()).lookup(claims_for(REVIEWER.subject)) is None


def test_a_miss_refuses_with_role_missing_and_not_a_fourth_reason() -> None:
    """One reason, by construction rather than by two records agreeing.

    A fourth reason was rejected because its record would be identical to this
    one's, so the record is what the test holds: the same denial class, the same
    remedy, both retry booleans false. Swapping the alias for a new ``Reason``
    carrying those same five values would satisfy the identity check below only
    by being the same object, which is the claim.
    """
    assert DIRECTORY_MISS is ROLE_MISSING
    assert DIRECTORY_MISS.denial_class is DenialClass.PROTOCOL_ERROR
    assert DIRECTORY_MISS.remedy is Remedy.ADMINISTRATOR_GRANT
    assert not DIRECTORY_MISS.retry_identical_helps
    assert not DIRECTORY_MISS.retry_as_other_person_helps


def test_the_key_is_the_subject_scoped_by_issuer() -> None:
    """A subject known at one issuer is a stranger at another."""
    directory = PrincipalDirectory(DIRECTORY_ROWS)
    elsewhere = Claims(
        issuer="https://issuer.example/realms/somewhere-else",
        subject=REVIEWER.subject,
        granted_scopes=ALL_SCOPES,
    )

    assert directory.lookup(elsewhere) is None


def test_a_partition_is_never_absent_from_a_resolved_principal() -> None:
    """Non-optional, which is what makes the empty-principal shortcut unwritable."""
    directory = PrincipalDirectory(DIRECTORY_ROWS)

    for subject in (REVIEWER.subject, OBSERVER.subject):
        principal = directory.lookup(claims_for(subject))
        assert isinstance(principal, Principal)
        assert principal.partition


def test_a_duplicated_row_fails_at_construction() -> None:
    """A rendering defect, so it fails at startup and not on the request that hits it."""
    duplicate = DirectoryEntry(
        issuer=ISSUER,
        subject=REVIEWER.subject,
        roles=frozenset({"observer"}),
        partition="P-9",
    )

    with pytest.raises(ValueError, match="duplicate directory row"):
        PrincipalDirectory([*DIRECTORY_ROWS, duplicate])


def test_the_rows_cannot_be_edited_after_construction() -> None:
    """Held immutable in memory, so a request cannot change who anybody is."""
    entries = list(DIRECTORY_ROWS)
    directory = PrincipalDirectory(entries)
    entries.clear()

    assert directory.lookup(claims_for(REVIEWER.subject)) == REVIEWER

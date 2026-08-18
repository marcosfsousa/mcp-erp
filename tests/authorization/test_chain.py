"""The chain evaluates in one place, in the fixed order.

Order is the property under test, not merely which refusal comes back: each case
below is arranged so that **more than one step would refuse**, and asserts that
the earlier one is what the caller sees. A test that only ever fails one step at
a time passes against a chain in any order at all.
"""

from declarations import (
    ALL_SCOPES,
    DECIDE_ROW,
    DECIDE_SCOPE,
    FOREIGN_ROW,
    LIST_ROWS,
    LONG_ROW,
    OBSERVER,
    OUTSIDER,
    OWN_LONG_ROW,
    OWN_ROW,
    RAISE_ROW,
    REVIEWER,
    ROW,
    SAME_PERSON,
    TOO_LONG,
    UNLIMITED,
    UNROLED,
    Row,
    refuse_long_row,
    refuse_own_row,
)

from mcp_erp.authorization import (
    INSUFFICIENT_SCOPE,
    NOT_FOUND,
    ROLE_MISSING,
    Principal,
    decide_call,
    decide_item,
    permits_scope,
)


def test_a_permitted_item_reaches_the_end_of_the_chain() -> None:
    """Every step passes, so the decision carries no reason at all."""
    decision = decide_item(REVIEWER, DECIDE_ROW, ROW)

    assert decision.permitted
    assert decision.reason is None


def test_scope_is_checked_before_role() -> None:
    """A principal failing both steps sees the scope refusal, not the role one."""
    scopeless = Principal(
        issuer=UNROLED.issuer,
        subject=UNROLED.subject,
        granted_scopes=ALL_SCOPES - {DECIDE_SCOPE},
        roles=frozenset(),
        partition=UNROLED.partition,
    )

    assert decide_call(scopeless, DECIDE_ROW).reason is INSUFFICIENT_SCOPE
    assert decide_item(scopeless, DECIDE_ROW, ROW).reason is INSUFFICIENT_SCOPE


def test_role_is_checked_before_row_scoping() -> None:
    """A roleless principal outside the partition sees the role refusal.

    The reverse order would answer ``not_found``, which reads to a client as a
    row that does not exist rather than as a grant an administrator can make.
    """
    stranger = Principal(
        issuer=OUTSIDER.issuer,
        subject=OUTSIDER.subject,
        granted_scopes=ALL_SCOPES,
        roles=frozenset(),
        partition="P-9",
    )

    assert decide_item(stranger, DECIDE_ROW, ROW).reason is ROLE_MISSING


def test_row_scoping_is_checked_before_the_relationship_rules() -> None:
    """A foreign row that a rule would also refuse comes back ``not_found``.

    The other order would tell a caller *why* a row they may not see was
    refused, which discloses that it exists.
    """
    foreign_and_long = Row(partition="P-9", raised_by=REVIEWER.subject, words=900)

    assert decide_item(REVIEWER, DECIDE_ROW, foreign_and_long).reason is NOT_FOUND


def test_the_relationship_rules_run_in_the_declared_order() -> None:
    """A row both rules refuse comes back with the first rule's reason."""
    assert DECIDE_ROW.rules == (refuse_own_row, refuse_long_row)
    assert decide_item(REVIEWER, DECIDE_ROW, OWN_LONG_ROW).reason is SAME_PERSON


def test_each_relationship_rule_refuses_on_its_own() -> None:
    """Both rules fire, so the ordering assertion above is about order alone."""
    assert decide_item(REVIEWER, DECIDE_ROW, OWN_ROW).reason is SAME_PERSON
    assert decide_item(REVIEWER, DECIDE_ROW, LONG_ROW).reason is TOO_LONG


def test_a_rule_reads_a_field_layer_2_never_sees() -> None:
    """The length rule passes for the role that lifts it, on the same row."""
    assert decide_item(UNLIMITED, DECIDE_ROW, LONG_ROW).permitted


def test_holding_any_one_required_role_satisfies_the_gate() -> None:
    """``required_roles`` is "at least one of", the same semantics the realm uses."""
    assert decide_call(REVIEWER, DECIDE_ROW).permitted
    assert decide_call(UNLIMITED, DECIDE_ROW).permitted
    assert decide_call(UNROLED, DECIDE_ROW).reason is ROLE_MISSING


def test_an_action_with_no_required_roles_is_gated_by_scope_alone() -> None:
    """Submitting is scope-only; a principal with no role at all reaches it."""
    assert decide_call(UNROLED, RAISE_ROW).permitted


def test_a_foreign_row_is_refused_and_a_bypass_role_reads_it() -> None:
    """One equality check, plus the roles the action names as bypassing it."""
    assert decide_item(REVIEWER, LIST_ROWS, FOREIGN_ROW).reason is NOT_FOUND
    assert decide_item(OBSERVER, LIST_ROWS, FOREIGN_ROW).permitted


def test_breadth_is_a_read_widening_and_never_a_write_grant() -> None:
    """The same principal, the same row, the two actions differing on one field."""
    assert decide_item(OBSERVER, LIST_ROWS, ROW).permitted
    assert decide_item(OBSERVER, RAISE_ROW, ROW).reason is NOT_FOUND


def test_the_item_path_re_evaluates_the_caller_level_steps() -> None:
    """The N+1 evaluation, asserted rather than left as a comment.

    ``decide_item`` runs steps 1 and 2 itself, so a handler cannot reach an
    item decision that skipped them by calling this entry point directly.
    """
    scopeless = Principal(
        issuer=REVIEWER.issuer,
        subject=REVIEWER.subject,
        granted_scopes=frozenset(),
        roles=REVIEWER.roles,
        partition=REVIEWER.partition,
    )

    assert decide_item(scopeless, DECIDE_ROW, ROW).reason is INSUFFICIENT_SCOPE
    assert decide_item(UNROLED, DECIDE_ROW, ROW).reason is ROLE_MISSING


def test_listing_is_a_strict_prefix_of_the_call_gate() -> None:
    """Where ``permits_scope`` refuses, ``decide_call`` refuses for the same reason.

    Where it permits, the call gate may still refuse — on the role, which is
    what keeps the middle denial class reachable instead of collapsing into a
    tool the caller never saw listed.
    """
    assert permits_scope(UNROLED, DECIDE_ROW)
    assert decide_call(UNROLED, DECIDE_ROW).reason is ROLE_MISSING

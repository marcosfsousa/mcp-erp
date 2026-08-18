"""The scope string is derived, the comparison is exact, and listing reads the token.

The last of those is the one with a proof hanging off it. ``tools/list`` is
cacheable under ``cacheScope: "private"`` because it is a pure function of the
access token; the moment ``permits_scope`` reads a directory-derived field, a
role revocation becomes invisible for up to five minutes on an unchanged token
and nothing else in the code objects. So it is asserted here by watching which
fields the function actually touches, rather than by reading the source and
trusting it.
"""

from dataclasses import dataclass, field, replace
from typing import Any, cast

from declarations import (
    DECIDE_ROW,
    LIST_ROWS,
    RAISE_ROW,
    REVIEWER,
)

from mcp_erp.authorization import Action, Capability, Principal, permits_scope


@dataclass
class _WatchedPrincipal:
    """A principal that records every attribute anything reads off it.

    ``__getattr__`` fires only when normal lookup fails, and this class declares
    none of a principal's fields, so every read of one lands here.
    """

    principal: Principal
    seen: set[str] = field(default_factory=set)

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 — it proxies whatever it is asked for
        """Record the read, then answer it from the real principal."""
        self.seen.add(name)
        return getattr(self.principal, name)


def test_the_scope_string_is_derived_from_the_capability() -> None:
    """Never stored as a literal, so the three artifacts consuming it cannot drift."""
    assert LIST_ROWS.scope == "review.read"
    assert RAISE_ROW.scope == "review.write"
    assert DECIDE_ROW.scope == "review.decide"


def test_no_action_stores_a_scope_string() -> None:
    """``scope`` is a property, not a field — there is nothing to hand-write."""
    assert isinstance(type(LIST_ROWS).scope, property)
    assert "scope" not in {name for name in Action.__dataclass_fields__}


def test_the_capability_vocabulary_is_three_words_owned_by_layer_2() -> None:
    """Layer 3 supplies the namespace token and nothing else about the string."""
    assert [capability.value for capability in Capability] == ["read", "write", "decide"]


def test_the_comparison_is_exact_and_case_sensitive() -> None:
    """A scope that merely resembles the required one does not satisfy it.

    Case and namespace are one deletion — the comparison expression — so both
    variants are asserted against it.
    """
    lookalikes = replace(
        REVIEWER,
        granted_scopes=frozenset({"REVIEW.READ", "audit.read", "review.read.all", "openid"}),
    )

    assert not permits_scope(lookalikes, LIST_ROWS)


def test_an_unrecognised_scope_is_inert() -> None:
    """No unknown-scope code path, no namespace awareness, nothing to fingerprint."""
    noisy = replace(
        REVIEWER,
        granted_scopes=frozenset({"review.read", "openid", "hr.read", "review.admin"}),
    )

    assert permits_scope(noisy, LIST_ROWS)
    assert not permits_scope(noisy, DECIDE_ROW)


def test_scopes_do_not_imply_one_another() -> None:
    """A plain set, and membership is the whole of the filter."""
    decide_only = replace(REVIEWER, granted_scopes=frozenset({DECIDE_ROW.scope}))

    assert permits_scope(decide_only, DECIDE_ROW)
    assert not permits_scope(decide_only, LIST_ROWS)


def test_permits_scope_reads_token_derived_fields_only() -> None:
    """Never roles, never partition. ADR-0002's ``ttlMs`` proof depends on it."""
    watched = _WatchedPrincipal(principal=REVIEWER)

    assert permits_scope(cast(Principal, watched), DECIDE_ROW)
    assert watched.seen <= {"issuer", "subject", "granted_scopes"}
    assert "roles" not in watched.seen
    assert "partition" not in watched.seen


def test_the_watcher_would_notice_a_directory_derived_read() -> None:
    """The guard above is only worth what its instrument is, so prove the instrument."""
    watched = _WatchedPrincipal(principal=REVIEWER)

    assert cast(Principal, watched).roles == REVIEWER.roles
    assert "roles" in watched.seen

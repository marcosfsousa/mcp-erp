"""Inline declarations standing in for layer 3 — deliberately from another domain.

Everything a real domain declares, declared here in a vocabulary this exhibit
does not model: rows in a **content review** tool rather than requisitions. That
is not decoration. The suite these feed runs with layer 3 deleted, so a
declaration naming a requisition would either import the package the ejection
command removes or quietly reintroduce its vocabulary into the layer that must
survive without it.

They are **declarations, not fixtures**: a fixture is generated from a
decision-matrix row and owned by it, where every constant here is hand-written
and stands in for what layer 3 will declare. The ticket that renders the
directory from the seed is a different one, and the chain does not need real
people to be proven domain-free.
"""

from dataclasses import dataclass

from mcp_erp.authorization import (
    Action,
    Capability,
    Claims,
    DenialClass,
    DirectoryEntry,
    Principal,
    Reason,
    Remedy,
)

ISSUER = "https://issuer.example/realms/exhibit"
"""One issuer throughout. The directory key is the subject **scoped by** it."""


@dataclass(frozen=True, slots=True)
class Row:
    """A resource in the stand-in domain: one item awaiting review.

    Satisfies the one-member ``Resource`` protocol through ``partition``, and
    carries two fields layer 2 never sees — the rules below read them, which is
    the whole reason ``Rule`` is parameterised.
    """

    partition: str
    raised_by: str
    words: int


SAME_PERSON = Reason(
    value="same_person",
    denial_class=DenialClass.TOOL_RESULT,
    remedy=Remedy.DIFFERENT_PERSON,
    retry_identical_helps=False,
    retry_as_other_person_helps=True,
)
"""The stand-in domain's segregation-of-duties reason.

Declared here rather than imported, because a domain declaring its own instances
is exactly the property under test: nothing in layer 2 enumerates this value,
and nothing had to be registered anywhere for it to work.
"""

TOO_LONG = Reason(
    value="too_long",
    denial_class=DenialClass.TOOL_RESULT,
    remedy=Remedy.DIFFERENT_PERSON,
    retry_identical_helps=False,
    retry_as_other_person_helps=True,
)
"""The stand-in domain's threshold reason — a second rule, so order is observable."""


def refuse_own_row(principal: Principal, resource: Row) -> Reason | None:
    """Refuse when the caller is the person who raised the row."""
    if principal.subject == resource.raised_by:
        return SAME_PERSON
    return None


def refuse_long_row(principal: Principal, resource: Row) -> Reason | None:
    """Refuse a long row unless the caller holds the unlimited role."""
    if resource.words > 500 and "unlimited_reviewer" not in principal.roles:
        return TOO_LONG
    return None


LIST_ROWS: Action[Row] = Action(
    namespace="review",
    capability=Capability.READ,
    required_roles=frozenset(),
    rules=(),
    partition_bypass=frozenset({"observer"}),
)
"""A read: gated by scope alone, and the one place breadth is granted."""

RAISE_ROW: Action[Row] = Action(
    namespace="review",
    capability=Capability.WRITE,
    required_roles=frozenset(),
    rules=(),
    partition_bypass=frozenset(),
)
"""A write: scope-only like the read, and **empty** bypass. Breadth is a read
widening, never a write grant, so the two differ on exactly that one field."""

DECIDE_ROW: Action[Row] = Action(
    namespace="review",
    capability=Capability.DECIDE,
    required_roles=frozenset({"reviewer", "unlimited_reviewer"}),
    rules=(refuse_own_row, refuse_long_row),
    partition_bypass=frozenset(),
)
"""The full chain: a role gate satisfied by holding either role, two ordered
relationship rules, and no bypass."""

READ_SCOPE = LIST_ROWS.scope
WRITE_SCOPE = RAISE_ROW.scope
DECIDE_SCOPE = DECIDE_ROW.scope
ALL_SCOPES = frozenset({READ_SCOPE, WRITE_SCOPE, DECIDE_SCOPE})

REVIEWER = Principal(
    issuer=ISSUER,
    subject="reviewer-1",
    granted_scopes=ALL_SCOPES,
    roles=frozenset({"reviewer"}),
    partition="P-1",
)
"""Holds every scope and one of the two deciding roles, in partition ``P-1``."""

UNLIMITED = Principal(
    issuer=ISSUER,
    subject="reviewer-2",
    granted_scopes=ALL_SCOPES,
    roles=frozenset({"unlimited_reviewer"}),
    partition="P-1",
)
"""The other deciding role, and the only principal the length rule lets past."""

OUTSIDER = Principal(
    issuer=ISSUER,
    subject="reviewer-3",
    granted_scopes=ALL_SCOPES,
    roles=frozenset({"reviewer"}),
    partition="P-2",
)
"""Everything ``REVIEWER`` has, in another partition."""

OBSERVER = Principal(
    issuer=ISSUER,
    subject="observer-1",
    granted_scopes=ALL_SCOPES,
    roles=frozenset({"observer"}),
    partition="P-2",
)
"""Breadth by role: reads every partition, holds no deciding role."""

UNROLED = Principal(
    issuer=ISSUER,
    subject="unroled-1",
    granted_scopes=ALL_SCOPES,
    roles=frozenset(),
    partition="P-1",
)
"""Every scope, no role at all — the principal the middle denial class exists for."""

ROW = Row(partition="P-1", raised_by="somebody-else", words=100)
"""An ordinary row in ``P-1``, raised by nobody in the cast above."""

OWN_ROW = Row(partition="P-1", raised_by=REVIEWER.subject, words=100)
LONG_ROW = Row(partition="P-1", raised_by="somebody-else", words=900)
OWN_LONG_ROW = Row(partition="P-1", raised_by=REVIEWER.subject, words=900)
"""A row both rules refuse, so the declared order is observable."""

FOREIGN_ROW = Row(partition="P-9", raised_by="somebody-else", words=100)

DIRECTORY_ROWS = (
    DirectoryEntry(
        issuer=ISSUER,
        subject=REVIEWER.subject,
        roles=REVIEWER.roles,
        partition=REVIEWER.partition,
    ),
    DirectoryEntry(
        issuer=ISSUER,
        subject=OBSERVER.subject,
        roles=OBSERVER.roles,
        partition=OBSERVER.partition,
    ),
)


def claims_for(subject: str, scopes: frozenset[str] = ALL_SCOPES) -> Claims:
    """Build the token half of an identity, for a subject the directory may not know."""
    return Claims(issuer=ISSUER, subject=subject, granted_scopes=scopes)

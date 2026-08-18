"""The principal directory, and the lookup step that sits ahead of the chain.

The directory maps an issuer-and-subject pair to a set of roles and a partition.
Layer 2 owns its shape, its implementation and its renderer; layer 3 supplies
only the rows, so identity provisioning survives ejection (ADR-0004, criterion
4). It is held immutable in memory, which is what keeps layer 2 free of a
database dependency and keeps ``tests/authorization`` Docker-free by
construction — the ejection job runs the real implementation rather than a stub.

Lookup is a **named step, not a collaborator**. It runs inside the token
middleware immediately after the token is validated, and the resolved principal
goes into request state for the gates to read. Placing it there rather than at
dispatch is what lets ``tools/list`` and ``tools/call`` share one scope check
(ADR-0006).

**This ticket delivers the function and its types, not the rows.** The committed
data file is rendered from the seed by the identity generator that lands with
it; hand-writing rows here would create data that ticket regenerates. The chain
does not need real people to be proven domain-free.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from mcp_erp.authorization.principal import Claims, Principal
from mcp_erp.authorization.reasons import ROLE_MISSING, Reason

DIRECTORY_MISS: Reason = ROLE_MISSING
"""What a directory miss refuses with — the same reason, not a fourth one.

A fourth reason was considered and rejected: its record would be identical to
``role_missing``'s — the same denial class, the same remedy, both retry booleans
false — so it would amend a closed vocabulary for a distinction carrying no
different remedy. Declaring the alias here rather than leaving the gate to pick
one is what makes "by construction they are one reason, not two" true in code.

The miss itself is asserted in ``tests/authorization``, where it matters most:
after ejection an empty directory is the normal state.
"""


@dataclass(frozen=True, slots=True)
class DirectoryEntry:
    """One directory row: who a token names, and what the server knows about them.

    Roles live here rather than in the domain's person table because they are
    policy facts, not domain facts — a role is resolved server-side per request
    and never carried in the token. Only the partition is duplicated between the
    two, and it is duplicated by generation, which is what a drift check
    polices (ADR-0003).
    """

    issuer: str
    subject: str
    roles: frozenset[str]
    partition: str


class PrincipalDirectory:
    """An immutable directory, keyed by issuer and subject.

    The join is on the standard subject claim **scoped by issuer**, never on an
    email or a preferred username: the OpenID Connect specification explicitly
    declines to guarantee either as stable or unique, which makes them the wrong
    shape for a primary key.
    """

    def __init__(self, entries: Iterable[DirectoryEntry]) -> None:
        """Build the directory, refusing a duplicated issuer-and-subject pair.

        A duplicate is a rendering defect rather than a runtime condition, so it
        fails at construction — which for the shipped directory means at
        startup, not on the request that happens to hit the second row.

        Raises:
            ValueError: Two entries share an issuer and subject.
        """
        rows: dict[tuple[str, str], DirectoryEntry] = {}
        for entry in entries:
            key = (entry.issuer, entry.subject)
            if key in rows:
                raise ValueError(
                    f"duplicate directory row for subject {entry.subject!r} "
                    f"at issuer {entry.issuer!r}"
                )
            rows[key] = entry
        self._rows: Mapping[tuple[str, str], DirectoryEntry] = MappingProxyType(rows)

    def lookup(self, claims: Claims) -> Principal | None:
        """Resolve the caller a token asserts into the principal the server stands behind.

        Returns ``None`` on a miss — **no principal at all**, rather than one
        with no roles. The empty-principal shortcut fails open: submitting is
        gated by scope alone and the write scope is deliberately ungated, so an
        unknown subject holding it would clear the scope gate, clear a role gate
        demanding nothing, and write a row charged to a null partition. The
        caller refuses with :data:`DIRECTORY_MISS`.

        The resolved principal is built from both stages: the scopes are the
        token's, the roles and partition are the directory's.
        """
        entry = self._rows.get((claims.issuer, claims.subject))
        if entry is None:
            return None
        return Principal(
            issuer=claims.issuer,
            subject=claims.subject,
            granted_scopes=claims.granted_scopes,
            roles=entry.roles,
            partition=entry.partition,
        )

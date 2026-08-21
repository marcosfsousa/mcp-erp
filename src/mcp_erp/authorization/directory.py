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

**The rows are rendered, never written here.** :func:`shipped_directory` reads
the committed file that :mod:`mcp_erp.authorization.identity` renders from the
seed, so the only hand-written rows anywhere are the stand-ins the tests
declare. The file is a package resource rather than a repository path: the
server reads it wherever it is installed, and the generator that writes it is
the only thing that needs to know where the checkout keeps it.
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
from types import MappingProxyType

from mcp_erp.authorization.principal import Claims, Principal
from mcp_erp.authorization.reasons import ROLE_MISSING, Reason

DIRECTORY_FILE = "principal-directory.json"
"""The rendered rows, inside layer 2's own package.

Inside, because identity provisioning is layer 2's and has to survive the
domain being deleted (ADR-0004, criterion 4). Its rows are domain-supplied and
its shape is not, which is the whole of the split.
"""

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


def parse_directory(text: str) -> tuple[DirectoryEntry, ...]:
    """Read rendered rows back into the type the lookup is built on.

    The reader of what :func:`mcp_erp.authorization.identity.render_directory`
    writes. Both are layer 2's, and the round trip is asserted, so one format
    cannot quietly become two that only nearly agree.

    Order is preserved rather than imposed: the renderer sorts, and re-sorting
    here would hide a rendering that had stopped doing so.
    """
    return tuple(
        DirectoryEntry(
            issuer=row["issuer"],
            subject=row["subject"],
            roles=frozenset(row["roles"]),
            partition=row["partition"],
        )
        for row in json.loads(text)
    )


@cache
def shipped_directory() -> PrincipalDirectory:
    """The directory the server runs on, read once and held immutable in memory.

    Cached because the file is a build artifact rather than configuration: it
    cannot change while the process runs, so re-reading it per request would
    buy nothing and put a file read inside the token middleware. A duplicated
    row therefore fails the first time this function is called, and
    :func:`mcp_erp.app.create_app` calls it while building the token gate — so
    it fails the boot rather than the request that happens to hit the second
    copy, and it cannot get that far anyway, because the renderer refuses a
    duplicated subject before it writes.

    No database, no Docker, and no call to the authorization server per
    request: ADR-0006 rejected the last of those outright, and this is what
    stands in its place.
    """
    package = resources.files(__package__)
    text = package.joinpath("data", DIRECTORY_FILE).read_text(encoding="utf-8")
    return PrincipalDirectory(parse_directory(text))

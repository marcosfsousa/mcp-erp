"""The identity generator: one authored seed, rendered into two committed artifacts.

Layer 2 owns identity provisioning end to end — the directory's shape, its
implementation and its renderer (ADR-0013) — so this module ships inside the
package the ejection command keeps. That placement is the point: provisioning
that lived in a top-level ``provisioning/`` would survive ejection by sitting
outside the blast radius rather than by being layer 2's, which is ADR-0004's
criterion 4 read approximately.

It renders **two of the seed's three renderings**: the principal directory, and
the authorization server's user import. The third — the ERP's own rows — is
layer 3's, rendered by a generator that is deleted with it. Each generator
speaks one layer's vocabulary, and neither reads the other.

**Issuer-side role names are opaque strings this module never interprets.** It
does not compare the two role columns, derive either from the other, or
validate an issuer-side name against anything. Rendering the user import from
directory roles would erase Priya Raman's realm-versus-server divergence, which
ADR-0007 calls load-bearing: that one row is what keeps the scope-without-role
state reachable through a real authorization code flow, and so what keeps the
middle denial class demonstrable rather than asserted.

**The renderings are byte-stable**: sorted keys, sorted rows, no generated
identifiers, no timestamps. A Keycloak realm export emits all three of those by
default, and any one of them would make the ``Seed renders clean`` job flaky —
which is the kind of required check that earns an exemption the branch ruleset
does not offer. So it is a constraint on this module, not a tolerance in the
check.

Run it from a checkout to re-render both files::

    python -m mcp_erp.authorization.identity
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from mcp_erp.authorization.directory import DirectoryEntry

SEED = "docs/organisation/seed.yaml"
"""The authored organisation this generator reads, relative to the repository root.

Layer 3's generator names the same file for itself. One shared constant would
be a cross-layer import for a string, and the layer that survives ejection
would be holding it on behalf of the layer that does not — the same trade
:func:`_as_json` is stated twice for.
"""

DIRECTORY_RENDERING = "src/mcp_erp/authorization/data/principal-directory.json"
"""Where the directory rendering is committed, relative to the repository root.

Inside the package, because it is layer 2's own data and has to survive the
domain being deleted. The shipped directory reads it as a package resource
rather than by this path — see :func:`mcp_erp.authorization.directory.shipped_directory`.
"""

USER_IMPORT_RENDERING = "keycloak/import/mcp-erp-users-0.json"
"""Where the user import is committed, relative to the repository root.

A second file beside the hand-authored realm rather than a ``users`` array
spliced into it. ADR-0007 wanted the clients, scopes and mappers hand-written
and only the users generated; two files make that split structural — the
authored file has no ``users`` key to hand-edit, and this one is never edited
at all. It is also Keycloak's own shape: exporting a realm with users in
separate files produces ``<realm>-realm.json`` alongside ``<realm>-users-N.json``,
and a directory import reads both.
"""

SUBJECT_LIMIT = 36
"""The longest subject the realm will store, which is the width a UUID fills.

The subject is imported as the realm's identifier for the person, so this is
the realm's constraint rather than ours. Checked here so that a too-long
subject fails at the line of the seed that caused it, rather than as an import
error with no obvious connection to it.
"""


@dataclass(frozen=True, slots=True)
class Identity:
    """One person, in the half of the seed layer 2 speaks.

    Everything the domain holds about them — their display name, what they do,
    which vendors they may raise a requisition against — is absent, because
    none of it reaches a rendering this module produces.

    Attributes:
        subject: The ``sub`` claim, and the realm's identifier for this person.
        username: What they type at the login form. Never a directory key: the
            OpenID Connect specification declines to guarantee a preferred
            username as stable or unique, which is the wrong shape for one.
        partition: What row scoping compares. Layer 3 authors it as a cost
            centre; this is the one point where the two names meet, and the
            duplication is by generation, which is what the drift check
            polices.
        roles: Server-side, resolved per request, never carried in a token.
        realm_roles: Issuer-side, and **opaque** — carried to the realm
            verbatim and never read for meaning.
    """

    subject: str
    username: str
    partition: str
    roles: tuple[str, ...]
    realm_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IdentitySeed:
    """The seed's identity half: who vouches for these people, and who they are.

    Named for the half rather than for the seed, because the seed is the whole
    of what the exhibit starts from — the authored organisation *and* the
    generated fixtures — and this type is one slice of the first of those.
    :class:`mcp_erp.purchase_to_pay.organisation.Organisation` is the slice
    beside it, in the layer whose words the rest of that half is written in.

    Attributes:
        issuer: The authorization server the subjects below are scoped by.
        realm: The realm the user import belongs to, taken from the issuer's
            last path segment rather than authored twice.
        password: One conspicuously fake password, shared by everybody. Seven
            per-person passwords would be seven equally committed, equally fake
            secrets buying no behaviour.
        identities: The cast, in the order the seed lists them.
    """

    issuer: str
    realm: str
    password: str
    identities: tuple[Identity, ...]


def read_identity_seed(text: str) -> IdentitySeed:
    """Parse the identity half of the seed, refusing what the realm would reject later.

    Two refusals, both of which would otherwise surface as an authorization
    server rejecting a file: a subject sharing another's — which is also a
    directory key collision — and a subject too long to be a realm identifier.

    Raises:
        ValueError: Two people share a subject, or a subject is empty or longer
            than :data:`SUBJECT_LIMIT`.
    """
    document = yaml.safe_load(text)
    issuer = str(document["issuer"])
    identities: list[Identity] = []
    seen: set[str] = set()

    for person in document["people"]:
        subject = str(person["subject"])
        if not subject or len(subject) > SUBJECT_LIMIT:
            raise ValueError(f"subject {subject!r} is not between 1 and {SUBJECT_LIMIT} characters")
        if subject in seen:
            raise ValueError(f"duplicate subject {subject!r}")
        seen.add(subject)
        identities.append(
            Identity(
                subject=subject,
                username=str(person["username"]),
                # The seed authors this as a cost centre, which is layer 3's
                # name for what fills the partition. Read once, here.
                partition=str(person["cost_centre"]),
                roles=tuple(sorted(person["roles"])),
                realm_roles=tuple(sorted(person["realm_roles"])),
            )
        )

    return IdentitySeed(
        issuer=issuer,
        realm=issuer.rsplit("/", 1)[-1],
        password=str(document["password"]),
        identities=tuple(identities),
    )


def directory_entries(seed: IdentitySeed) -> tuple[DirectoryEntry, ...]:
    """The directory rows this seed describes, in the shape layer 2 already owns.

    Going through :class:`~mcp_erp.authorization.directory.DirectoryEntry`
    rather than straight to JSON is what keeps the rendered file and the loaded
    row one shape: the round trip is asserted, so the writer and the reader
    cannot drift into two formats that only nearly agree.
    """
    return tuple(
        DirectoryEntry(
            issuer=seed.issuer,
            subject=identity.subject,
            roles=frozenset(identity.roles),
            partition=identity.partition,
        )
        for identity in sorted(seed.identities, key=lambda identity: identity.subject)
    )


def render_directory(seed: IdentitySeed) -> str:
    """Render the principal directory: issuer, subject, roles and partition per row.

    A flat array rather than an issuer with rows beneath it. The key is a pair,
    and writing it as a pair on every row is what keeps a second issuer from
    being a format change.
    """
    return _as_json(
        [
            {
                "issuer": entry.issuer,
                "partition": entry.partition,
                "roles": sorted(entry.roles),
                "subject": entry.subject,
            }
            for entry in directory_entries(seed)
        ]
    )


def render_user_import(seed: IdentitySeed) -> str:
    """Render the authorization server's user import.

    The credential is **non-temporary with no required actions**, deliberately:
    an imported password is temporary by default, which triggers an
    update-password action on first login and hangs a headless flow on a form
    it does not expect.

    Nothing here is read for meaning. ``realmRoles`` carries the seed's
    issuer-side column verbatim, and the roles it names are the realm's to
    define — this module neither declares them nor checks that they exist.
    """
    return _as_json(
        {
            "realm": seed.realm,
            "users": [
                {
                    "credentials": [
                        {"temporary": False, "type": "password", "value": seed.password}
                    ],
                    "enabled": True,
                    "id": identity.subject,
                    "realmRoles": list(identity.realm_roles),
                    "requiredActions": [],
                    "username": identity.username,
                }
                for identity in sorted(seed.identities, key=lambda identity: identity.subject)
            ],
        }
    )


def _as_json(document: object) -> str:
    """One serialisation for both renderings, and the whole of the byte-stability claim.

    Sorted keys, a fixed indent, no ASCII escaping — so a name outside ASCII
    reads as itself — and a trailing newline. Line endings are the one
    character Python writes for a newline on every platform, because
    :func:`_write` emits bytes rather than text: a rendering whose bytes
    depended on the machine that produced it would fail the drift check for the
    one reason that check is not allowed to fire.
    """
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write(path: Path, text: str) -> None:
    """Write a rendering, in bytes, with the newline the renderer chose."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def main() -> None:
    """Re-render both artifacts from the committed seed.

    Resolves paths from this file's location, so it runs from a checkout and
    nowhere else. That is the only place it is meant to run: the renderings are
    committed, and the ``Seed renders clean`` job re-runs this and fails on any
    diff.
    """
    repo = Path(__file__).resolve().parents[3]
    seed = read_identity_seed((repo / SEED).read_text(encoding="utf-8"))

    for rendering, text in (
        (DIRECTORY_RENDERING, render_directory(seed)),
        (USER_IMPORT_RENDERING, render_user_import(seed)),
    ):
        _write(repo / rendering, text)
        print(f"rendered {rendering}")


if __name__ == "__main__":
    main()

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

**What this module's loader refuses, and where that stops.** A loader here
refuses exactly what would otherwise fail further away — a realm rejecting the
user import, a directory key colliding, a rendering that is wrong in every file
at once — and nothing else. Type-checking every field is not on the list: that
is what the seed's own shape and mypy are for, and a loader that grew a check
per field would be a schema written twice. The rule is stated here so a review
grades a proposed refusal against it rather than against taste, and
:func:`read_identity_seed` lists the seven it currently makes.

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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

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
        issuer: The authorization server the subjects below are scoped by, in
            the configuration ``docker compose up`` brings up.
        tls_issuer: The same realm's identifier under the opt-in TLS profile,
            or ``None``. Optional because the default configuration has one
            identifier and the profile is something a reader takes
            deliberately. ADR-0015 makes it ``issuer`` under another scheme and
            nothing else, so it is not a second place the realm can be reached
            from.
        realm: The realm the user import belongs to, taken from the first
            issuer's last path segment rather than authored twice.
        password: One conspicuously fake password, shared by everybody. Seven
            per-person passwords would be seven equally committed, equally fake
            secrets buying no behaviour.
        identities: The cast, in the order the seed lists them.
    """

    issuer: str
    tls_issuer: str | None
    realm: str
    password: str
    identities: tuple[Identity, ...]

    @property
    def issuers(self) -> tuple[str, ...]:
        """Every identifier one realm answers to, default first.

        The directory is keyed by issuer **and** subject, so an identifier the
        directory has never heard of resolves nobody and every call under it
        refuses with ``role_missing``. Listing them here is what lets the
        renderer hold the cast at each without a second authored copy of the
        cast.
        """
        if self.tls_issuer is None:
            return (self.issuer,)
        return (self.issuer, self.tls_issuer)


def realm_of(issuer: str) -> str:
    """The realm an issuer names, which is its last path segment.

    One derivation, and it runs on the **first** issuer alone. The realm name is
    not what the second issuer is checked against — ADR-0015 holds that one to
    the first issuer entire, scheme excepted — because a name taken from one
    path segment is the same name at an authority nothing serves, and reading
    the second issuer for its realm is what made the refusal one segment
    narrower than the sentence describing it.

    **The empty segment is refused here rather than returned**, so that a
    trailing slash fails at the issuer that carries it. The second issuer needs
    no separate guard: it either matches the first, whose segment was checked
    here, or it does not and is refused for that. Nothing downstream would have
    noticed either: the user import would carry ``"realm": ""`` and every
    rendering would be wrong at once, with no line of the seed to point at.

    Raises:
        ValueError: The issuer's last path segment is empty.
    """
    realm = issuer.rsplit("/", 1)[-1]
    if not realm:
        raise ValueError(f"issuer {issuer!r} names no realm in its last path segment")
    return realm


def _but_for_the_scheme(issuer: str) -> tuple[str, tuple[str, ...]]:
    """An issuer as the scheme it is reached by, and everything else it is.

    Parsed rather than split on ``"://"``, so that an issuer carrying no scheme
    at all has its whole self land in the second half instead of vanishing into
    a separator that was never there — two schemeless issuers would otherwise
    compare equal on nothing and pass.
    """
    parts = urlsplit(issuer)
    return parts.scheme, (parts.netloc, parts.path, parts.query, parts.fragment)


def read_identity_seed(text: str) -> IdentitySeed:
    """Parse the identity half of the seed, refusing what the realm would reject later.

    Seven refusals, every one of them an instance of the rule this module's
    docstring states. Four are things an authorization server would reject a
    file for, later and further away: a subject sharing another's — also a
    directory key collision — a subject too long to be a realm identifier, a
    username sharing another's, and an issuer with no last path segment to take
    a realm name from, which :func:`realm_of` makes.

    The other three nothing downstream would reject at all. A second issuer that
    moves more than the scheme, and one that moves nothing, are both ADR-0015 —
    the first renders seven directory rows at an address nothing serves, the
    second renders every person twice under one key. And a role column that is
    absent, ``null`` or one scalar rather than a list is a row that reads
    correctly to a person and holds either no roles or one role per character.

    The empty role list is **not** among them. It is the state ADR-0007 calls
    load-bearing — Priya Raman holds no server-side role — so a person with no
    roles parses, and a person with no ``roles`` key does not.

    Raises:
        ValueError: A subject is empty or longer than :data:`SUBJECT_LIMIT`; two
            people share a subject or a username; the issuer's last path segment
            is empty; the second issuer is not the first under another scheme;
            or a person states a role column that is absent, ``null`` or a
            scalar.
    """
    document = yaml.safe_load(text)
    issuer = str(document["issuer"])
    realm = realm_of(issuer)
    authored = document.get("tls_issuer")
    tls_issuer = None if authored is None else str(authored)
    if tls_issuer is not None:
        # ADR-0015. The profile changes how the realm is reached and not which
        # realm it is, nor where — `tls.env` moves one origin variable from
        # `http://keycloak:8081` to `https://keycloak:8081` and every issuer
        # string in `compose.yaml` reads it — so the scheme is the one part
        # allowed to differ and everything else has to be the same string.
        scheme, rest = _but_for_the_scheme(issuer)
        second_scheme, second_rest = _but_for_the_scheme(tls_issuer)
        if second_rest != rest:
            raise ValueError(
                f"second issuer {tls_issuer!r} moves more than the scheme of {issuer!r}"
            )
        if second_scheme == scheme:
            raise ValueError(
                f"second issuer {tls_issuer!r} moves no scheme: it is the first issuer, "
                "and the directory would hold every person twice under one key"
            )

    identities: list[Identity] = []
    subjects: set[str] = set()
    usernames: set[str] = set()

    for person in document["people"]:
        subject = str(person["subject"])
        if not subject or len(subject) > SUBJECT_LIMIT:
            raise ValueError(f"subject {subject!r} is not between 1 and {SUBJECT_LIMIT} characters")
        if subject in subjects:
            raise ValueError(f"duplicate subject {subject!r}")
        subjects.add(subject)

        username = str(person["username"])
        if username in usernames:
            raise ValueError(f"duplicate username {username!r}")
        usernames.add(username)

        identities.append(
            Identity(
                subject=subject,
                username=username,
                # The seed authors this as a cost centre, which is layer 3's
                # name for what fills the partition. Read once, here.
                partition=str(person["cost_centre"]),
                roles=_roles(person, "roles", subject=subject),
                realm_roles=_roles(person, "realm_roles", subject=subject),
            )
        )

    return IdentitySeed(
        issuer=issuer,
        tls_issuer=tls_issuer,
        realm=realm,
        password=str(document["password"]),
        identities=tuple(identities),
    )


def _roles(person: Mapping[str, Any], column: str, *, subject: str) -> tuple[str, ...]:
    """One role column, sorted, refusing everything that is not a list of names.

    Two distinctions, and they are the whole of this function. ``roles: []`` is
    Priya Raman and stays legal, while the key missing or ``null`` is a
    malformed row that reported itself as a `TypeError` out of ``sorted`` rather
    than as a defect naming the person it came from. And **one authored scalar
    is not one role**: ``roles: erp.read`` is a string, ``sorted`` walks it, and
    the row that reads correctly to a person builds an identity holding one role
    per character — every call under which refuses ``role_missing``, several
    steps from the line that caused it.

    A list rather than *not a string*, because the number the standard library
    does refuse is refused here too, naming the person and the column instead of
    the iteration.

    Raises:
        ValueError: The column is absent, ``null``, or not a list.
    """
    names = person.get(column)
    if names is None:
        raise ValueError(f"person {subject!r} states no {column!r}")
    if not isinstance(names, list):
        raise ValueError(
            f"person {subject!r} states {column!r} as one {type(names).__name__} rather than a list"
        )
    return tuple(sorted(str(name) for name in names))


def directory_entries(seed: IdentitySeed) -> tuple[DirectoryEntry, ...]:
    """The directory rows this seed describes, in the shape layer 2 already owns.

    Going through :class:`~mcp_erp.authorization.directory.DirectoryEntry`
    rather than straight to JSON is what keeps the rendered file and the loaded
    row one shape: the round trip is asserted, so the writer and the reader
    cannot drift into two formats that only nearly agree.

    **The whole cast at every issuer**, which is the seed's list and today is
    two: the address ``docker compose up`` serves and the one the opt-in TLS
    profile serves. The roles and the partition come from the one authored
    person either way — a second identifier for one realm is not a second
    policy, and rendering them per issuer is what would let two rows for one
    person disagree.

    Issuer-major order, so the default configuration's rows read as a block and
    a reader can see where the second identifier starts.
    """
    return tuple(
        DirectoryEntry(
            issuer=issuer,
            subject=identity.subject,
            roles=frozenset(identity.roles),
            partition=identity.partition,
        )
        for issuer in seed.issuers
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

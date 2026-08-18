"""The identity generator: two renderings from one seed, and the invariants between them.

These assertions are what the `Seed renders clean` job means for layer 2's half
of the seed. They run in the ejection suite deliberately — provisioning is the
one layer-3-shaped job layer 2 owns outright (ADR-0004, criterion 4), so it has
to keep working with the domain deleted, and this is where that is proved.

**The invariants between the two renderings are asserted against the committed
files, not against two renders of one object in memory.** ADR-0007's claim is
that membership is held equal *"not by the assumption that the seed is the only
writer"*, and comparing `render_directory(seed)` to `render_user_import(seed)`
would assume exactly that — the two would be near-tautologically equal because
they walk the same tuple. Read from disk, the assertion survives a second
writer, and it is the form that extends when the hand-authored realm file lands
with #36: its users join the realm side of the comparison, and nothing else
about these tests changes.

The assertions are written against the seed's own rows rather than a hardcoded
cast. Only one literal from the organisation appears below — the subject
declared as the role-column exception — because an exception that is not named
in the test is not an exception, it is an absence of checking.
"""

import json
from pathlib import Path

import pytest
import yaml

from mcp_erp.authorization.identity import (
    DIRECTORY_RENDERING,
    SEED,
    USER_IMPORT_RENDERING,
    IdentitySeed,
    read_identity_seed,
    render_directory,
    render_user_import,
)

REPO = Path(__file__).parents[2]
SEED_FILE = REPO / SEED

ROLE_COLUMN_EXCEPTION = "priya-raman"
"""The one subject whose two role columns are allowed to disagree.

Declared on the **role columns only, never on membership**: a subject missing
from either rendering is a defect no matter whose it is. ADR-0007 makes this
row load-bearing — it is what keeps the scope-without-role state reachable
through a real flow — so the assertion below also fails if somebody tidies the
divergence away.
"""


@pytest.fixture(scope="module")
def seed() -> IdentitySeed:
    """The committed organisation, parsed once."""
    return read_identity_seed(SEED_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def directory_rows() -> list[dict[str, object]]:
    """The committed directory rendering, as it sits on disk."""
    rows: list[dict[str, object]] = json.loads(
        (REPO / DIRECTORY_RENDERING).read_text(encoding="utf-8")
    )
    return rows


@pytest.fixture(scope="module")
def realm_users() -> list[dict[str, object]]:
    """The committed user import, as it sits on disk."""
    users: list[dict[str, object]] = json.loads(
        (REPO / USER_IMPORT_RENDERING).read_text(encoding="utf-8")
    )["users"]
    return users


def test_the_committed_directory_is_what_the_seed_renders(seed: IdentitySeed) -> None:
    """A hand-edited rendering is a failing test, not a surprise at boot."""
    committed = (REPO / DIRECTORY_RENDERING).read_bytes()

    assert render_directory(seed).encode("utf-8") == committed


def test_the_committed_user_import_is_what_the_seed_renders(seed: IdentitySeed) -> None:
    """The same claim for the realm's half."""
    committed = (REPO / USER_IMPORT_RENDERING).read_bytes()

    assert render_user_import(seed).encode("utf-8") == committed


def test_rendering_twice_produces_the_same_bytes(seed: IdentitySeed) -> None:
    """Byte-stability, asserted rather than assumed.

    A renderer that emitted a timestamp or a generated identifier would pass
    every other test here and make the drift job flake — and a flaky required
    check is the one that earns an exemption the branch ruleset does not offer.
    """
    assert render_directory(seed) == render_directory(seed)
    assert render_user_import(seed) == render_user_import(seed)


def test_neither_rendering_carries_a_generated_identifier_or_a_timestamp(
    seed: IdentitySeed,
) -> None:
    """Every value in either rendering is one the seed states, or a named derivation.

    A generated identifier or a timestamp is exactly a value nobody wrote down,
    so this is the shape that catches one. Keycloak's own export emits both,
    plus unsorted keys, which is why the renderer is ours.

    Compared against the seed's **parsed values**, never against its text. Text
    would let a rendering pass because a word happened to appear in a comment,
    and would turn red when a comment was reflowed — a flake in the one job
    whose whole premise is that a required check must not have any.
    """
    authored = set(_strings(yaml.safe_load(SEED_FILE.read_text(encoding="utf-8"))))
    allowed = authored | _derived_values(seed)

    for rendering in (render_directory(seed), render_user_import(seed)):
        for value in _strings(json.loads(rendering)):
            assert value in allowed, value


def test_both_renderings_sort_their_keys(seed: IdentitySeed) -> None:
    """Sorted keys, so a re-render cannot reorder a file and read as a change."""
    for rendering in (render_directory(seed), render_user_import(seed)):
        for mapping in _mappings(json.loads(rendering)):
            assert list(mapping) == sorted(mapping)


def test_the_realm_subject_set_equals_the_directory_subject_set(
    directory_rows: list[dict[str, object]], realm_users: list[dict[str, object]]
) -> None:
    """Membership is held equal by this test, not by trusting who writes the realm.

    ADR-0013 withdrew the stronger claim that a stranger's token is unmintable:
    ADR-0007 engineers realm-versus-server drift on purpose, so a realm user
    with no directory row is one edit from a state this design deliberately
    inhabits. What replaces it is this equality, and it takes no exceptions.
    """
    directory = {row["subject"] for row in directory_rows}
    realm = {user["id"] for user in realm_users}

    assert directory == realm


def test_the_role_columns_agree_except_where_the_exception_is_declared(
    directory_rows: list[dict[str, object]], realm_users: list[dict[str, object]]
) -> None:
    """Two independent columns, and exactly one row allowed to diverge."""
    directory = _roles_by_subject(directory_rows, "subject", "roles")
    realm = _roles_by_subject(realm_users, "id", "realmRoles")

    diverging = {subject for subject in directory if directory[subject] != realm[subject]}

    assert diverging == {ROLE_COLUMN_EXCEPTION}


def test_the_declared_exception_diverges_in_the_direction_the_exhibit_needs(
    directory_rows: list[dict[str, object]], realm_users: list[dict[str, object]]
) -> None:
    """Scope from the realm, no role at the server — the middle denial class.

    The other direction is not modelled and would not satisfy this: a server
    role with no realm role produces `insufficient_scope`, which the matrix
    already reaches by varying the requested scope set.
    """
    directory = _roles_by_subject(directory_rows, "subject", "roles")
    realm = _roles_by_subject(realm_users, "id", "realmRoles")

    assert directory[ROLE_COLUMN_EXCEPTION] == set()
    assert realm[ROLE_COLUMN_EXCEPTION] != set()


def test_an_issuer_side_role_name_is_carried_through_uninterpreted() -> None:
    """Opaque strings, on their way to a realm layer 2 does not model.

    The generator never compares the two columns, never derives one from the
    other, and never validates an issuer-side name against anything. A realm
    role that means nothing here still renders verbatim, and renders nowhere
    near the directory.
    """
    invented = read_identity_seed(
        _seed_text(
            subject="somebody",
            roles=["a_server_role"],
            realm_roles=["a-name-layer-2-has-never-heard-of"],
        )
    )

    directory = json.loads(render_directory(invented))
    realm = json.loads(render_user_import(invented))

    assert directory[0]["roles"] == ["a_server_role"]
    assert realm["users"][0]["realmRoles"] == ["a-name-layer-2-has-never-heard-of"]


def test_a_duplicated_subject_fails_at_the_renderer() -> None:
    """Two people cannot share a subject; the directory key would collide."""
    text = _seed_text(subject="twice") + _person_block(subject="twice")

    with pytest.raises(ValueError, match="duplicate subject"):
        read_identity_seed(text)


def test_a_subject_too_long_for_the_realm_fails_at_the_renderer() -> None:
    """The realm stores the subject as its identifier for the person, in 36 characters.

    Caught here rather than at import, where the failure would be an
    authorization server rejecting a file with no obvious connection to the
    line of the seed that caused it.
    """
    with pytest.raises(ValueError, match="subject"):
        read_identity_seed(_seed_text(subject="x" * 37))


def test_every_person_carries_a_partition(directory_rows: list[dict[str, object]]) -> None:
    """A directory row with no partition cannot produce a principal at all."""
    for row in directory_rows:
        assert row["partition"]


def test_the_password_is_imported_ready_to_use(
    seed: IdentitySeed, realm_users: list[dict[str, object]]
) -> None:
    """Non-temporary, with no required actions.

    Keycloak imports a credential as temporary unless told otherwise, which
    triggers an update-password action on first login and hangs a headless flow
    on a form it does not expect.
    """
    for user in realm_users:
        assert user["requiredActions"] == []
        assert user["credentials"] == [
            {"temporary": False, "type": "password", "value": seed.password}
        ]


def _derived_values(seed: IdentitySeed) -> set[str]:
    """The two values a rendering may carry that the seed does not state outright.

    Both are named rather than tolerated: ``password`` is the credential type
    Keycloak's own format fixes, and the realm name is the issuer's last path
    segment rather than a second authored copy of it.
    """
    return {"password", seed.realm}


def _roles_by_subject(
    rows: list[dict[str, object]], subject_key: str, roles_key: str
) -> dict[str, set[str]]:
    """One role column, keyed by subject, read through each rendering's own field names.

    The two renderings name the same two things differently — the directory
    says ``subject`` and ``roles``, the realm says ``id`` and ``realmRoles`` —
    and that is the whole reason this takes the keys as arguments rather than
    normalising one side into the other's shape.
    """
    by_subject: dict[str, set[str]] = {}
    for row in rows:
        subject, roles = row[subject_key], row[roles_key]
        assert isinstance(subject, str)
        assert isinstance(roles, list)
        by_subject[subject] = set(roles)
    return by_subject


def _seed_text(
    subject: str,
    roles: list[str] | None = None,
    realm_roles: list[str] | None = None,
) -> str:
    """A one-person seed, for the cases the committed organisation cannot show."""
    return (
        "issuer: https://issuer.example/realms/exhibit\n"
        "password: not-a-secret\n"
        "cost_centres: []\n"
        "vendors: []\n"
        "people:\n" + _person_block(subject, roles, realm_roles)
    )


def _person_block(
    subject: str,
    roles: list[str] | None = None,
    realm_roles: list[str] | None = None,
) -> str:
    """One `people` entry, in the seed's own shape."""
    return (
        f"  - name: A Person\n"
        f"    subject: {subject}\n"
        f"    username: a.person\n"
        f"    cost_centre: P-1\n"
        f"    roles: {json.dumps(roles or [])}\n"
        f"    realm_roles: {json.dumps(realm_roles or [])}\n"
    )


def _strings(node: object) -> list[str]:
    """Every string value anywhere in a parsed document."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [s for value in node.values() for s in _strings(value)]
    if isinstance(node, list):
        return [s for item in node for s in _strings(item)]
    return []


def _mappings(node: object) -> list[dict[str, object]]:
    """Every mapping anywhere in a parsed document, including nested ones."""
    if isinstance(node, dict):
        return [node, *(m for value in node.values() for m in _mappings(value))]
    if isinstance(node, list):
        return [m for item in node for m in _mappings(item)]
    return []

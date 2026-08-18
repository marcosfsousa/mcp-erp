"""The identity generator: two renderings from one seed, and the invariants between them.

These assertions are what the `Seed renders clean` job means for layer 2's half
of the seed. They run in the ejection suite deliberately — provisioning is the
one layer-3-shaped job layer 2 owns outright (ADR-0004, criterion 4), so it has
to keep working with the domain deleted, and this is where that is proved.

The assertions are written against the seed's own rows rather than against a
hardcoded cast. Only one literal from the organisation appears below — the
subject declared as the role-column exception — because an exception that is
not named in the test is not an exception, it is an absence of checking.
"""

import json
from pathlib import Path

import pytest

from mcp_erp.authorization.identity import (
    DIRECTORY_RENDERING,
    USER_IMPORT_RENDERING,
    Seed,
    read_seed,
    render_directory,
    render_user_import,
)

REPO = Path(__file__).parents[2]
SEED_FILE = REPO / "docs" / "organisation" / "seed.yaml"

ROLE_COLUMN_EXCEPTION = "priya-raman"
"""The one subject whose two role columns are allowed to disagree.

Declared on the **role columns only, never on membership**: a subject missing
from either rendering is a defect no matter whose it is. ADR-0007 makes this
row load-bearing — it is what keeps the scope-without-role state reachable
through a real flow — so the assertion below also fails if somebody tidies the
divergence away.
"""


@pytest.fixture(scope="module")
def seed() -> Seed:
    """The committed organisation, parsed once."""
    return read_seed(SEED_FILE.read_text(encoding="utf-8"))


def test_the_committed_directory_is_what_the_seed_renders(seed: Seed) -> None:
    """A hand-edited rendering is a failing test, not a surprise at boot."""
    committed = (REPO / DIRECTORY_RENDERING).read_bytes()

    assert render_directory(seed).encode("utf-8") == committed


def test_the_committed_user_import_is_what_the_seed_renders(seed: Seed) -> None:
    """The same claim for the realm's half."""
    committed = (REPO / USER_IMPORT_RENDERING).read_bytes()

    assert render_user_import(seed).encode("utf-8") == committed


def test_rendering_twice_produces_the_same_bytes(seed: Seed) -> None:
    """Byte-stability, asserted rather than assumed.

    A renderer that emitted a timestamp or a generated identifier would pass
    every other test here and make the drift job flake — and a flaky required
    check is the one that earns an exemption the branch ruleset does not offer.
    """
    assert render_directory(seed) == render_directory(seed)
    assert render_user_import(seed) == render_user_import(seed)


def test_neither_rendering_carries_a_generated_identifier_or_a_timestamp(seed: Seed) -> None:
    """Every value in either rendering is traceable to a line in the seed.

    Stated as substring containment against the authored file, which is the
    form that catches what matters: a generated identifier or a timestamp is
    exactly a value nobody wrote down. Keycloak's own export emits both, plus
    unsorted keys, which is why the renderer is ours.
    """
    authored = SEED_FILE.read_text(encoding="utf-8")

    for rendering in (render_directory(seed), render_user_import(seed)):
        for value in _strings(json.loads(rendering)):
            assert value in authored, value


def test_both_renderings_sort_their_keys(seed: Seed) -> None:
    """Sorted keys, so a re-render cannot reorder a file and read as a change."""
    for rendering in (render_directory(seed), render_user_import(seed)):
        for mapping in _mappings(json.loads(rendering)):
            assert list(mapping) == sorted(mapping)


def test_the_realm_subject_set_equals_the_directory_subject_set(seed: Seed) -> None:
    """Membership is held equal by this test, not by trusting who writes the realm.

    ADR-0013 withdrew the stronger claim that a stranger's token is unmintable:
    ADR-0007 engineers realm-versus-server drift on purpose, so a realm user
    with no directory row is one edit from a state this design inhabits. What
    replaces it is this equality, and it takes no exceptions.
    """
    directory = {row["subject"] for row in json.loads(render_directory(seed))}
    realm = {user["id"] for user in json.loads(render_user_import(seed))["users"]}

    assert directory == realm


def test_the_role_columns_agree_except_where_the_exception_is_declared(seed: Seed) -> None:
    """Two independent columns, and exactly one row allowed to diverge."""
    directory = {row["subject"]: set(row["roles"]) for row in json.loads(render_directory(seed))}
    users = json.loads(render_user_import(seed))["users"]
    realm = {user["id"]: set(user["realmRoles"]) for user in users}

    diverging = {subject for subject in directory if directory[subject] != realm[subject]}

    assert diverging == {ROLE_COLUMN_EXCEPTION}


def test_the_declared_exception_diverges_in_the_direction_the_exhibit_needs(seed: Seed) -> None:
    """Scope from the realm, no role at the server — the middle denial class.

    The other direction is not modelled and would not satisfy this: a server
    role with no realm role produces `insufficient_scope`, which the matrix
    already reaches by varying the requested scope set.
    """
    directory = {row["subject"]: set(row["roles"]) for row in json.loads(render_directory(seed))}
    users = json.loads(render_user_import(seed))["users"]
    realm = {user["id"]: set(user["realmRoles"]) for user in users}

    assert directory[ROLE_COLUMN_EXCEPTION] == set()
    assert realm[ROLE_COLUMN_EXCEPTION] != set()


def test_an_issuer_side_role_name_is_carried_through_uninterpreted() -> None:
    """Opaque strings, on their way to a realm layer 2 does not model.

    The generator never compares the two columns, never derives one from the
    other, and never validates an issuer-side name against anything. A realm
    role that means nothing here still renders verbatim, and renders nowhere
    near the directory.
    """
    invented = read_seed(
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
        read_seed(text)


def test_a_subject_too_long_for_the_realm_fails_at_the_renderer() -> None:
    """The realm stores the subject as its user identifier, in 36 characters.

    Caught here rather than at import, where the failure would be an
    authorization server rejecting a file with no obvious connection to the
    line of the seed that caused it.
    """
    with pytest.raises(ValueError, match="subject"):
        read_seed(_seed_text(subject="x" * 37))


def test_every_person_carries_a_partition(seed: Seed) -> None:
    """A directory row with no partition cannot produce a principal at all."""
    for row in json.loads(render_directory(seed)):
        assert row["partition"]


def test_the_password_is_imported_ready_to_use(seed: Seed) -> None:
    """Non-temporary, with no required actions.

    Keycloak imports a credential as temporary unless told otherwise, which
    triggers an update-password action on first login and hangs a headless flow
    on a form it does not expect.
    """
    for user in json.loads(render_user_import(seed))["users"]:
        assert user["requiredActions"] == []
        assert user["credentials"] == [
            {"temporary": False, "type": "password", "value": seed.password}
        ]


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

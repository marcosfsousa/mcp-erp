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
import re
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


def test_the_committed_directory_holds_the_cast_at_every_issuer(
    seed: IdentitySeed,
    directory_rows: list[dict[str, object]],
    realm_users: list[dict[str, object]],
) -> None:
    """The row count has a ceiling, and it is the cast times the issuer list.

    The opt-in TLS profile reaches one realm under a second identifier, and a
    directory keyed by issuer *and* subject has to hold both or every call under
    the profile refuses with `role_missing`. That is a rule which generates
    rows, so it is stated with its ceiling: two issuers, seven people, fourteen
    rows and no third source of multiplication.
    """
    assert len(directory_rows) == len(seed.issuers) * len(realm_users)
    assert {row["issuer"] for row in directory_rows} == set(seed.issuers)


def test_the_second_issuer_moves_nothing_but_the_scheme(seed: IdentitySeed) -> None:
    """One address, two schemes, and the profile's whole diff.

    The service name and the port are what resolve identically on both sides of
    the container boundary — Compose's own DNS inside, one `127.0.0.1 keycloak`
    line outside — so the profile buys a secure context by moving the one thing
    W3C Secure Contexts §3.1 reads, and moves nothing else.
    """
    default, under_the_profile = seed.issuers

    assert default.startswith("http://")
    assert under_the_profile == f"https://{default.removeprefix('http://')}"


def test_a_person_renders_the_same_roles_at_every_issuer() -> None:
    """A second issuer is a second identifier for one realm, not a second policy.

    Rendering the roles per issuer rather than once is what would let the two
    drift, and a reader comparing two rows for one person would have no way to
    tell which the server was answering from.
    """
    both = read_identity_seed(
        _seed_text(
            subject="somebody",
            roles=["a_server_role"],
            issuer="http://issuer.example/realms/exhibit",
            tls_issuer="https://issuer.example/realms/exhibit",
        )
    )

    rows = json.loads(render_directory(both))

    assert [row["issuer"] for row in rows] == [
        "http://issuer.example/realms/exhibit",
        "https://issuer.example/realms/exhibit",
    ]
    assert {row["subject"] for row in rows} == {"somebody"}
    assert all(row["roles"] == ["a_server_role"] for row in rows)


def test_a_seed_with_no_second_issuer_renders_one_row_per_person() -> None:
    """The second identifier is optional, because the default configuration has none."""
    only_one = read_identity_seed(_seed_text(subject="somebody"))

    assert only_one.issuers == ("https://issuer.example/realms/exhibit",)
    assert len(json.loads(render_directory(only_one))) == 1


@pytest.mark.parametrize(
    ("moves", "second"),
    [
        # The realm name, which is what the check compared before ADR-0015 and
        # the only thing it compared.
        ("the realm", "http://issuer.example/realms/other"),
        # The authority, which the check never looked at. It is the case the
        # ticket named as the symptom, and the one a last-segment comparison
        # and a whole-path comparison both admit.
        ("the authority", "https://elsewhere.example/realms/exhibit"),
        ("the port", "https://issuer.example:8443/realms/exhibit"),
        # The path above the realm, which is legacy Keycloak's own shape and
        # shares the last segment with the first issuer.
        ("the path above the realm", "https://issuer.example/auth/realms/exhibit"),
        # Nothing at all. Two identical identifiers are not one realm reached
        # two ways; they are one reached once, rendered twice, and the
        # directory would hold every person under a key it already holds them
        # under.
        ("nothing", "http://issuer.example/realms/exhibit"),
    ],
)
def test_a_second_issuer_that_moves_more_than_the_scheme_is_refused(
    moves: str, second: str
) -> None:
    """ADR-0015: the second identifier is the first with a different scheme.

    Parameterised over what moves rather than asserted once, because every
    weaker reading of *the same realm* — the last path segment, the whole path —
    is green on some of these rows and red on others, and a single case would
    not say which reading landed.
    """
    text = _seed_text(
        subject="somebody",
        issuer="http://issuer.example/realms/exhibit",
        tls_issuer=second,
    )

    with pytest.raises(ValueError, match="scheme"):
        read_identity_seed(text)


def test_a_second_issuer_that_moves_only_the_scheme_is_the_one_shape_admitted() -> None:
    """The profile's own diff, stated as the positive case beside the refusals.

    `tls.env` moves `MCP_KEYCLOAK_ORIGIN` from `http://keycloak:8081` to
    `https://keycloak:8081` and nothing else, so this is the one seed the
    committed configuration can produce.
    """
    text = _seed_text(
        subject="somebody",
        issuer="http://issuer.example/realms/exhibit",
        tls_issuer="https://issuer.example/realms/exhibit",
    )

    parsed = read_identity_seed(text)

    assert parsed.issuers == (
        "http://issuer.example/realms/exhibit",
        "https://issuer.example/realms/exhibit",
    )
    assert parsed.realm == "exhibit"


@pytest.mark.parametrize("position", ["issuer", "tls_issuer"])
@pytest.mark.parametrize(
    ("damage", "authored", "names"),
    [
        # `urlsplit` strips ASCII whitespace from both ends, so a comparison of
        # parses admits these and the rendering keys the directory at the
        # string with the space still on it.
        ("a leading space", " https://issuer.example/realms/exhibit", "' '"),
        ("a trailing space", "https://issuer.example/realms/exhibit ", "' '"),
        # Deleted wherever it sits rather than stripped from the ends, which is
        # why this one damages the host itself and is invisible in the seed.
        ("an embedded tab", "https://issuer\t.example/realms/exhibit", r"'\\t'"),
        (
            "a trailing carriage return",
            "https://issuer.example/realms/exhibit\r\n",
            r"'\\r'",
        ),
        # Case-folded by the parse, so the guard compares `https` and the
        # directory renders `HTTPS`.
        ("an upper-case scheme", "HTTPS://issuer.example/realms/exhibit", "lower case"),
        # The one shape a round-trip through the parse would not catch: it
        # survives unchanged and is simply an address no token names.
        ("no scheme at all", "//issuer.example/realms/exhibit", "carries no scheme"),
    ],
)
def test_an_issuer_the_parse_would_change_is_refused(
    damage: str, authored: str, names: str, position: str
) -> None:
    """ADR-0015: the authored string is canonical, at either issuer.

    The cross-product is the assertion. The rule is that an issuer is taken
    exactly as written — which is a claim about **both** of them, and a loader
    that validated only the second would still key seven directory rows at an
    address nothing serves whenever the first is the damaged one. Parameterised
    over the position as well as the damage so that a refactor narrowing the
    rule to one issuer goes red on half the rows rather than none.

    Each row pins its own fragment of the message, because all three refusals
    would otherwise pass on the word `issuer` alone and the test would not say
    which one fired.
    """
    other = "http://issuer.example/realms/exhibit"
    if position == "issuer":
        text = _seed_text(subject="somebody", issuer=authored)
    else:
        text = _seed_text(subject="somebody", issuer=other, tls_issuer=authored)

    with pytest.raises(ValueError, match=names):
        read_identity_seed(text)


def test_a_damaged_issuer_is_refused_before_the_realm_is_taken_from_it() -> None:
    """The order is what makes the message name the slip rather than its consequence.

    A protocol-relative issuer with a trailing slash carries two defects at
    once. `realm_of` would report the empty last path segment — true, and not
    what the author typed — so the canonical-form refusal runs first and names
    the missing scheme.
    """
    text = _seed_text(subject="somebody", issuer="//issuer.example/realms/exhibit/")

    with pytest.raises(ValueError, match="carries no scheme"):
        read_identity_seed(text)


def test_the_committed_issuers_are_already_canonical(seed: IdentitySeed) -> None:
    """The positive case, against the seed that ships rather than a constructed one.

    Nothing in the committed organisation moves under this rule, which is the
    claim `Seed renders clean` rests on: the refusals above are about seeds an
    author is in the middle of writing, not about this one.
    """
    for issuer in seed.issuers:
        assert issuer == issuer.strip()
        assert issuer.split(":", 1)[0] in {"http", "https"}
        assert not any(
            character.isascii() and (character.isspace() or not character.isprintable())
            for character in issuer
        )


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
    text = _seed_text(subject="twice", username="first.person") + _person_block(
        subject="twice", username="second.person"
    )

    with pytest.raises(ValueError, match="duplicate subject"):
        read_identity_seed(text)


def test_a_duplicated_username_fails_at_the_renderer() -> None:
    """Two people cannot share a username; the realm import would be rejected.

    Not a directory key — the directory is keyed by issuer and subject, and
    :class:`~mcp_erp.authorization.identity.Identity` says why. It is the realm's
    key, and a user import naming one twice is a file the authorization server
    refuses whole, which is the failure this loader exists to move earlier.
    """
    text = _seed_text(subject="first", username="shared.name") + _person_block(
        subject="second", username="shared.name"
    )

    with pytest.raises(ValueError, match=re.escape("duplicate username 'shared.name'")):
        read_identity_seed(text)


def test_an_issuer_with_no_last_path_segment_fails_at_the_renderer() -> None:
    """A trailing slash would otherwise render an empty realm name everywhere.

    The realm is the issuer's last path segment rather than a second authored
    copy of it, so the one input that segment cannot be taken from has to be
    refused where it is read. Nothing downstream would notice: the user import
    would carry ``"realm": ""`` and the rendering would be wrong in every file
    at once, with no line of the seed to point at.
    """
    with pytest.raises(ValueError, match="names no realm"):
        read_identity_seed(_seed_text(subject="anybody", issuer="https://issuer.example/realms/"))


@pytest.mark.parametrize(
    ("column", "missing"),
    [
        # `null` and the key being absent altogether are one branch in the
        # loader and two ways to author the same defect, so both are stated —
        # the `.get()` that reads them cannot tell them apart, and a falsifier
        # for one is not a falsifier for the other until it is written down.
        ("roles", "    roles: null\n    realm_roles: []\n"),
        ("roles", "    realm_roles: []\n"),
        ("realm_roles", "    roles: []\n    realm_roles: null\n"),
        ("realm_roles", "    roles: []\n"),
    ],
)
def test_a_person_stating_no_roles_at_all_fails_as_a_seed_defect(column: str, missing: str) -> None:
    """Absent or null, which is a malformed row — not the empty list, which is Priya.

    ``roles: []`` is the role-column exception and ADR-0007 calls it
    load-bearing, so it stays legal. What is refused is the column being missing
    or ``null``, which reached ``sorted`` and reported itself as a `TypeError`
    from the standard library rather than as a defect naming the row.

    Both columns, because the loader reads them through one helper and a
    refusal asserted on only one of them is a refusal half asserted.
    """
    text = (
        "issuer: https://issuer.example/realms/exhibit\n"
        "password: not-a-secret\n"
        "cost_centres: []\n"
        "vendors: []\n"
        "people:\n"
        "  - name: A Person\n"
        "    subject: rolesless\n"
        "    username: a.person\n"
        "    cost_centre: P-1\n" + missing
    )

    with pytest.raises(ValueError, match=re.escape(f"'rolesless' states no {column!r}")):
        read_identity_seed(text)


@pytest.mark.parametrize(
    ("column", "authored"),
    [
        # The string is the case that costs nothing to author and nothing to
        # read back: YAML hands it over as a scalar, `sorted` walks it, and one
        # role becomes one role per character.
        ("roles", "    roles: erp.read\n    realm_roles: []\n"),
        ("realm_roles", "    roles: []\n    realm_roles: approver\n"),
        # The number is the same defect where the standard library does raise —
        # as a `TypeError` from inside `sorted`, naming neither the person nor
        # the column.
        ("roles", "    roles: 3\n    realm_roles: []\n"),
        ("realm_roles", "    roles: []\n    realm_roles: 3\n"),
    ],
)
def test_a_role_column_authored_as_one_scalar_is_refused(column: str, authored: str) -> None:
    """`roles: erp.read` is eight roles of one character each, and nothing raised.

    The identity parsed, the directory got a row, and every call under it
    refused `role_missing` — from a line of the seed that reads correctly to a
    person. Both columns and both scalar kinds, because the loader reads them
    through one helper and the string is the only one the standard library lets
    through.
    """
    text = (
        "issuer: https://issuer.example/realms/exhibit\n"
        "password: not-a-secret\n"
        "cost_centres: []\n"
        "vendors: []\n"
        "people:\n"
        "  - name: A Person\n"
        "    subject: scalar-roles\n"
        "    username: a.person\n"
        "    cost_centre: P-1\n" + authored
    )

    with pytest.raises(ValueError, match=re.escape(f"'scalar-roles' states {column!r} as one")):
        read_identity_seed(text)


def test_a_person_holding_no_server_role_is_not_a_defect() -> None:
    """The empty list is the state Priya Raman is in, and the exhibit needs it.

    Stated beside the refusal above because the two are one line apart in the
    loader, and a tightening that swallowed this case would delete the
    scope-without-role state ADR-0007 keeps reachable.
    """
    seed = read_identity_seed(_seed_text(subject="no-roles", roles=[], realm_roles=["approver"]))

    assert seed.identities[0].roles == ()


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
    username: str = "a.person",
    issuer: str = "https://issuer.example/realms/exhibit",
    tls_issuer: str | None = None,
) -> str:
    """A one-person seed, for the cases the committed organisation cannot show.

    ``issuer`` is emitted **double-quoted**, which is the only way an arbitrary
    string survives YAML. Unquoted, a plain scalar has its leading and trailing
    whitespace stripped before the loader ever sees it — so the leading-space
    case would go green with its coverage silently gone — and a tab or a
    carriage return inside one is a scanner error, which is a different
    exception from a different layer. ``json.dumps`` emits a double-quoted
    scalar with the escapes YAML reads, the same way ``_person_block`` already
    emits the role lists. ``tls_issuer`` is emitted the same way and for the
    same reason, which is why it is a parameter here rather than a line the
    caller appends.
    """
    second = "" if tls_issuer is None else f"tls_issuer: {json.dumps(tls_issuer)}\n"
    return (
        f"issuer: {json.dumps(issuer)}\n" + second + "password: not-a-secret\n"
        "cost_centres: []\n"
        "vendors: []\n"
        "people:\n" + _person_block(subject, roles, realm_roles, username)
    )


def _person_block(
    subject: str,
    roles: list[str] | None = None,
    realm_roles: list[str] | None = None,
    username: str = "a.person",
) -> str:
    """One `people` entry, in the seed's own shape.

    ``username`` is a parameter rather than a constant because a second block
    appended to a first is how the duplicate-key cases are built, and two of
    them turn on which key is duplicated — so a block that always carried the
    same username would make the subject case assert the username refusal.
    """
    return (
        f"  - name: A Person\n"
        f"    subject: {subject}\n"
        f"    username: {username}\n"
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

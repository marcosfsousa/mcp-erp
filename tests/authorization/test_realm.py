"""The hand-authored realm, and the properties an attack-suite row would remove.

ADR-0007 calls the realm *the exhibit* — a reader opens it to see the audience
mapper, the decoy client and the deliberate role drift. What a reader cannot do
is notice that one client quietly lost its challenge-method pin, so the
properties the suite's `removal` lines name are asserted here, against the
committed file, before any container is involved.

**These are the Docker-free half.** Three attack rows say in as many words that
their removal is an edit to this file — `pkce_downgrade_plain`,
`password_grant_refused`, `refresh_token_replay` — and each is a realm property
long before it is a wire behaviour. Asserting them here does not replace the
wire assertions those rows own; it means an edit that removes one fails a suite
that needs no network, on the pull request that made it.

They live in `tests/authorization/` for the reason
:mod:`tests.authorization.test_identity` does: identity provisioning is the one
layer-3-shaped job layer 2 owns outright, so it has to keep working with the
domain deleted, and the ejection job runs this directory whole.

The realm file is **authored**, unlike the user import beside it, so nothing
here re-renders anything. Every assertion reads the committed bytes.
"""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from mcp_erp.authorization.identity import (
    DIRECTORY_RENDERING,
    SEED,
    USER_IMPORT_RENDERING,
    read_identity_seed,
)

REPO = Path(__file__).parents[2]

REALM_FILE = REPO / "keycloak/import/mcp-erp-realm.json"
"""The authored realm: clients, scopes, mappers and roles, and no users."""

NEIGHBOUR_FILE = REPO / "keycloak/import/mcp-erp-neighbour-realm.json"
"""The second issuer, with its own signing keys and its own real flow."""

CAPABILITY_SCOPES = ("erp.read", "erp.write", "erp.decide")
"""The three capability scopes ADR-0012 fixed. Layer 2 owns the vocabulary."""

DECIDING_ROLES = {"approver", "unlimited_approver"}
"""The two roles `erp.decide` maps from.

ADR-0012: Ingrid Holm holds `unlimited_approver` and not `approver`, so a
single-valued mapping would unlist `approve_requisition` for her and make the
above-threshold branch she exists for unreachable.
"""

PLACEHOLDER = re.compile(r"\$\{([^}]*)\}")
"""Keycloak's `${VAR}` substitution, which resolves from the environment only.

ADR-0007's third banked trap: an unresolved placeholder is left literally in
place rather than erroring, silently installing the string `${MCP_RESOURCE_URL}`
as an audience value.
"""


@pytest.fixture(scope="module")
def realm() -> dict[str, Any]:
    """The authored realm, as it sits on disk."""
    return _read(REALM_FILE)


@pytest.fixture(scope="module")
def neighbour() -> dict[str, Any]:
    """The neighbour realm, as it sits on disk."""
    return _read(NEIGHBOUR_FILE)


@pytest.fixture(scope="module")
def user_import() -> dict[str, Any]:
    """The generated user import, which the realm file must be able to receive."""
    return _read(REPO / USER_IMPORT_RENDERING)


@pytest.fixture(scope="module")
def cast_subjects() -> set[str]:
    """Every subject the principal directory holds, read from the committed rendering."""
    directory = json.loads((REPO / DIRECTORY_RENDERING).read_text(encoding="utf-8"))
    subjects: set[str] = {row["subject"] for row in directory}
    return subjects


# ─── The seam between the authored realm and the generated import ──────────


def test_the_realm_file_carries_no_users(realm: dict[str, Any]) -> None:
    """The split ADR-0007 was amended to make structural.

    *Hand-written clients, generated users* is unenforceable in one file. Two
    files make it a property: this one has no `users` key to hand-edit, and the
    one beside it is never edited at all.
    """
    assert "users" not in realm


def test_the_realm_and_the_user_import_name_the_same_realm(
    realm: dict[str, Any], user_import: dict[str, Any]
) -> None:
    """A directory import pairs the two by name, and a mismatch imports nothing."""
    assert realm["realm"] == user_import["realm"]


def test_the_realm_name_is_the_issuer_s_last_path_segment() -> None:
    """The seed's issuer and the realm's name are one fact, held in one place.

    The generator already derives the import's realm this way. Asserting it of
    the authored file too is what stops an edit to either from producing two
    realms that only nearly agree.
    """
    seed = read_identity_seed((REPO / SEED).read_text(encoding="utf-8"))

    assert _read(REALM_FILE)["realm"] == seed.realm


def test_every_realm_role_the_import_references_is_declared(
    realm: dict[str, Any], user_import: dict[str, Any]
) -> None:
    """An undeclared role is imported as nothing, and the exhibit loses a branch.

    The generator treats issuer-side names as opaque strings and validates them
    against nothing — deliberately, since interpreting them would erase Priya
    Raman's divergence. That leaves exactly one thing unchecked, and this is it:
    the realm has to declare what the import assigns, or a user is imported
    without the role and `erp.decide` silently stops being issued.
    """
    declared = {role["name"] for role in realm["roles"]["realm"]}
    referenced = {role for user in user_import["users"] for role in user["realmRoles"]}

    assert referenced <= declared


def test_the_deciding_roles_are_declared(realm: dict[str, Any]) -> None:
    """Both roles `erp.decide` maps from exist as realm roles."""
    declared = {role["name"] for role in realm["roles"]["realm"]}

    assert DECIDING_ROLES <= declared


# ─── Properties an attack-suite row names as its own removal ───────────────


def test_every_client_is_public(realm: dict[str, Any], neighbour: dict[str, Any]) -> None:
    """No secret exists anywhere in the repository.

    Every real client the exhibit targets runs on a user's machine and cannot
    hold one, so a confidential conformance client would have made the
    load-bearing offline proof exercise a flow no real client uses.
    """
    for client in _clients(realm) + _clients(neighbour):
        assert client["publicClient"] is True, client["clientId"]
        assert "secret" not in client, client["clientId"]


def test_every_client_pins_the_sha_256_challenge_method(
    realm: dict[str, Any], neighbour: dict[str, Any]
) -> None:
    """`pkce_downgrade_plain`'s removal, in the file it names.

    The pin is per client, and the discovery document does not reflect
    per-client policy — the realm advertises `plain` and `S256` regardless. So
    the pin is the whole of the control, and it is invisible in the metadata a
    reader would think to check.
    """
    for client in _clients(realm) + _clients(neighbour):
        attributes = client.get("attributes", {})

        assert attributes.get("pkce.code.challenge.method") == "S256", client["clientId"]


def test_no_client_enables_direct_access_grants(
    realm: dict[str, Any], neighbour: dict[str, Any]
) -> None:
    """`password_grant_refused`'s removal is *enable it on any client in the realm file*.

    Username and password straight to the token endpoint would make the
    conformance client trivial, and it is the flow OAuth 2.1 removed. Turning it
    off and asserting that it is off converts a thing we did not use into a
    thing the realm refuses.
    """
    for client in _clients(realm) + _clients(neighbour):
        assert client["directAccessGrantsEnabled"] is False, client["clientId"]


def test_refresh_tokens_rotate_with_zero_reuse(realm: dict[str, Any]) -> None:
    """RFC 9700 §4.14.2, binding because every client here is public.

    Sender-constraining needs mutual TLS or proof-of-possession, neither in
    scope, which leaves rotation. `refresh_token_replay` names the removal:
    turn rotation off, or allow reuse.
    """
    assert realm["revokeRefreshToken"] is True
    assert realm["refreshTokenMaxReuse"] == 0


def test_the_realm_issues_five_minute_tokens(realm: dict[str, Any]) -> None:
    """Five minutes keeps ADR-0002's published `ttlMs` cap meaningful.

    Sixty seconds would degenerate `min(5 min, remaining token lifetime)` to
    always picking the token; an hour would make the cap decoration.
    """
    assert realm["accessTokenLifespan"] == 300


def test_the_probe_client_overrides_its_lifespan_to_ten_seconds(realm: dict[str, Any]) -> None:
    """`token_expired` is a ten-second wait rather than a fake clock."""
    probe = _client(realm, "mcp-expiry-probe")

    assert probe["attributes"]["access.token.lifespan"] == "10"


# ─── Four clients, one stated job each ─────────────────────────────────────


def test_the_four_clients_exist(realm: dict[str, Any]) -> None:
    """ADR-0007's table, as membership."""
    expected = {
        "mcp-conformance",
        "mcp-conformance-decoy",
        "mcp-conformance-bare",
        "mcp-expiry-probe",
    }

    assert {client["clientId"] for client in _clients(realm)} == expected


def test_the_decoy_is_audience_bound_to_another_resource(realm: dict[str, Any]) -> None:
    """`audience_confusion` needs a token legitimately issued for somebody else.

    Minting one ourselves would exercise the same branch while asserting
    against a token we invented, so the decoy is a real client for a real other
    resource — and its audience must not be ours.
    """
    ours = _audiences(realm, "mcp-conformance")
    decoy = _audiences(realm, "mcp-conformance-decoy")

    assert decoy
    assert not (decoy & ours)


def test_the_bare_client_carries_no_audience_at_all(realm: dict[str, Any]) -> None:
    """`audience_missing` is the fail-closed check, and it needs a real bare token."""
    assert _audiences(realm, "mcp-conformance-bare") == set()


def test_the_probe_and_the_conformance_client_share_our_audience(realm: dict[str, Any]) -> None:
    """The expiry probe differs from the normal client in its lifespan and nothing else.

    ADR-0007 rejected the probe doubling as the audience-less client precisely
    so a failure cannot be attributed to expiry or to the missing audience.
    """
    assert _audiences(realm, "mcp-expiry-probe") == _audiences(realm, "mcp-conformance")


def test_consent_is_required_on_every_client(realm: dict[str, Any]) -> None:
    """The only place a human meets the delegation ceiling as a choice."""
    for client in _clients(realm):
        assert client["consentRequired"] is True, client["clientId"]


# ─── Scopes: the capability vocabulary, and what gates it ──────────────────


def test_the_three_capability_scopes_exist_and_are_optional(realm: dict[str, Any]) -> None:
    """Optional, so the client's own `scope` parameter is what narrows the grant.

    A default scope would arrive on every token and the ladder of four token
    shapes the matrix runs on would collapse to one.
    """
    conformance = _client(realm, "mcp-conformance")

    for scope in CAPABILITY_SCOPES:
        assert _client_scope(realm, scope) is not None, scope
        assert scope in conformance["optionalClientScopes"], scope
        assert scope not in conformance["defaultClientScopes"], scope


def test_each_capability_scope_carries_consent_screen_text(realm: dict[str, Any]) -> None:
    """Three lines on the screen, one per capability.

    The purchase-to-pay meaning of `decide` lives here and only here — it is a
    display field, and it never reaches the wire.
    """
    for scope in CAPABILITY_SCOPES:
        attributes = _client_scope(realm, scope)["attributes"]

        assert attributes["display.on.consent.screen"] == "true", scope
        assert attributes["consent.screen.text"], scope


def test_the_audience_scope_is_not_displayed_on_the_consent_screen(realm: dict[str, Any]) -> None:
    """It is infrastructure rather than a permission, so the screen shows three lines."""
    for scope in _audience_scopes(realm):
        attributes = scope.get("attributes", {})

        assert attributes.get("display.on.consent.screen") == "false", scope["name"]


def test_only_the_deciding_scope_is_gated_by_roles(realm: dict[str, Any]) -> None:
    """One role scope mapping, listing two roles.

    `erp.write` cannot be gated — ADR-0003 gates submitting by scope alone, so a
    mapping there would lock every submitter out of a scope they are entitled
    to. `erp.read` has no role behind it either: `auditor` widens which rows
    come back, it does not grant reading.
    """
    gated = {
        mapping["clientScope"]: set(mapping["roles"])
        for mapping in realm.get("scopeMappings", [])
        if "clientScope" in mapping
    }

    assert gated == {"erp.decide": DECIDING_ROLES}


# ─── The three traps ADR-0007 banked, each of which fails at runtime ───────


def test_the_realm_carries_a_subject_mapper_explicitly(realm: dict[str, Any]) -> None:
    """Trap 1, and we hit it by construction.

    A realm JSON containing a `clientScopes` array never gets Keycloak's
    built-in defaults created — including `basic`, which is where the access
    token's `sub` comes from since Keycloak 25. The audience mapper lives on a
    hand-authored scope, so the array exists, so the subject mapper has to be
    declared. Without it the failure lands exactly where we read it: the `sub`
    join to the ERP rows and the principal directory.
    """
    mappers = [
        mapper
        for scope in realm["clientScopes"]
        for mapper in scope.get("protocolMappers", [])
        if mapper["protocolMapper"] == "oidc-sub-mapper"
    ]

    assert mappers


def test_the_subject_mapper_is_a_default_scope_on_every_client(realm: dict[str, Any]) -> None:
    """A subject mapper on an optional scope is a subject claim a client can decline."""
    carriers = {
        scope["name"]
        for scope in realm["clientScopes"]
        if any(
            mapper["protocolMapper"] == "oidc-sub-mapper"
            for mapper in scope.get("protocolMappers", [])
        )
    }

    for client in _clients(realm):
        assert carriers & set(client["defaultClientScopes"]), client["clientId"]


def test_the_profile_check_is_disabled_in_both_realms(
    realm: dict[str, Any], neighbour: dict[str, Any]
) -> None:
    """A fourth trap, found the way the other three were — by a flow stopping on it.

    ADR-0007 banks *imported passwords are temporary by default* as the required
    action that hangs a headless flow. `VERIFY_PROFILE` is a second one, and an
    empty `requiredActions` on the user does not prevent it: it fires from
    Keycloak's declarative user profile, which marks email, first name and last
    name required, and the Cast carries none of the three.

    That absence is the governing rule holding. No field of a profile changes an
    authorization decision, and ADR-0003 rejected `email` as a directory key on
    the record — so the realm turns the check off rather than the seed growing
    three columns to satisfy it.

    Measured: the flow reached `login-actions/required-action?execution=VERIFY_PROFILE`
    instead of a redirect carrying a code.
    """
    for document in (realm, neighbour):
        actions = {action["alias"]: action for action in document.get("requiredActions", [])}

        assert "VERIFY_PROFILE" in actions, document["realm"]
        assert actions["VERIFY_PROFILE"]["enabled"] is False, document["realm"]


def test_every_placeholder_carries_a_default() -> None:
    """Trap 3: an unresolved placeholder is left literally in place rather than erroring.

    `${MCP_RESOURCE_URL}` with no default installs that string as an audience
    value and every token silently becomes audience-bound to a literal. A
    default means the realm is complete on its own and Compose's environment is
    an override rather than a requirement.
    """
    for path in (REALM_FILE, NEIGHBOUR_FILE):
        for placeholder in PLACEHOLDER.findall(path.read_text(encoding="utf-8")):
            assert ":" in placeholder, placeholder
            assert placeholder.split(":", 1)[1], placeholder


def test_no_credential_is_temporary_anywhere_in_the_authored_realms(
    realm: dict[str, Any], neighbour: dict[str, Any]
) -> None:
    """Trap 2, which hangs a headless flow on a form it does not expect.

    The generated import is asserted by :mod:`tests.authorization.test_identity`.
    The neighbour realm's user is authored, so it is asserted here.
    """
    for document in (realm, neighbour):
        for user in document.get("users", []):
            assert user["requiredActions"] == []
            for credential in user["credentials"]:
                assert credential["temporary"] is False


# ─── The access token names nothing in the domain ──────────────────────────


def test_no_mapper_puts_a_role_on_the_wire(
    realm: dict[str, Any], neighbour: dict[str, Any]
) -> None:
    """Realm roles are an issuance-time gate only.

    `unlimited_approver` is unambiguously layer-3 vocabulary, and putting it in
    the token would make the token contract itself domain-shaped — clone this
    repository for another purpose and the wire format still talks about
    purchasing. Suppression is the default outcome of a hand-authored
    `clientScopes` array; inclusion would be the deliberate act, so this
    asserts that nobody took it.
    """
    forbidden = {
        "oidc-usermodel-realm-role-mapper",
        "oidc-usermodel-client-role-mapper",
        "oidc-usermodel-property-mapper",
        "oidc-usermodel-attribute-mapper",
    }

    for document in (realm, neighbour):
        for scope in document.get("clientScopes", []):
            for mapper in scope.get("protocolMappers", []):
                assert mapper["protocolMapper"] not in forbidden, mapper["name"]


# ─── The neighbour realm ───────────────────────────────────────────────────


def test_the_neighbour_is_a_different_realm_with_one_client(
    realm: dict[str, Any], neighbour: dict[str, Any]
) -> None:
    """A genuinely different issuer, not a token we invented."""
    assert neighbour["realm"] != realm["realm"]
    assert len(_clients(neighbour)) == 1


def test_the_neighbour_token_is_perfect_except_for_who_issued_it(
    realm: dict[str, Any], neighbour: dict[str, Any]
) -> None:
    """`foreign_issuer_token` asserts the `iss` check, so nothing else may fail first.

    Same audience and a subject the directory holds means the only thing wrong
    with a neighbour token is the realm that minted it. A neighbour bound to its
    own audience would be refused by the audience comparison and the row would
    pass while proving nothing about `iss`.
    """
    assert _audiences(neighbour, _clients(neighbour)[0]["clientId"]) == _audiences(
        realm, "mcp-conformance"
    )


def test_the_neighbour_asserts_a_subject_the_directory_holds(
    neighbour: dict[str, Any], cast_subjects: set[str]
) -> None:
    """The one value the neighbour realm copies from the seed, policed rather than trusted.

    The directory is keyed by issuer *and* subject, so this collides with
    nothing — and it is what makes `foreign_issuer_token`'s removal meaningful.
    Skip the `iss` check with a *foreign* subject and the call still fails, at
    the directory, on `role_missing`: the row would go red on removal while
    proving nothing about the issuer. With this subject, removing the check
    lets the call through, which is the thing the row exists to forbid.

    **It is a claim rather than a user id, and that was forced.** A Keycloak user
    id is the primary key of `USER_ENTITY` across the whole database, not per
    realm, so importing a second user with an id the Cast already uses fails the
    boot outright — measured, on 26.7.1. The subject therefore comes from a
    hardcoded claim mapper, and the user beneath it carries a generated id
    nothing reads.
    """
    asserted = {
        mapper["config"]["claim.value"]
        for scope in neighbour["clientScopes"]
        for mapper in scope.get("protocolMappers", [])
        if mapper["protocolMapper"] == "oidc-hardcoded-claim-mapper"
        and mapper["config"]["claim.name"] == "sub"
    }

    assert asserted
    assert asserted <= cast_subjects


def test_no_neighbour_user_reuses_a_cast_identifier(
    neighbour: dict[str, Any], cast_subjects: set[str]
) -> None:
    """The boot failure that produced the mapper above, asserted so it stays fixed.

    `USER_ENTITY.ID` is unique across the database rather than per realm, so a
    neighbour user whose `id` is one of the Cast's subjects is a duplicate-key
    error during import — and Compose reports it as a container that started and
    then stopped, several steps from the file that caused it.
    """
    for user in neighbour["users"]:
        assert user.get("id") not in cast_subjects, user["username"]


def test_the_neighbour_user_takes_the_password_the_seed_states() -> None:
    """The second value the neighbour copies from the seed, and it fails silently.

    The token helper logs every Person in with the seed's password, this one
    included. Authored beside the realm, the copy has nothing holding it: change
    the seed and the foreign-issuer flow stops working, with the authorization
    server reporting a rejected password and nothing pointing at the file that
    went stale. Its *subject* is already policed above; this is the other half.

    The neighbour is authored rather than rendered on purpose — it is not the
    Cast, and ADR-0007's split governs the realm the Cast lives in. Authored
    still means checked.
    """
    seed = read_identity_seed((REPO / SEED).read_text(encoding="utf-8"))
    neighbour = _read(NEIGHBOUR_FILE)

    for user in neighbour["users"]:
        for credential in user["credentials"]:
            assert credential["value"] == seed.password, user["username"]


def _read(path: Path) -> dict[str, Any]:
    """One realm document, parsed."""
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return document


def _clients(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Every client a realm document declares."""
    clients: list[dict[str, Any]] = document.get("clients", [])
    return clients


def _client(document: dict[str, Any], client_id: str) -> dict[str, Any]:
    """One client, by the identifier the wire uses."""
    for client in _clients(document):
        if client["clientId"] == client_id:
            return client
    raise AssertionError(f"no client {client_id!r} in realm {document['realm']!r}")


def _client_scope(document: dict[str, Any], name: str) -> dict[str, Any]:
    """One client scope, by name."""
    for scope in document.get("clientScopes", []):
        if scope["name"] == name:
            scope_document: dict[str, Any] = scope
            return scope_document
    raise AssertionError(f"no client scope {name!r} in realm {document['realm']!r}")


def _audience_scopes(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Every client scope carrying an audience mapper."""
    return [
        scope
        for scope in document.get("clientScopes", [])
        if any(
            mapper["protocolMapper"] == "oidc-audience-mapper"
            for mapper in scope.get("protocolMappers", [])
        )
    ]


def _audiences(document: dict[str, Any], client_id: str) -> set[str]:
    """Every audience value one client's *default* scopes put in its tokens.

    Default rather than every linked scope, because an audience on an optional
    scope is an audience the client can decline — which would make the binding
    a property of the request rather than of the resource.
    """
    client = _client(document, client_id)
    default = set(client["defaultClientScopes"])

    return {
        mapper["config"]["included.custom.audience"]
        for scope in _audience_scopes(document)
        if scope["name"] in default
        for mapper in scope["protocolMappers"]
        if mapper["protocolMapper"] == "oidc-audience-mapper"
    }

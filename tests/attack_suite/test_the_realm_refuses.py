"""Three rows the authorization server keeps, not the resource server.

Scenarios: `pkce_downgrade_plain`, `password_grant_refused` and
`refresh_token_replay`. They are in the attack suite because ADR-0007 makes the
realm part of the exhibit — *"a reader opens the realm files to see the audience
mapper, the decoy client and the deliberate role drift"* — and a realm nobody
asserts against is a configuration file, not an exhibit.

**Each one turns a flow we do not use into a flow the realm refuses.** That is
the difference the three rows exist to make: *we never send a password to the
token endpoint* is a statement about our client, and any other client of this
realm could send one tomorrow. What is asserted here is that the realm would
refuse it.

**Every removal here is an edit to a committed file**, which is what makes them
performable: enable direct access grants on a client, clear a challenge-method
pin, turn off refresh rotation. Two of the three are asserted against **every
client the realm file declares**, read from the file itself, because the recorded
removal says *any client* and a list written out here would go stale the day a
sixth client arrives.

**The metadata advertises both flows, and that is not a contradiction.** Realm
metadata reports realm-wide capability; the refusals below are per client. Both
are asserted, because the caveat is ADR-0007's own and a reader who saw only the
document would conclude the opposite of what the realm does.
"""

import json
import secrets
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from scenarios import exercises

import fixtures
import tokens
from tokens import (
    LOGIN_FORM,
    PASSWORD,
    REDIRECT_URI,
    challenge_for,
    metadata,
    mint,
    reachable,
)

REALM_FILE = "keycloak/import/mcp-erp-realm.json"
"""The authored half of the realm, and the file two removals below name.

Read rather than restated. ADR-0007 decided these clients are hand-written JSON
because *"that section is the exhibit; a generated blob is worse evidence than
authored intent"* — so the exhibit is what the assertions run against.
"""

TIMEOUT = 30.0


def _clients() -> Iterator[str]:
    """Every client the realm declares, in the order the file declares them."""
    document = json.loads((fixtures.REPO / REALM_FILE).read_text(encoding="utf-8"))
    for client in document["clients"]:
        yield str(client["clientId"])


def _authorization_request(client_id: str, **overrides: str) -> httpx.Response:
    """One authorization request, not followed, so the redirect *is* the answer.

    The same shape `tokens.py` performs, with whatever this test wants to be
    wrong about passed in — which is the only difference between an attack here
    and an ordinary mint.
    """
    document = metadata()
    parameters = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "openid erp.read",
        "state": secrets.token_urlsafe(16),
        "code_challenge": challenge_for(secrets.token_urlsafe(64)),
        "code_challenge_method": "S256",
        **overrides,
    }
    with httpx.Client(follow_redirects=False, timeout=TIMEOUT) as http:
        return http.get(reachable(str(document["authorization_endpoint"])), params=parameters)


def _post_to_the_token_endpoint(data: dict[str, str]) -> httpx.Response:
    """One form post to the token endpoint, whatever it answers."""
    with httpx.Client(timeout=TIMEOUT) as http:
        return http.post(reachable(str(metadata()["token_endpoint"])), data=data)


@exercises("pkce_downgrade_plain")
def test_pkce_downgrade_plain() -> None:
    """A client downgrading its challenge method to `plain` is refused the code.

    Scenario: `pkce_downgrade_plain`, `basis: adr`, sourced to ADR-0007 §Every
    client is public, and the weak challenge method is refused.

        removal: Clear the per-client challenge-method pin in the realm file.

    **`basis: adr` and not `clause`, and the row's `context` field says why.** The
    MUST that exists — *"MCP clients MUST use the S256 code challenge method when
    technically capable"* — governs **clients**, and what is asserted here is a
    **server** refusal. Nothing in either document requires an authorization
    server to reject `plain`. Rewording the row could not fix that, because the
    clause simply does not govern what this asserts; the obligation is ADR-0007's
    per-client pin, and the clause rides along as context.

    The refusal arrives as a redirect back to the client carrying
    `error=invalid_request`, which is where an authorization server puts an error
    it can attribute to a registered redirect URI.
    """
    refused = _authorization_request(tokens.CONFORMANCE_CLIENT, code_challenge_method="plain")

    assert refused.status_code == httpx.codes.FOUND
    location = str(refused.headers["location"])
    assert location.startswith(REDIRECT_URI)

    # Parsed rather than substring-matched, so the assertion is about which
    # parameter carries which value — the same reason `rpc.challenge` parses a
    # `WWW-Authenticate` header instead of looking for words in it.
    answer = {name: values[0] for name, values in parse_qs(urlparse(location).query).items()}
    assert answer["error"] == "invalid_request"
    assert "code challenge method" in answer["error_description"], answer
    assert "code" not in answer


@exercises("pkce_downgrade_plain")
def test_the_same_request_with_the_strong_method_is_not_refused() -> None:
    """The control: `S256` reaches the login form, so the method is what was refused.

    Scenario: `pkce_downgrade_plain`.

    Without it the row would pass on a client that was disabled, misspelled or
    unregistered — every one of which also answers with an error redirect.
    """
    permitted = _authorization_request(tokens.CONFORMANCE_CLIENT)

    assert permitted.status_code == httpx.codes.OK
    assert LOGIN_FORM in permitted.text


@exercises("pkce_downgrade_plain")
def test_the_metadata_still_advertises_the_weak_method() -> None:
    """ADR-0007's binding caveat, asserted so nobody reads the row as being about discovery.

    Scenario: `pkce_downgrade_plain`.

    The pin is **per client** and authorization server metadata reports what the
    realm supports, so `plain` is advertised and will stay advertised. This row
    asserts that the server **refuses a plain challenge for our client** — never
    that the document omits it — and a reader who found `plain` in the metadata
    and no assertion here would reasonably conclude the row was aspirational.
    """
    assert "plain" in metadata()["code_challenge_methods_supported"]
    assert "S256" in metadata()["code_challenge_methods_supported"]


@exercises("password_grant_refused")
def test_password_grant_refused() -> None:
    """Username and password at the token endpoint, refused for every client in the realm.

    Scenario: `password_grant_refused`, `basis: clause`, `MUST NOT` — RFC 9700
    §2.4: *"The resource owner password credentials grant [RFC6749] MUST NOT be
    used."*

        removal: Enable Direct Access Grants on any client in the realm file.

    **Every client, read from the realm file**, because the removal says *any
    client* — one enabled client is the whole defect, and it would be the one
    nobody remembered to check. A written-out list here would pass while a sixth
    client shipped with the flow switched on.

    The credentials are **real**: the Cast's own conspicuously fake password, the
    one that works at the login form three lines into every other suite in this
    directory. A refusal against a wrong password would say nothing about the
    grant.

    **RFC 9700 rather than the obvious document, deliberately.** OAuth 2.1
    draft-13 removes this grant by *omission* — it defines the flow nowhere, so
    there is no sentence in it to quote, and an absence cannot be cited. RFC 9700
    §2.4 carries the only explicit prohibition at a pinned revision.
    """
    for client_id in _clients():
        refused = _post_to_the_token_endpoint(
            {
                "grant_type": "password",
                "client_id": client_id,
                "username": "tomas.weber",
                "password": PASSWORD,
                "scope": "openid erp.read",
            }
        )

        assert refused.status_code == httpx.codes.BAD_REQUEST, (client_id, refused.text)
        answer: dict[str, Any] = refused.json()
        assert answer["error"] == "unauthorized_client", (client_id, answer)
        assert "access_token" not in answer, client_id


@exercises("password_grant_refused")
def test_the_metadata_still_advertises_the_grant() -> None:
    """The same caveat as the challenge method, one flow along.

    Scenario: `password_grant_refused`.

    Keycloak reports `password` in `grant_types_supported` realm-wide, and every
    client refuses it. The row is about what happens when the flow is attempted,
    and asserting the document here is what keeps a reader from taking the
    advertisement for the answer.
    """
    assert "password" in metadata()["grant_types_supported"]


@exercises("refresh_token_replay")
def test_refresh_token_replay() -> None:
    """A refresh token redeemed twice revokes the grant it belonged to.

    Scenario: `refresh_token_replay`, `basis: clause`, `MUST` — RFC 9700
    §4.14.2: *"Authorization servers MUST utilize one of these methods to detect
    refresh token replay by malicious actors for public clients:
    sender-constrained refresh tokens … refresh token rotation."*

        removal: Turn off refresh token rotation, or allow reuse, in the realm
                 file.

    **Binding because every client here is public**, which is the condition the
    clause names — ADR-0007 makes them all public, since a confidential client
    would need a secret nobody could keep in an exhibit that ships its own realm.

    Three redemptions, and the third is the row. The first rotates. The second
    replays the value the first consumed and is refused. The third presents the
    **rotated** token — the one the honest client is holding, and would still be
    entitled to under mere reuse detection — and it is refused too, because
    detecting a replay revokes the grant rather than the token. That is what
    turns a stolen refresh token from a persistent credential into a
    self-destructing one.
    """
    minted = mint("mei.tanaka", ["erp.read"])
    assert minted.refresh_token is not None

    first = _post_to_the_token_endpoint(
        {
            "grant_type": "refresh_token",
            "client_id": tokens.CONFORMANCE_CLIENT,
            "refresh_token": minted.refresh_token,
        }
    )
    assert first.status_code == httpx.codes.OK, first.text
    rotated = str(first.json()["refresh_token"])
    assert rotated != minted.refresh_token

    replayed = _post_to_the_token_endpoint(
        {
            "grant_type": "refresh_token",
            "client_id": tokens.CONFORMANCE_CLIENT,
            "refresh_token": minted.refresh_token,
        }
    )

    assert replayed.status_code == httpx.codes.BAD_REQUEST
    assert replayed.json()["error"] == "invalid_grant"

    after_the_replay = _post_to_the_token_endpoint(
        {
            "grant_type": "refresh_token",
            "client_id": tokens.CONFORMANCE_CLIENT,
            "refresh_token": rotated,
        }
    )

    assert after_the_replay.status_code == httpx.codes.BAD_REQUEST
    assert after_the_replay.json()["error"] == "invalid_grant"
    assert "access_token" not in after_the_replay.json()

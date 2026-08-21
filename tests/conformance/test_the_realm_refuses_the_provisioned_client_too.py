"""The realm's refusals, asserted against the one client no realm file contains.

`tests/authorization/test_realm.py` and `tests/attack_suite/test_the_realm_refuses.py`
both read their clients out of `keycloak/import/mcp-erp-realm.json`, and both say
in as many words that they cover *every client the realm declares*. The client
this directory's flow uses is declared nowhere: it is provisioned at runtime from
a hosted Client Identity Metadata Document, its `clientId` **is** that document's
URL, and no file in this repository names it.

**That gap has already shipped a defect once.** #46 found this client accepting
`plain` and accepting no `code_challenge` at all, because the SHA-256 pin was a
per-client attribute and a per-client attribute cannot reach a client the realm
does not contain. `keycloak/README.md` calls it *the fifth* and this file calls
it *the sixth*: the realm declared four authored clients when #46 was written and
declares five now, so the ordinal moves and the client does not. It is named
rather than numbered everywhere below. The repair was a second `pkce-enforcer` policy
conditioned on `client-access-type: public`, which is the one thing every client
here has in common — and until this module, **nothing asserted the repair.**
Deleting that policy leaves all forty assertions in the two files above green
and puts the authorization endpoint back to answering `plain` with a login form.

**Here rather than in `tests/attack_suite/`, and the reason is the job.** Minting
this client requires the authorization server to dereference the document, and
that document's URL *is* the `clientId` — so a locally served copy is not a
stand-in for this client, it is a different one, and #46's repair was found on
this one. The profile would admit a local copy: `cimd-allow-permitted-domains`
lists `localhost` and `127.0.0.1` beside the exhibit's origin, and the condition
naming that origin belongs to the *other* policy. What cannot be served from
inside the compose network is the identity under test, and that is what makes
the assertion need egress. `Attack suite (wire)` states of itself that *nothing it asserts
depends on a service outside this repository*, and that sentence is worth more
than the cohesion of keeping the realm's refusals in one directory.
`Authorization code flow` already fetches this document, and already runs the
preflight step that tells a Pages outage apart from a regression.

**Every assertion is a refusal the running realm makes, never a field read back
out of it.** The admin API would answer these questions faster and would be
answering a different one: ADR-0007's caveat is that the pin is per client and
the metadata is realm-wide, so what a row may assert is the refusal. A stored
attribute saying `S256` is not a client that refuses `plain`.

**The request builders here are near-copies of
`tests/attack_suite/test_the_realm_refuses.py`'s, and they stay copies for now.**
The rule this repository applies to shared test tooling is the one `tokens.py`
and `requisitions.py` both state — a helper moves up beside them at its **third**
caller, because two is a coincidence and three is a pattern. This is the second.
When a third arrives, what moves up is the authorization request and the token
post; what cannot move is the client each one names, which is the whole
difference between the two files.
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from conformance_client import CLIENT_ID, METADATA, TIMEOUT, preflight
from tokens import LOGIN_FORM, PASSWORD, challenge_for, metadata, rebase

REDIRECT_URI = str(METADATA["redirect_uris"][0])
"""One of the two the document publishes, read from it rather than restated.

`conformance_client` makes the same argument about `client_id`: the document
cannot be corrected in place, so a second copy of anything in it is a second
thing to keep equal to a file whose divergence is a new version rather than a
fix.
"""

A_PERSON = "tomas.weber"
"""Any member of the Cast. Which one changes nothing here — no assertion below
reaches a role, a scope or a partition, because none of them is a property of the
client. He is the one `password_grant_refused` already names, so the two rows
that make the same request of two different client sets make it identically.
"""


@pytest.fixture(scope="module", autouse=True)
def document_is_served() -> None:
    """Name an external cause before any assertion below can be read as a regression.

    **This module never fetches the document; the authorization server does.**
    So a Pages outage arrives here as the control test finding a login form it
    expected and did not get — `assert 200 == 302`, on a suite whose subject is a
    challenge method. The preflight turns that into the one sentence that names
    the URL.

    A fixture rather than a test, unlike `test_authorization_code_flow`'s
    `test_the_published_document_answers_as_committed`, and that is the
    difference between the two claims. There the reachability of the document
    **is** an assertion the suite makes — ADR-0008's second mechanism, and half
    the reason the job may block. Here it is a precondition for three assertions
    about something else, so it belongs in setup: a reader running this file
    alone gets the same naming, and a reader running the directory gets the
    assertion from the sibling that owns it.
    """
    preflight()


def _authorization_request(**overrides: str) -> httpx.Response:
    """One authorization request as the provisioned client, not followed.

    The redirect **is** the answer — an authorization server puts an error it can
    attribute to a registered redirect URI there rather than in a status code —
    so following it would replace what is under test with whatever the callback
    address serves.

    Args:
        overrides: Whatever this caller wants to be wrong about, which is the
            only difference between an attack here and an ordinary flow.

    Returns:
        The response, with its `location` header intact.
    """
    parameters = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        # `openid` alone. The provisioned client is assigned the realm's default
        # scopes and no capability scope of its own, so asking for `erp.read`
        # would be refused as `invalid_scope` *before* the challenge method is
        # looked at — the same trap `test_the_realm_refuses` documents for two of
        # its five, arriving here for a different reason.
        "scope": "openid",
        "state": secrets.token_urlsafe(16),
        "code_challenge": challenge_for(secrets.token_urlsafe(64)),
        "code_challenge_method": "S256",
        **overrides,
    }

    with httpx.Client(follow_redirects=False, timeout=TIMEOUT) as http:
        return http.get(rebase(metadata()["authorization_endpoint"]), params=parameters)


def test_the_provisioned_client_reaches_the_login_form() -> None:
    """The control, and without it every refusal below asserts nothing.

    A client that is disabled, misspelled, unregistered or served from a document
    the authorization server could not dereference is refused too, and refused
    the same way. So this says the realm really does provision a client from this
    document and really does let it start a flow — which is what makes the two
    refusals below facts about the parameter that was wrong rather than about the
    client that sent it.
    """
    permitted = _authorization_request()

    assert permitted.status_code == httpx.codes.OK, permitted.status_code
    assert LOGIN_FORM in permitted.text


def test_the_provisioned_client_is_refused_the_weak_challenge_method() -> None:
    """`pkce_downgrade_plain`'s property, against the client that row cannot reach.

    The attack suite asserts this of the five clients the realm file declares, by
    reading their identifiers out of the file. This is the sixth, and it is the
    one that was wrong: #46 found it accepting `plain` because the pin was an
    attribute and it has none.

    Falsified by deleting the `proof-key-for-code-exchange` client policy — which
    leaves the five file clients still refusing, because each of them carries the
    attribute, and leaves nothing else in the repository red.
    """
    refused = _authorization_request(code_challenge_method="plain")

    assert refused.status_code == httpx.codes.FOUND, refused.status_code
    location = str(refused.headers["location"])
    assert location.startswith(REDIRECT_URI), location

    # Parsed rather than substring-matched, for the reason `rpc.challenge` parses
    # a `WWW-Authenticate` header: the assertion is about which parameter carries
    # which value, and `code` being absent is half of it.
    answer = {name: values[0] for name, values in parse_qs(urlparse(location).query).items()}
    assert answer["error"] == "invalid_request", answer
    assert "code challenge method" in answer["error_description"], answer
    assert "code" not in answer, answer


def test_the_provisioned_client_is_refused_the_password_grant() -> None:
    """`password_grant_refused`'s property, against the same client.

    RFC 9700 §2.4 puts a `MUST NOT` on the grant and that row's removal is
    *enable Direct Access Grants on any client in the realm file* — which is
    already the shape of the gap: a client that is in the realm and not in the
    file cannot have the flow switched on by editing a file, and could not be
    checked by reading one either.

    The credentials are the Cast's own conspicuously fake password, because a
    refusal against a wrong one would say nothing about the grant.
    """
    with httpx.Client(follow_redirects=False, timeout=TIMEOUT) as http:
        refused = http.post(
            rebase(metadata()["token_endpoint"]),
            data={
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "username": A_PERSON,
                "password": PASSWORD,
                "scope": "openid",
            },
        )

    answer: dict[str, Any] = refused.json()
    assert refused.status_code == httpx.codes.BAD_REQUEST, (refused.status_code, answer)
    assert answer["error"] == "unauthorized_client", answer
    assert "access_token" not in answer, answer

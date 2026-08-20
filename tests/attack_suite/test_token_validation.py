"""The token gate, whole: one row per word in the closed refusal vocabulary.

Eight scenarios — `audience_missing`, `foreign_issuer_token`, `audience_confusion`,
`token_passthrough`, `token_expired`, `signature_invalid`, `unknown_key` and
`malformed_token` — and the first two landed early, with #37, because that slice
is what made them reachable. The rest arrive here.

**The organising principle is `transport/tokens.py`'s own.** That module declares
seven descriptions and says of them that *"every one of them is reached by a named
attack scenario"*, which is the property that makes the vocabulary worth closing:
without distinguishable descriptions every row below would assert the same `401`
and no recorded removal would be observable. So the file reads as the vocabulary
does — `audience_missing`, `audience_mismatch`, `issuer_mismatch`, `token_expired`,
`signature_invalid`, `unknown_key`, `malformed` — with `token_passthrough` beside
`foreign_issuer_token`, the two rows one credential can be wrong in two ways for.

**Minted through a real flow against a real client wherever a real client can
produce the defect.** ADR-0007 provisions `mcp-conformance-bare` with no audience
mapper, `mcp-conformance-decoy` with somebody else's, `mcp-expiry-probe` with a
ten-second lifespan, and a whole second realm with its own signing keys, precisely
so these assertions run against tokens an authorization server actually issued.

**Two of the eight cannot be minted, and they say so where they sit.** No
authorization server issues a credential with a broken signature or a key
identifier it never published — those two are made here, out of a real token and
a real key respectively, and the alternative is not a better test but no test.
"""

import json
import time
from typing import Any

import httpx2
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from scenarios import exercises

import rpc
from tokens import NEIGHBOUR_CLIENT, NEIGHBOUR_REALM, decode_claims, metadata, mint, rebase

EXPIRY_PROBE = "mcp-expiry-probe"
"""ADR-0007's ten-second client. Its whole purpose is the row below."""

DECOY = "mcp-conformance-decoy"
"""A real client of another resource server, which is what makes a replay real."""

BARE = "mcp-conformance-bare"
"""No audience mapper at all — the fail-closed row's instrument."""


@exercises("audience_missing")
def test_audience_missing() -> None:
    """A token the authorization server minted with **no audience at all** is refused.

    Scenario: `audience_missing`, `basis: adr`, sourced to ADR-0006 §Refusals
    disclose the caller's own token, and nothing else.

        removal: Treat an absent `aud` as "not addressed to anyone else" and
                 allow it.

    Deliberately not a clause. Research 0003 established that nothing in the
    specification says what a server does with an audience-less token, so
    fail-closed is this project's decision rather than a conformance tick — which
    is why the row carries a project-ADR basis and a null normative strength.

    It is also the row the audience check as a whole rests on. Keycloak does not
    honour RFC 8707's `resource` parameter — the normative register's *Resource
    indicators unhonoured* deviation — so the resource server's own audience check
    is the load-bearing control; a server
    that waved through a token with no audience would have no control left.
    """
    minted = mint("priya.raman", ["erp.read"], client_id=BARE)
    assert "aud" not in minted.claims, minted.claims

    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "audience_missing"
    assert parameters["resource_metadata"] == rpc.METADATA_URL


@exercises("audience_confusion")
def test_audience_confusion() -> None:
    """A token legitimately issued for another resource server, replayed at us.

    Scenario: `audience_confusion`, `basis: clause`, `MUST` — *"MCP servers MUST
    only accept tokens specifically intended for themselves and MUST reject
    tokens that do not include them in the audience claim."*

        removal: Delete the `aud` comparison in token validation.

    **Nothing is wrong with this credential except who it is for.** Our own
    issuer minted it, our own signing key signed it, it is unexpired, and its
    subject is a person the directory knows — the audience is the only thing
    separating it from the article. That is what makes it a replay rather than a
    forgery: the same token, presented at the wrong door.

    `floor: true`, and it is one of the two rows map ship line `#8` names. The
    other is `audience_missing`, and the pair is the whole of the check: a server
    that compared audiences but waved through a token carrying none would pass
    this row and fail that one.
    """
    minted = mint("tomas.weber", ["hr.read"], client_id=DECOY)
    # Perfect except for the audience: our issuer, our signing key, a directory
    # subject — and somebody else's resource identifier.
    assert minted.claims["iss"] == _our_issuer()
    assert _audiences(minted.claims.get("aud")) and rpc.RESOURCE not in _audiences(
        minted.claims.get("aud")
    ), minted.claims
    assert minted.subject == "tomas-weber"

    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "audience_mismatch"


@exercises("foreign_issuer_token")
def test_foreign_issuer_token() -> None:
    """A structurally valid token from an issuer our metadata does not name is refused.

    Scenario: `foreign_issuer_token`, `basis: clause`, `MUST NOT` —
    *"MCP servers MUST NOT accept or transit any other tokens."*

        removal: Skip the `iss` check against the configured issuer.

    The neighbour realm makes this a real token rather than an invented one: its
    own signing keys, its own flow, and — through a hardcoded claim mapper —
    **the same subject and the same audience** as the genuine article. So it is
    perfect in every respect except who issued it, which is the only thing left
    for the refusal to be about.

    **Why the description is asserted and not only the status.** Our own key set
    does not contain the neighbour's key either, so a server with no `iss` check
    would still refuse this token — as `unknown_key`. Asserting the description
    is what makes the recorded removal observable: delete the `iss` comparison
    and this assertion fails, where a status-only assertion would not.
    """
    minted = mint("tomas.weber", ["erp.read"], client_id=NEIGHBOUR_CLIENT, realm=NEIGHBOUR_REALM)
    # Perfect except for the issuer: the subject is a directory row, and the
    # audience is ours.
    assert minted.subject == "tomas-weber"
    assert rpc.RESOURCE in _audiences(minted.claims.get("aud"))
    assert minted.claims["iss"].endswith(NEIGHBOUR_REALM)

    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "issuer_mismatch"


@exercises("token_passthrough")
def test_token_passthrough() -> None:
    """A credential another authorization server minted verifies — and is refused anyway.

    Scenario: `token_passthrough`, `basis: clause`, `MUST NOT` — *"MCP servers
    MUST NOT accept any tokens that were not explicitly issued for the MCP
    server."*

        removal: Accept any token that verifies, regardless of which issuer
                 minted it.

    **The recorded removal is what splits this from `foreign_issuer_token`, and
    the split is the reason this test does something that one does not.** That
    row's deletion is the `iss` *comparison*, and its falsifier is the word the
    challenge names. This row's deletion is a server that verifies a signature
    and asks no further question — the shape a passthrough implementation
    actually takes — so its falsifier has to establish that the signature
    genuinely verifies. Otherwise *refused* and *unverifiable* are the same
    result and the row asserts nothing about acceptance.

    So the neighbour's token is verified **here, against the neighbour's own
    published key set**, before being presented. That is a precondition held by a
    test rather than by trust, in the shape `row_probe_indistinguishable` uses
    for the foreign row it calls foreign: a token nobody could verify would make
    this pass for the wrong reason.

    It does not reopen `tokens.py`'s rule that nothing there validates a token.
    That rule is about a suite validating **our** tokens as a stand-in for the
    server's obligation, and this validates somebody else's as a statement about
    what was presented.
    """
    minted = mint("tomas.weber", ["erp.read"], client_id=NEIGHBOUR_CLIENT, realm=NEIGHBOUR_REALM)
    verified = _verified_by_the_issuer_that_minted_it(minted.access_token, realm=NEIGHBOUR_REALM)

    # It really is a token: the neighbour's own key set verifies its signature,
    # it names our resource in `aud`, and it is not expired.
    assert verified["sub"] == "tomas-weber"
    assert rpc.RESOURCE in _audiences(verified.get("aud"))
    assert verified["exp"] > time.time()

    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(response)["error"] == "invalid_token"


@exercises("token_expired")
def test_token_expired() -> None:
    """A token is refused the moment its lifetime ends, and the wait is real.

    Scenario: `token_expired`, `basis: clause`, `MUST` — *"Invalid or expired
    tokens MUST receive a HTTP 401 response."*

        removal: Delete the `exp` comparison.

    **A ten-second client rather than a fake clock**, which is ADR-0007's
    `mcp-expiry-probe` and the reason it exists. A frozen clock would assert
    against the test's own idea of the time; this asserts against the resource
    server's, which is the one that matters and the one an operator gets wrong.

    **The permitted call first, and it is not decoration.** Without it a
    refusal proves nothing about expiry — a token that was never going to work
    is refused at the ten-second mark too. The pair is one credential, twice,
    with nothing changing but the time.

    ADR-0006 pins **zero leeway** on `exp` precisely so this stays a ten-second
    test: with the conventional sixty seconds of forgiveness a ten-second token
    stays valid for seventy, and the row would need a wait nobody would keep.
    """
    minted = mint("tomas.weber", ["erp.read"], client_id=EXPIRY_PROBE)
    lifetime = int(minted.claims["exp"]) - int(minted.claims["iat"])
    assert lifetime <= 10, minted.claims

    fresh = rpc.post("tools/list", token=minted.access_token)
    assert fresh.status_code == httpx2.codes.OK, fresh.text

    # Slept against the token's own `exp` rather than a written-down ten, so a
    # realm that changed the lifespan changes the wait instead of the verdict.
    time.sleep(max(0.0, int(minted.claims["exp"]) - time.time()) + 1.0)

    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "token_expired"


@exercises("signature_invalid")
def test_signature_invalid() -> None:
    """A token whose payload was altered after signing is refused.

    Scenario: `signature_invalid`, `basis: clause`, `MUST` — *"Invalid or expired
    tokens MUST receive a HTTP 401 response."*

        removal: Verify the token's claims without verifying its signature.

    **The alteration is the one an attacker would actually make**: a real token
    for a real person, with the subject swapped for somebody else's and the
    signature left as it was. Under the recorded removal every claim in it reads
    as true and the caller becomes Priya Raman, who holds a different role set in
    a different position on the chain.

    Made here rather than minted, and it is the honest kind of made-up: no
    authorization server issues a credential with a broken signature, so the
    alternative to constructing one is not a better test but no test at all.
    """
    minted = mint("tomas.weber", ["erp.read"])
    tampered = _with_the_subject_swapped(minted.access_token, "priya-raman")

    # The alteration took: everything a server that skipped the signature would
    # read now says somebody else.
    assert decode_claims(tampered)["sub"] == "priya-raman"

    response = rpc.post("tools/list", token=tampered)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "signature_invalid"


@exercises("unknown_key")
def test_unknown_key() -> None:
    """A token signed with a key the issuer never published is refused.

    Scenario: `unknown_key`, `basis: clause`, `MUST` — *"Invalid or expired
    tokens MUST receive a HTTP 401 response."*

        removal: On an unknown key identifier, fall through to any cached key
                 instead of refetching and failing closed.

    **The one scenario that exercises ADR-0006's miss-driven key-set refetch.**
    A key identifier the cached set does not hold is exactly what a rotation
    looks like from here, so the server refetches — and this token is what
    proves the refetch **fails closed** rather than falling through to whatever
    was cached. The call after it is the other half: the refetch left the key set
    able to verify a genuine token, so failing closed is not the same as breaking.

    Signed with a key generated here and named with an identifier nobody
    published, which is the only way to reach a branch a real authorization
    server has no way to produce. The issuer claim is ours **deliberately**:
    validation compares `iss` before it looks at the key, so a foreign issuer
    would be refused one step earlier and this row would assert
    `foreign_issuer_token`'s branch instead of its own.
    """
    forged = _signed_with_an_unpublished_key(issuer=_our_issuer(), key_id="a-key-nobody-published")

    response = rpc.post("tools/list", token=forged)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "unknown_key"

    # Failing closed is not the same as breaking: a genuine token still verifies
    # against the key set the miss above made the server refetch.
    permitted = rpc.post("tools/list", token=mint("tomas.weber", ["erp.read"]).access_token)
    assert permitted.status_code == httpx2.codes.OK, permitted.text


@exercises("unknown_key")
def test_a_token_naming_no_key_at_all_is_refused_as_an_unknown_key() -> None:
    """A credential with no `kid` names no key we hold, and says so in those words.

    Scenario: `unknown_key`.

    The near miss worth pinning: it is structurally valid, so `malformed` would
    be a different claim than the true one — and a server that treated a missing
    key identifier as *use the only key you have* would accept this from anybody
    who could reach the issuer's published set. Both readings answer `401`, which
    is why the description rather than the status is what this asserts.
    """
    forged = _signed_with_an_unpublished_key(issuer=_our_issuer(), key_id=None)

    response = rpc.post("tools/list", token=forged)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(response)["error_description"] == "unknown_key"


@exercises("malformed_token")
def test_malformed_token() -> None:
    """A credential that is not a token produces a refusal rather than a `500`.

    Scenario: `malformed_token`, `basis: clause`, `MUST` — *"Invalid or expired
    tokens MUST receive a HTTP 401 response."*

        removal: Let the parse error propagate instead of mapping it to a
                 refusal.

    **The row is about the status code, not about the parse.** Under the removal
    the server answers `500`, which is a different sentence: it says the server
    broke, when what happened is that a caller presented nonsense. A stack trace
    in the response body is the usual second half of that answer.

    Two shapes, because they fail in different places: a value that is not
    segmented at all, and one that is segmented and carries no JSON.
    """
    for credential in ("not-a-token", "one.two", "aaa.bbb.ccc"):
        response = rpc.post("tools/list", token=credential)

        assert response.status_code == httpx2.codes.UNAUTHORIZED, credential
        parameters = rpc.challenge(response)
        assert parameters["error"] == "invalid_token", credential
        assert parameters["error_description"] == "malformed", credential


def _audiences(claim: object) -> set[str]:
    """The `aud` claim as a set, since it is one value or a list of them."""
    if isinstance(claim, str):
        return {claim}
    if isinstance(claim, list):
        return {str(value) for value in claim}
    return set()


def _our_issuer() -> str:
    """The issuer this server trusts, read from the token a real flow produced.

    Off a minted token rather than out of the seed, so a forgery below names the
    string the resource server is actually configured with — which is what the
    `iss` comparison it has to get past will be reading.
    """
    return str(mint("tomas.weber", ["erp.read"]).claims["iss"])


def _with_the_subject_swapped(token: str, subject: str) -> str:
    """One real token, re-encoded around a different subject, signature untouched.

    Base64url without padding, which is what a JSON Web Token's segments are —
    the same rule `tokens.decode_claims` reads them back under.
    """
    header, _, signature = token.split(".")
    claims = decode_claims(token) | {"sub": subject}
    altered = jwt.utils.base64url_encode(json.dumps(claims).encode("utf-8")).decode("ascii")

    return f"{header}.{altered}.{signature}"


def _signed_with_an_unpublished_key(*, issuer: str, key_id: str | None) -> str:
    """A well-formed token, signed with a key generated for this call and thrown away.

    Everything the resource server checks before the signature is correct — the
    issuer, the audience, an unexpired lifetime and a subject the directory
    holds — so what refuses it is the key and nothing standing in front of the
    key.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    return jwt.encode(
        {
            "iss": issuer,
            "aud": rpc.RESOURCE,
            "sub": "tomas-weber",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
            "scope": "erp.read",
        },
        key,
        algorithm="RS256",
        headers={} if key_id is None else {"kid": key_id},
    )


def _verified_by_the_issuer_that_minted_it(token: str, *, realm: str) -> dict[str, Any]:
    """The token's claims, verified against the key set that realm publishes.

    Discovered rather than written down, and rebased onto the address these
    requests can reach — the same two-addresses-one-identity rule `tokens.py`
    keeps, applied to somebody else's issuer.

    Raises:
        jwt.PyJWTError: The signature does not verify, which would make the
            precondition false rather than the assertion.
    """
    document = metadata(realm)
    keys = jwt.PyJWKClient(rebase(str(document["jwks_uri"])))
    claims: dict[str, Any] = jwt.decode(
        token,
        key=keys.get_signing_key_from_jwt(token).key,
        algorithms=["RS256"],
        audience=rpc.RESOURCE,
        issuer=str(document["issuer"]),
    )

    return claims

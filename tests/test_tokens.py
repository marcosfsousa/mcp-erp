"""The token helper's own unit tests — the half that needs no authorization server.

``tests/tokens.py`` is one flow driver with two kinds of code in it: small pure
functions, and the sequence of requests that strings them together. The sequence
is proved by using it — every wire suite mints through it, and the standalone
command in its ``__main__`` block is what #36 signs off against. These are the
pure functions, which have no such cover and would otherwise be proved only by a
failure three requests later that names none of them. The cache is here too,
because it is the one behaviour #36 singles out and it does not need a server to
exercise.

They stay Docker-free deliberately, and the `Lint and types` job runs this file
by name — a step inside an existing job rather than a ninth one, since ADR-0013
fixes the job set at eight and holds their names equal to the ruleset's required
contexts. A broken base64 padding rule is an ordinary Python defect, which is
what that job means.
"""

import base64
import hashlib
import json

import pytest

import tokens
from tokens import (
    Minted,
    authorization_code,
    cache_key,
    challenge_for,
    decode_claims,
    form_action,
    mint,
    scope_set,
)


def test_the_challenge_is_the_unpadded_url_safe_digest_of_the_verifier() -> None:
    """RFC 7636 §4.2, and the padding is the part implementations get wrong.

    ADR-0007 pins the method to `S256` at the server per client, so a helper
    that computed this wrongly would fail at the token endpoint with a message
    about a mismatched verifier and nothing pointing here.
    """
    verifier = "a" * 43

    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())

    assert challenge_for(verifier) == expected.decode("ascii").rstrip("=")
    assert "=" not in challenge_for(verifier)


def test_the_challenge_is_a_pure_function_of_the_verifier() -> None:
    """Two calls, one answer — the property the token endpoint checks against."""
    assert challenge_for("verifier") == challenge_for("verifier")
    assert challenge_for("verifier") != challenge_for("another")


def test_a_form_action_is_read_back_with_its_entities_resolved() -> None:
    """Keycloak's login form action carries `execution` and `tab_id` query parameters.

    They arrive HTML-escaped, so posting the raw attribute sends `&amp;` as part
    of a parameter value and the authorization server answers with a page rather
    than a redirect. The failure looks like a rejected password.
    """
    html = '<form id="kc-form-login" action="http://keycloak:8081/x?a=1&amp;b=2" method="post">'

    assert form_action(html) == "http://keycloak:8081/x?a=1&b=2"


def test_a_form_action_is_found_whatever_order_the_attributes_come_in() -> None:
    """The attribute order is the template's business, not ours."""
    html = "<form method=\"post\" action='http://keycloak:8081/consent' id='kc-form'>"

    assert form_action(html) == "http://keycloak:8081/consent"


def test_a_document_with_no_form_says_so() -> None:
    """A page with no form is an error page, and it should read as one.

    Returning an empty action would post to the current URL and produce a
    second, less legible failure somewhere further along.
    """
    with pytest.raises(ValueError, match="no form"):
        form_action("<html><body>Invalid username or password.</body></html>")


def test_the_authorization_code_is_read_out_of_the_redirect_location() -> None:
    """The helper never listens on the callback port; it reads the redirect.

    A registered redirect URI has to exist because the authorization server
    validates it, but nothing has to answer at it — which is why the helper
    needs no server, no thread and no port to be free.
    """
    location = "http://localhost:8085/callback?state=abc&code=the-code&session_state=x"

    assert authorization_code(location, expected_state="abc") == "the-code"


def test_a_redirect_carrying_an_error_names_it() -> None:
    """`invalid_scope` and friends arrive here, and arrive as the redirect's own words."""
    location = "http://localhost:8085/callback?error=invalid_scope&error_description=nope"

    with pytest.raises(ValueError, match="invalid_scope"):
        authorization_code(location, expected_state="abc")


def test_a_redirect_carrying_somebody_else_s_state_is_refused() -> None:
    """The value is sent on every request, so it is checked rather than decoration.

    Nothing here is a browser, so this is not the cross-site defence `state`
    exists for. What it does catch is the flow crossing wires — a cached
    redirect, or a session belonging to a different mint — which would
    otherwise show up as a token for the wrong Person.
    """
    location = "http://localhost:8085/callback?state=somebody-else&code=the-code"

    with pytest.raises(ValueError, match="state"):
        authorization_code(location, expected_state="ours")


def test_claims_decode_without_their_padding() -> None:
    """A JSON Web Token's segments are unpadded base64url, and Python's decoder is not.

    Feeding an unpadded segment to `urlsafe_b64decode` raises rather than
    returning a short read, so this is a hard failure the moment a claim set
    happens to land on a length that needs padding.
    """
    payload = {"sub": "priya-raman", "scope": "erp.read erp.write"}
    segment = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).rstrip(b"=")
    token = b".".join([b"header", segment, b"signature"]).decode("ascii")

    assert decode_claims(token) == payload


def test_decoding_does_not_verify_a_signature() -> None:
    """The helper mints; the resource server validates. Stated as a test so it stays true.

    Verifying here would make every wire suite's token pass through a second,
    home-grown validator — and a suite whose fixtures validate their own tokens
    proves the fixture, not the server.
    """
    payload = base64.urlsafe_b64encode(b'{"sub":"x"}').rstrip(b"=").decode("ascii")

    assert decode_claims(f"not-a-header.{payload}.not-a-signature") == {"sub": "x"}


def test_a_token_that_is_not_three_segments_is_refused() -> None:
    """An opaque token would decode to nonsense rather than to an error."""
    with pytest.raises(ValueError, match="segments"):
        decode_claims("opaque-token")


def test_a_scope_claim_is_a_set_and_not_a_string() -> None:
    """RFC 6749 §3.3: space-delimited, case-sensitive strings.

    A set is what the granted-versus-requested comparison needs, and the case
    sensitivity is not ours to choose — `scope_exact_match` asserts the same
    rule at the server.
    """
    assert scope_set("erp.read  erp.write\topenid") == frozenset(
        {"erp.read", "erp.write", "openid"}
    )
    assert scope_set("") == frozenset()
    assert scope_set(None) == frozenset()


def test_scope_comparison_is_case_sensitive() -> None:
    """`ERP.READ` is a different string, and therefore a different scope."""
    assert scope_set("ERP.READ") != scope_set("erp.read")


# ─── The cache, which #36 names as the reason to build this once ───────────


def test_the_key_does_not_depend_on_the_order_the_scopes_were_written_in() -> None:
    """A scope set is a set, so two spellings of one request are one cache entry.

    Keyed by a list, the two calls below would mint twice for the same token —
    which is the *slow* half of what #36 wants building deliberately, and the
    half that would never show up as a failure.
    """
    assert cache_key("mcp-erp", "mcp-conformance", "tomas.weber", ["erp.read", "erp.write"]) == (
        cache_key("mcp-erp", "mcp-conformance", "tomas.weber", ["erp.write", "erp.read"])
    )


def test_everything_that_changes_a_token_changes_the_key() -> None:
    """Realm, client, Person and scope set, each on its own.

    The *duplicated* half of #36's worry is a key that collides: a token minted
    for one Person handed to a row asserting about another passes for the wrong
    reason, which is the failure the whole exhibit is built to make impossible.
    """
    base = cache_key("mcp-erp", "mcp-conformance", "tomas.weber", ["erp.read"])

    assert cache_key("mcp-erp-neighbour", "mcp-conformance", "tomas.weber", ["erp.read"]) != base
    assert cache_key("mcp-erp", "mcp-expiry-probe", "tomas.weber", ["erp.read"]) != base
    assert cache_key("mcp-erp", "mcp-conformance", "ingrid.holm", ["erp.read"]) != base
    assert cache_key("mcp-erp", "mcp-conformance", "tomas.weber", ["erp.decide"]) != base


def test_a_second_mint_for_the_same_request_performs_no_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cached within a run, asserted without a server.

    The flow is stubbed rather than reached, so this says exactly one thing:
    `mint` consults the cache before performing anything. What a real flow
    returns is the wire suites' business.
    """
    performed: list[tuple[str, frozenset[str]]] = []

    def _record(username: str, requested: frozenset[str], **_: object) -> Minted:
        performed.append((username, requested))
        return Minted(
            access_token="a.b.c",
            refresh_token=None,
            claims={"sub": "tomas-weber"},
            requested_scopes=requested,
            granted_scopes=requested,
        )

    monkeypatch.setattr(tokens, "_perform", _record)
    monkeypatch.setattr(tokens, "_CACHE", {})

    first = mint("tomas.weber", ["erp.read", "erp.write"])
    second = mint("tomas.weber", ["erp.write", "erp.read"])

    assert first is second
    assert len(performed) == 1


def test_a_different_scope_set_is_a_different_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """The cache is per Person *and* scope set, which is what the matrix varies."""
    performed: list[tuple[str, frozenset[str]]] = []

    def _record(username: str, requested: frozenset[str], **_: object) -> Minted:
        performed.append((username, requested))
        return Minted(
            access_token="a.b.c",
            refresh_token=None,
            claims={"sub": "tomas-weber"},
            requested_scopes=requested,
            granted_scopes=requested,
        )

    monkeypatch.setattr(tokens, "_perform", _record)
    monkeypatch.setattr(tokens, "_CACHE", {})

    mint("tomas.weber", ["erp.read"])
    mint("tomas.weber", ["erp.decide"])

    assert len(performed) == 2

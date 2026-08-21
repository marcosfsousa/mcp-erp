"""The mask, and the README's derived proof — the transcript machinery's Docker-free half.

`docs/transcripts/` is committed verbatim and re-captured by a run, and the whole
of what makes that comparison mean anything is :func:`transcripts.mask`: it has
to replace **every** volatile field, or a required check flakes on a clock, and
**no** stable one, or the check goes green on a beat that stopped being true.
Neither half is visible from a passing capture — a mask that replaced everything
would compare two identical documents and report nothing wrong forever.

**No Compose, deliberately.** Everything here is a pure function of text, so it
runs in `Lint and types` beside `tests/test_tokens.py` and
`tests/test_conformance_client.py` — the two other Docker-free halves of tooling
whose other half needs a stack. A mask that dropped `sub` is an ordinary Python
defect, which is what that job means.

The fixtures below are written out rather than captured, for the reason the
suite exists: a test that masked a real transcript and asserted the result would
be asserting that the mask agrees with itself.
"""

from __future__ import annotations

import json

import transcripts

A_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsImtpZCIgOiAiazEifQ"
    ".eyJzdWIiOiJwcml5YS1yYW1hbiIsImV4cCI6MX0"
    ".c2lnbmF0dXJlLXdoaWNoLWlzLW5vdC1yZWFs"
)
"""A compact JSON Web Token, shaped like the ones the realm mints."""


def masked(text: str) -> str:
    """The mask applied to one fragment, for a test that asserts on what came out."""
    return transcripts.mask(text)


# ─── The volatile set ─────────────────────────────────────────────────────────


def test_a_bearer_credential_never_survives_the_mask() -> None:
    """The token is the largest volatile thing in the artifact and the first to check."""
    assert A_TOKEN not in masked(f"authorization: Bearer {A_TOKEN}")


def test_every_volatile_claim_the_decision_named_is_replaced() -> None:
    """ADR-0014's own list, asserted as a list rather than one test per member.

    Written out here as literals rather than looped over
    :data:`transcripts.VOLATILE_CLAIMS`, which is the point: a test that iterated
    the module's own set would pass the moment somebody deleted a member from it.
    """
    body = json.dumps(
        {
            "iat": 1787260158,
            "exp": 1787260458,
            "auth_time": 1787260157,
            "jti": "onrtac:7be5cf79",
            "sid": "oGs5pgCuE0hNNzlY3dZR9YgU",
            "kid": "wT8FVjNohnPxEXCW6HF5z",
            "session_state": "oGs5pgCuE0hNNzlY3dZR9YgU",
            "ttlMs": 299224,
        },
        indent=2,
    )

    for line in masked(body).split("\n")[1:-1]:
        assert transcripts.MASKED in line, line


def test_the_session_cookies_are_replaced_in_both_directions() -> None:
    """A cookie the server set, and the same cookie coming back."""
    rendered = masked("set-cookie: AUTH_SESSION_ID=abc; Path=/\ncookie: KC_RESTART=def")

    assert "abc" not in rendered
    assert "def" not in rendered


def test_the_authorization_code_and_its_companions_go_from_a_redirect() -> None:
    """The callback carries a code, a `state` and an `iss`, and only one of them stays."""
    rendered = masked(
        "location: http://127.0.0.1:8085/callback"
        "?code=04c46728-16dd&state=SnIo3JHe&iss=http://keycloak:8081/realms/mcp-erp"
    )

    assert "04c46728-16dd" not in rendered
    assert "SnIo3JHe" not in rendered
    assert "iss=http://keycloak:8081/realms/mcp-erp" in rendered


def test_the_challenge_and_its_verifier_go_from_a_request_target_and_a_form() -> None:
    """Proof Key for Code Exchange, on the authorization request and on the token post."""
    target = masked(
        "GET /realms/mcp-erp/protocol/openid-connect/auth?code_challenge=eM7OQf29 HTTP/1.1"
    )
    form = masked("grant_type=authorization_code&code_verifier=Xy7Q&client_id=https%3A%2F%2Fx")

    assert "eM7OQf29" not in target
    assert "Xy7Q" not in form
    assert "grant_type=authorization_code" in form


def test_keycloaks_own_per_attempt_identifiers_go_without_being_enumerated() -> None:
    """The allow-list is what covers a dependency's internals this file never names.

    `session_code`, `tab_id`, `execution` and `client_data` are Keycloak's, they
    are fresh on every login attempt, and no clause of this exhibit mentions any
    of them. A deny-list would have had to name all four and stay current with a
    dependency; the allow-list catches the fifth one too.
    """
    rendered = masked(
        "POST /realms/mcp-erp/login-actions/authenticate"
        "?session_code=VB9hulj8&execution=e624aefb&tab_id=eUrZj90BI00&client_data=eyJydSI6 HTTP/1.1"
    )

    for volatile in ("VB9hulj8", "e624aefb", "eUrZj90BI00", "eyJydSI6"):
        assert volatile not in rendered, rendered


def test_the_headers_that_move_on_their_own_are_replaced() -> None:
    """A clock, a byte count, and which replica the gateway happened to pick."""
    rendered = masked(
        "date: Thu, 20 Aug 2026 21:14:55 GMT\ncontent-length: 8566\nx-served-by: 172.19.0.5:8080"
    )

    assert "2026" not in rendered
    assert "8566" not in rendered
    assert "172.19.0.5" not in rendered


# ─── The stable set, which the mask must leave alone ──────────────────────────


def test_the_claims_the_exhibit_asserts_on_survive() -> None:
    """`sub`, `aud`, `iss` and the granted scope are what every beat claims."""
    body = json.dumps(
        {
            "iss": "http://keycloak:8081/realms/mcp-erp",
            "aud": "http://localhost:8080/mcp",
            "sub": "priya-raman",
            "scope": "erp.read erp.write",
        },
        indent=2,
    )
    rendered = masked(body)

    assert '"sub": "priya-raman"' in rendered
    assert '"aud": "http://localhost:8080/mcp"' in rendered
    assert '"iss": "http://keycloak:8081/realms/mcp-erp"' in rendered
    assert '"scope": "erp.read erp.write"' in rendered


def test_an_error_code_is_a_json_member_and_a_code_parameter_is_not() -> None:
    """The one collision the structural rules exist to keep apart.

    A JSON-RPC error's `code` is the exhibit's most load-bearing number and an
    authorization response's `code` is the most volatile string in the flow. They
    are the same word, and nothing but the shape they sit in tells them apart.
    """
    body = masked(json.dumps({"error": {"code": -31010, "message": "role_missing"}}, indent=2))
    redirect = masked("location: http://127.0.0.1:8085/callback?code=04c46728")

    assert '"code": -31010' in body
    assert "04c46728" not in redirect


def test_a_refusal_keeps_its_shape() -> None:
    """The four fields a structured refusal carries, which is what ADR-0002 fixed."""
    payload = {
        "reason": "segregation_of_duties",
        "remedy": "different_person",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": True,
    }

    assert json.loads("\n".join(masked(json.dumps(payload, indent=2)).split("\n"))) == payload


def test_the_ordinal_identifiers_and_the_order_they_come_back_in_survive() -> None:
    """Row scoping is a claim about which rows and in what order, so both stay.

    ADR-0003 gave list results a deterministic order deliberately — `ORDER BY
    requisition.id`, *"for the reader and for nothing else"* — and a mask that
    sorted arrays would erase the one artifact that shows it.
    """
    body = json.dumps({"requisitions": [{"id": "req_0003"}, {"id": "req_0001"}]}, indent=2)
    rendered = masked(body)

    assert rendered.index("req_0003") < rendered.index("req_0001")


# ─── Canonicalisation, which is not masking ───────────────────────────────────


def test_a_scope_set_survives_the_mask_and_loses_only_its_order() -> None:
    """RFC 6749 §3.3 says *"the order of values does not matter"*, and this reads it that way.

    Keycloak builds both spellings from an unordered collection, so two boots of
    one realm advertise one set in two orders. The values are what the exhibit
    claims and they are all still here; what is gone is an order the
    specification says is not information.
    """
    one = masked(
        json.dumps({"scope": "erp.decide erp.read", "scopes_supported": ["b", "a"]}, indent=2)
    )
    other = masked(
        json.dumps({"scope": "erp.read erp.decide", "scopes_supported": ["a", "b"]}, indent=2)
    )

    assert one == other
    assert "erp.decide" in one
    assert "erp.read" in one


def test_two_bodies_differing_only_in_member_order_compare_equal() -> None:
    """RFC 8259 defines a JSON object as unordered, and the mask reads it that way."""
    assert masked(json.dumps({"a": 1, "b": 2}, indent=2)) == masked(
        json.dumps({"b": 2, "a": 1}, indent=2)
    )


def test_a_body_that_is_not_json_after_all_is_masked_rather_than_raising() -> None:
    """A malformed artifact should read as a diff, never as a stack trace."""
    assert A_TOKEN not in masked("{\n  not json at all " + A_TOKEN + "\n}")


# ─── The README's one embedded proof ──────────────────────────────────────────


def test_the_proof_is_derived_from_the_capture_and_not_from_a_constant() -> None:
    """Every value in the README's block is read out of the committed transcript.

    ADR-0014 requires the one embedded proof *"included from the captured set,
    never retyped"*, and the derivation is what makes that mechanical: the
    subject and the granted scope come from decoding the token the capture
    presented, which is the same thing the write-up invites a reader to do.
    """
    committed = (transcripts.COMMITTED / f"{transcripts.PROOF}{transcripts.SUFFIX}").read_text(
        encoding="utf-8"
    )
    derived = transcripts.proof(committed)

    assert "priya-raman" in derived
    assert "rafael-costa" in derived
    assert "approve_requisition" in derived


def test_the_readme_carries_the_proof_the_capture_produces() -> None:
    """The committed README and a fresh derivation agree, which is what the check re-runs."""
    committed = (transcripts.COMMITTED / f"{transcripts.PROOF}{transcripts.SUFFIX}").read_text(
        encoding="utf-8"
    )
    readme = transcripts.README.read_text(encoding="utf-8")

    assert transcripts.include(readme, committed) == readme


def test_a_readme_that_lost_its_markers_is_refused() -> None:
    """A README with nowhere to put the proof renders clean and carries a stale one.

    So it is an error rather than a no-op — the one failure mode of a marked
    region that a diff check cannot see, because a file nothing writes to has no
    diff.
    """
    try:
        transcripts.include("# mcp-erp\n\nnothing to include into.\n", "")
    except ValueError:
        return

    raise AssertionError("a README with no proof markers was accepted")

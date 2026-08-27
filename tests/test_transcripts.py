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
from pathlib import Path

import pytest

import transcripts

A_TOKEN = (
    "eyJhbGciOiJSUzI1NiIsImtpZCIgOiAiazEifQ"
    ".eyJzdWIiOiJwcml5YS1yYW1hbiIsImV4cCI6MX0"
    ".c2lnbmF0dXJlLXdoaWNoLWlzLW5vdC1yZWFs"
)
"""A compact JSON Web Token, shaped like the ones the realm mints."""

A_CAPTURE = """A beat

1 of 1
──────────────────────────────────────────────────────────────────────────────

POST /mcp HTTP/1.1
host: localhost:8080

HTTP/1.1 200 OK
date: Thu, 20 Aug 2026 21:34:54 GMT

{
  "sub": "priya-raman"
}
"""
"""One rendered beat, small enough to read and carrying both sides of the mask.

The `date` is what a second run moves on its own and the `sub` is what only a
changed exhibit moves, so a test can tell :func:`transcripts.keep`'s two answers
apart with a one-line edit either way.
"""


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


def test_a_lifetime_counted_down_in_seconds_is_replaced() -> None:
    """The token response's two countdowns, which cross a second boundary between runs.

    `expires_in` and `refresh_expires_in` are `exp` restated as a countdown, the
    same thing `ttlMs` is and masked for the same reason — Keycloak computes
    what is left of a lifetime at the moment it answers, so a capture taken a
    fraction of a second later reads 299 where the committed one reads 300.
    Neither number is a claim these beats make: what the flow proves is that a
    token came back, and its lifetime is the realm's configuration rather than
    anything the wire decided here.

    Found by `Authorization code flow` going red on a diff of exactly `300` →
    `299` and `1800` → `1799`, on a branch that had touched neither the flow nor
    the mask (#112). A drift check that fires on the clock is one a reader learns
    to re-run rather than read.
    """
    body = json.dumps({"expires_in": 300, "refresh_expires_in": 1800}, indent=2)

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


# ─── The shapes the parser has to recognise to reach a value at all ───────────


def test_an_array_body_is_parsed_like_an_object_body() -> None:
    """`json.dumps(indent=2)` puts either at column zero, and a beat may answer with a list.

    Before #108 the parser opened on `{` alone, so an array body was never
    parsed: its volatile members survived and its objects went unsorted, and
    nothing said so until a beat returned one.
    """
    body = json.dumps([{"iat": 1787260158, "sub": "priya-raman"}], indent=2)
    out = masked(body)

    assert "1787260158" not in out
    assert "priya-raman" in out


def test_a_json_document_carried_inside_a_string_is_masked_as_a_document() -> None:
    """A text content block carries its payload as a document inside a string.

    A volatile value there is one no line-oriented rule can see, and the mask
    descends into members rather than lines.
    """
    out = masked(json.dumps({"text": json.dumps({"iat": 1787260158, "id": "req_0001"})}, indent=2))

    assert "1787260158" not in out
    assert "req_0001" in out


def test_a_string_that_is_not_a_document_is_left_exactly_as_it_was() -> None:
    """The descent is for documents; ordinary prose and numeric strings are values."""
    payload = {"amount": "1200.00", "description": "40 ergonomic desk chairs"}

    assert masked(json.dumps(payload, indent=2)) == json.dumps(payload, indent=2, sort_keys=True)


def test_an_elided_body_keeps_its_media_type_whole() -> None:
    """`[text/html;charset=utf-8]` carries no space and no `: `, and is not a form.

    The unqualified form pattern matched it and `_mask_query` rewrote it as a
    query string, so the one elided body in the captured set read
    `[text/html;charset=<masked>` — its closing bracket eaten by a mask that
    thought `charset` was a parameter.
    """
    assert masked("[text/html;charset=utf-8]") == "[text/html;charset=utf-8]"


def test_a_real_form_body_is_still_masked_by_parameter() -> None:
    """The other side of the same rule: keeping the elision must not release a form."""
    out = masked("state=6f2a&code_challenge=xyz&scope=openid")

    assert out == f"state={transcripts.MASKED}&code_challenge={transcripts.MASKED}&scope=openid"


# ─── `keep`, which is the drift check's whole mechanism ───────────────────────


def test_the_same_capture_under_the_mask_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that captured the same beat again leaves the committed bytes alone.

    This is what makes `git status --porcelain -- docs/transcripts` a verdict
    about the exhibit rather than about the minute the job ran in.
    """
    monkeypatch.setattr(transcripts, "COMMITTED", tmp_path)
    path = tmp_path / f"beat{transcripts.SUFFIX}"
    path.write_text(A_CAPTURE, encoding="utf-8")

    assert transcripts.keep("beat", A_CAPTURE.replace("21:34:54", "22:11:07")) is False
    assert path.read_text(encoding="utf-8") == A_CAPTURE


def test_a_substantive_change_rewrites_the_committed_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other direction, and the one a green check would be lying about."""
    monkeypatch.setattr(transcripts, "COMMITTED", tmp_path)
    path = tmp_path / f"beat{transcripts.SUFFIX}"
    path.write_text(A_CAPTURE, encoding="utf-8")
    fresh = A_CAPTURE.replace('"sub": "priya-raman"', '"sub": "tomas-weber"')

    assert transcripts.keep("beat", fresh) is True
    assert path.read_text(encoding="utf-8") == fresh


def test_a_beat_with_no_committed_copy_is_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The missing-capture case, which is why the check is a `git status` and not a `git diff`."""
    monkeypatch.setattr(transcripts, "COMMITTED", tmp_path / "nowhere")

    assert transcripts.keep("beat", A_CAPTURE) is True
    assert (tmp_path / "nowhere" / f"beat{transcripts.SUFFIX}").exists()


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


# ─── The short form, and the card it carries ──────────────────────────────────


ALLOWED_DIGITS = ("OAuth 2.0", "2026-07-28")
"""The only literals carrying a digit that the short form's prose may contain.

Two, each with something that goes red if it drifted, which is what #142 asks a
reviewer to be able to name. `2026-07-28` is the protocol revision, asserted
against the server's own answer at `tests/wire/test_endpoints.py`; `OAuth 2.0`
names a specification family rather than a quantity, and there is nothing in it
to drift. **Everything else with a digit in it is a count, a figure or an
identifier**, and those are included from the capture or absent — the rule the
card exists to satisfy.
"""


def test_the_card_is_derived_from_the_capture_and_not_from_a_constant() -> None:
    """Every cell in the short form's table is read out of the committed transcript."""
    committed = (transcripts.COMMITTED / f"{transcripts.PROOF}{transcripts.SUFFIX}").read_text(
        encoding="utf-8"
    )
    derived = transcripts.card(committed)

    assert "priya-raman" in derived
    assert "rafael-costa" in derived
    assert "erp.decide" in derived


def test_the_card_shows_the_tool_absent_rather_than_refused() -> None:
    """The one row that carries the exhibit's claim, and the only asymmetric cell.

    `approve_requisition` is in Priya Raman's listing and not in Rafael Costa's,
    because the authorization server declined `erp.decide` and never issued it.
    A card that ticked both columns would be a table nobody needs; this is the
    difference the short form exists to show without a sentence.
    """
    committed = (transcripts.COMMITTED / f"{transcripts.PROOF}{transcripts.SUFFIX}").read_text(
        encoding="utf-8"
    )

    row = next(
        line
        for line in transcripts.card(committed).split("\n")
        if line.startswith("| `approve_requisition`")
    )

    assert transcripts.LISTED in row
    assert transcripts.ABSENT in row


def test_the_readme_carries_the_card_the_capture_produces() -> None:
    """The committed card and a fresh derivation agree, which is what the check re-runs.

    The round trip one test above covers both regions at once, since
    :func:`transcripts.include` rewrites them together. This asserts the card's
    own bytes are in the file, so a README that kept its markers and lost its
    table fails here rather than passing an equality that both sides satisfy.
    """
    committed = (transcripts.COMMITTED / f"{transcripts.PROOF}{transcripts.SUFFIX}").read_text(
        encoding="utf-8"
    )
    readme = transcripts.README.read_text(encoding="utf-8")

    assert transcripts.card(committed) in readme


def test_a_readme_that_lost_its_card_markers_is_refused() -> None:
    """A README carrying the proof's markers and not the card's is still an error.

    The second region has the first's failure mode and no diff to show for it,
    so it gets the first's refusal.
    """
    lost = f"# mcp-erp\n\n{transcripts.PROOF_OPENS}\n{transcripts.PROOF_CLOSES}\n"

    try:
        transcripts.include(lost, "")
    except ValueError as refusal:
        assert transcripts.CARD_OPENS in str(refusal)
        return

    raise AssertionError("a README with no card markers was accepted")


def test_the_short_form_stays_under_the_ceiling_it_declares() -> None:
    """The soft ceiling, read out of the README and asserted against the README.

    **Red here is not an instruction to delete a sentence.** It says: look at
    whether the short form has started restating the page below it, which is the
    failure ADR-0014 §*What the README carries* names and the reason the bound is
    soft. The number lives in the marker rather than here, on the shape
    `matrix.yaml` uses for its own `meta.ceiling` — a ceiling a test carries is a
    ceiling the artifact does not declare.

    The card is cut out before counting. It is rendered from the capture, so a
    tool joining the listing must never be what puts a hand-written surface over
    its bound.
    """
    form = transcripts.short_form(transcripts.README.read_text(encoding="utf-8"))

    assert form.words <= form.ceiling, f"{form.words} words against a ceiling of {form.ceiling}"


SPELLED_COUNTS = (
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
)
"""Counts the digit rule below would miss, because a spelled count is still a count.

Written out rather than derived, and **`one` is deliberately not here**: in this
repository's register it is a determiner far more often than a quantity — *the
one proof*, *one route onward* — so forbidding it would fight the prose instead
of the drift. Everything from `two` up is a count in practice, and a count in
the short form belongs in the card.
"""


def test_the_short_form_spells_out_no_count_either() -> None:
    """The hole the digit rule leaves, closed to the extent a check can close it.

    *five tools* and *two tokens* carry exactly the drift `5` and `2` would and
    pass a search for digits. What no check can reach is a count phrased around
    the number — that stays a reviewer's job, and it is why the ceiling above is
    asserted at all: a short form that grows enough to start counting things is
    a short form that has started restating the page below it.
    """
    form = transcripts.short_form(transcripts.README.read_text(encoding="utf-8"))
    words = {word.strip(".,;:*`()[]").lower() for word in form.prose.split()}

    assert not words.intersection(SPELLED_COUNTS), sorted(words.intersection(SPELLED_COUNTS))


def test_the_short_form_carries_no_number_a_check_does_not_hold() -> None:
    """Every count, figure or identifier in the short form is included or absent.

    #142's first constraint, made mechanical: the prose is hand-written and
    nothing renders it, so the only enforceable rule is that it carries no digit
    at all outside :data:`ALLOWED_DIGITS`. A reviewer can name, for each one,
    what would go red if it drifted. Anything countable belongs in the card,
    where the capture answers for it.
    """
    form = transcripts.short_form(transcripts.README.read_text(encoding="utf-8"))

    prose = form.prose
    for allowed in ALLOWED_DIGITS:
        prose = prose.replace(allowed, "")

    assert not any(character.isdigit() for character in prose), prose


def test_the_short_form_is_the_first_thing_under_the_title() -> None:
    """Reachable without a click, and above every heading on the page.

    #142's measurement was that 402 of 785 words came before the one proof, so
    the property that matters is positional and this is where it is held. A
    short form that drifted below `## Run it` would satisfy every other test
    here and none of the ticket.
    """
    readme = transcripts.README.read_text(encoding="utf-8")

    opens = transcripts.SHORT_OPENS.search(readme)
    assert opens is not None

    assert opens.start() < readme.index("\n## ")
    assert opens.start() < readme.index(transcripts.PROOF_OPENS)

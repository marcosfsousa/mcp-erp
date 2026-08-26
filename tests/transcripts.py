"""The captured transcripts: what the wire said, rendered, masked and committed.

ADR-0014 §*What a machine can keep true, a machine keeps true* splits the
walkthrough by what each part is. The tables render from their sources, the
connective prose is hand-written, and the wire exchanges are **captured
artifacts**: a run writes them, a committed copy is what the write-up includes,
and a check refuses a diff. This module is that third thing — the `Seed renders
clean` pattern extended to a further rendering.

**Committed verbatim, masked only inside the check.** The artifact is exactly
what came off the wire, real bearer token and all. :func:`keep` re-renders,
applies :func:`mask` to *both* sides, and rewrites the file only when the masked
forms differ — so the committed bytes change when something substantive changed
and never because a token was minted again. That makes the drift check the same
`git status --porcelain` the seed's four renderings already get, rather than a
second kind of verdict.

**The committed bearer token is not a secret**, on the terms `seed.yaml` already
uses for the password: a throwaway local realm whose signing keys are regenerated
on every boot, a five-minute expiry, and a Person whose password is committed as
`not-a-secret-demo-password`. It is unverifiable by anyone, anywhere, five
minutes after capture — and ADR-0014 prefers a real expired token to a
placeholder, because a reader can decode it and check `aud` against what the
write-up claims. `docs/transcripts/README.md` carries that line for a reader who
arrives at the directory rather than at this file.

**Nothing here is prose about the exhibit.** A transcript carries its beat's
title, numbered exchanges and the wire; the narrative that reads them is ticket
(iii)'s.


WHO WRITES WHICH BEAT, AND WHY IT IS TWO WRITERS
------------------------------------------------
Three of the six beats need a token a human consented to at a login screen, and
Keycloak remembers a grant per Person and client — so a second flow in a second
process would post one form where the first posted two, and the transcript would
record the difference. The three earned beats are therefore written by
`tests/conformance/test_authorization_code_flow.py`, from the flows that suite
already performs; the three minted beats are written by `tests/capture.py`,
which needs no consent screen and no ordering.

Both writers write into one directory that one check reads, which is what keeps
*two writers* an implementation detail rather than two artifacts. This module is
what they share, and it is **deliberately the half that touches no fixture and no
domain**: `tests/conformance_client.py` imports it to snapshot what a flow saw,
and that client is independent of layer 3 on purpose. What needs the seeded rows
lives in `tests/capture.py`.


AN EXCHANGE IS A SNAPSHOT, NOT THE LIVE OBJECTS
-----------------------------------------------
Found by execution. `httpx2` reuses one `Request` object across an authenticated
retry — the auth flow sets `Authorization` on the request the `401` came back
from — so an exchange holding the live object renders a credential the server
never saw on that request. :func:`snapshot` copies what a message was at the
moment it happened, and the rendering is a statement about the wire again.


THE ELISION, STATED RATHER THAN DISCOVERED
-------------------------------------------
JSON and form-encoded bodies are rendered in full. Anything else — which here is
only Keycloak's own login and consent pages — is rendered as its media type and
nothing more. Those pages are tens of kilobytes of markup carrying a fresh
`session_code` per attempt, and ADR-0014 already assigns them to a different
artifact class: *the consent screen ships as a screenshot, beside the captured
transcript that proves what it claims.* What the transcript owes those two steps
is the envelope, and the envelope is what it renders.

**JSON bodies are re-serialised for reading and for the mask.** Every key, value
and ordering is the wire's; what changes is that the wire's single line becomes
one key per line, which is what lets :func:`mask` name a field structurally
instead of by a regular expression over a whole document. `content-length` is
masked, so nothing in the artifact claims a byte count the rendering no longer
has.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import httpx2

from tokens import decode_claims

REPO: Final = Path(__file__).resolve().parents[1]
"""The checkout, from this file's own location — `tests/fixtures.py`'s resolution."""

COMMITTED: Final = REPO / "docs" / "transcripts"
"""Where the captured beats are committed.

Under `docs/` rather than beside a suite, because the write-up is what reads
them and no test asserts against their contents. `.gitattributes` pins them
`-text` for the reason the seed's renderings are pinned: these bytes are
compared, and a checkout that converted line endings would fail the drift check
on a machine rather than on a change.
"""

SUFFIX: Final = ".txt"
"""Plain text, so GitHub renders the wire rather than interpreting it."""

README: Final = REPO / "README.md"
"""The root README, whose one embedded proof is derived from the captured set."""

WALKTHROUGH: Final = REPO / "docs" / "walkthrough.md"
"""The write-up, which ADR-0014 settles is also the walkthrough and is one artifact.

The README carries a **derivation** between markers, rewritten by a generator.
This document carries **excerpts**, chosen by whoever writes it and checked
where they sit — see :func:`quotations`. Two mechanisms because the two
documents want different things: the README's one proof is the same proof
forever and nobody picks it, while a narrative quotes the four lines that make
its paragraph land and no generator can know which four.
"""

QUOTED: Final = re.compile(r"<!-- excerpt: ([^\s>]+) -->")
"""What names the transcript a fenced block was taken out of.

One marker per block, on its own line, immediately above the opening fence.
The capture is a beat name from :data:`BEATS` or the literal
:data:`HAND_WRITTEN`. A marker rather than a path because the beat name is
already this module's stable identifier and a path would be a second spelling
of it.
"""

HAND_WRITTEN: Final = "hand-written"
"""The one thing a fenced block may name instead of a beat.

A walkthrough contains blocks that are not quotations — a command the reader
types, a fragment of configuration, a decoded claim set. They have to be
writable, and they must not be writable **by omission**: an unmarked block is a
failure, so the escape is a marker a reviewer sees in the diff rather than an
absence nobody notices. That asymmetry is the whole mechanism.
"""

FENCE: Final = "```"
"""What opens and closes a Markdown code block, at column zero and nowhere else.

Indented fences are not read, and so would slip the check. Nothing in this
document needs one: a quotation inside a list item is a quotation that wants to
be a paragraph.
"""

FLOW_COMPLETES: Final = "the-flow-completes"
SCOPE_WITHOUT_ROLE: Final = "scope-without-role"
TOOLS_LIST_FOR_TWO_TOKENS: Final = "tools-list-for-two-tokens"
UNDER_SCOPED: Final = "under-scoped-tool-absent"
SEGREGATION_OF_DUTIES: Final = "segregation-of-duties"
ROW_SCOPED_NOT_FOUND: Final = "row-scoped-not-found"

PROOF: Final = TOOLS_LIST_FOR_TWO_TOKENS
"""The beat the README embeds, and the only one it does.

ADR-0014: *"the exhibit's shortest complete thought — same server, two tokens,
different tools — and the only beat that lands both gaps in a single artifact."*
"""

PROOF_OPENS: Final = "<!-- proof: derived from docs/transcripts/tools-list-for-two-tokens.txt -->"
PROOF_CLOSES: Final = "<!-- /proof -->"
"""What :func:`include` rewrites between, so the README's prose stays hand-written.

A marked region rather than a rendered README, because ADR-0014 keeps the
connective prose free and only the proof included: *"included from the captured
set, never retyped."* Everything outside the two markers is a person's.
"""

EARNED: Final = (FLOW_COMPLETES, SCOPE_WITHOUT_ROLE, TOOLS_LIST_FOR_TWO_TOKENS)
"""The beats whose token was consented to at a login screen, written by the flow suite."""

MINTED: Final = (UNDER_SCOPED, SEGREGATION_OF_DUTIES, ROW_SCOPED_NOT_FOUND)
"""The beats `tests/capture.py` writes, which need no consent screen and no ordering."""

BEATS: Final = EARNED + MINTED
"""Every beat ADR-0014 and #92 name, in the order the walkthrough walks them."""

TITLES: Final = {
    FLOW_COMPLETES: "The flow completes",
    SCOPE_WITHOUT_ROLE: "Scope without role: a protocol error where a 403 would lie",
    TOOLS_LIST_FOR_TWO_TOKENS: "tools/list, answered for two different tokens",
    UNDER_SCOPED: "Under-scoped: the tool is absent from the listing",
    SEGREGATION_OF_DUTIES: "Segregation of duties: a domain rejection, not an authorization error",
    ROW_SCOPED_NOT_FOUND: "Row scoping: another partition's row and no row at all, byte for byte",
}
"""One line per beat, and the whole of what a transcript says in its own words."""

JSON_MEDIA_TYPE: Final = "application/json"
"""What is rendered as a document rather than as a media type. A `+json` suffix joins it."""

FORM_MEDIA_TYPE: Final = "application/x-www-form-urlencoded"
"""The other body shape a flow produces — the two form posts and the token request."""

EVENT_STREAM_MEDIA_TYPE: Final = "text/event-stream"
"""What a body that must never be read declares. This server opens none; see `TIMEOUT`."""

MASKED: Final = "<masked>"
"""What a volatile value becomes on both sides of the comparison."""

MASKED_TOKEN: Final = "<jwt>"
"""What a bearer token, an identity token or a refresh token becomes."""

VOLATILE_HEADERS: Final = frozenset(
    {
        # Wall-clock, per response.
        "date",
        # A function of the token's length, and the rendering re-serialises
        # bodies anyway — so a kept value would describe bytes that are not here.
        "content-length",
        # The session cookies ADR-0014 names, in both directions.
        "cookie",
        "set-cookie",
        # Which replica answered, as the gateway reports it. It alternates by
        # design — `gateway/nginx.conf` exists to make that observable — so it is
        # volatile in the ordinary sense and nothing in these beats claims it.
        "x-served-by",
    }
)
"""Header values replaced wholesale. `location:` is masked by parameter instead."""

VOLATILE_CLAIMS: Final = frozenset(
    {
        # ADR-0014's named set, as they are spelled in a JSON document.
        "iat",
        "exp",
        "auth_time",
        "jti",
        "sid",
        "kid",
        # Keycloak's spelling of `sid` on a token response: the same per-login
        # identifier under a name of its own.
        "session_state",
        # The tool listing's freshness hint, which the server derives from the
        # presented token's remaining lifetime. It is `exp` restated as a
        # countdown in milliseconds, so it is the same clock ADR-0014 already
        # names and it moves by the millisecond between two runs. What
        # `Server posture` asserts about it is that it is bounded by the token,
        # and that is not a claim any of these beats makes.
        "ttlMs",
        # The token response's two countdowns, which are `ttlMs`'s argument one
        # entity along: Keycloak computes what is left of each lifetime at the
        # moment it answers, so a capture taken a fraction of a second later
        # reads 299 where the committed one reads 300. The lifetimes themselves
        # are the realm's configuration and no beat here claims either.
        "expires_in",
        "refresh_expires_in",
        # Tokens are masked by :data:`_JWT` wherever they appear; naming the keys
        # as well costs nothing and keeps the set readable as the set ADR-0014
        # wrote down.
        "access_token",
        "id_token",
        "refresh_token",
    }
)
"""JSON keys whose value is replaced. A deny-list, because JSON is where the stable claims live.

`sub`, `aud`, `iss`, the granted scopes, the ordinal identifiers, list ordering,
error codes and refusal shapes are all JSON and all stable — so an allow-list
here would have to enumerate the exhibit's whole vocabulary and would mask a
domain payload the day a field was added.
"""

STABLE_PARAMETERS: Final = frozenset(
    {
        "client_id",
        "redirect_uri",
        "response_type",
        "response_mode",
        "scope",
        "code_challenge_method",
        "resource",
        "grant_type",
        "username",
        "password",
        "credentialId",
        "accept",
        "iss",
        "error",
        "error_description",
    }
)
"""Query-string and form parameters kept verbatim. An allow-list, and the direction matters.

Everything else in a URL or a form body is masked, which is what covers the
authorization code, `state`, the code challenge and its verifier **and**
Keycloak's own per-attempt identifiers — `session_code`, `tab_id`, `execution`,
`client_data` — without this file having to enumerate a dependency's internals
and stay current with them. The failure mode of a deny-list here is a volatile
value that flakes a required check; the failure mode of this list is a stable
value that reads as `<masked>` until somebody adds it, which is visible on sight.
"""

UNORDERED_SCOPE_SETS: Final = frozenset({"scope", "scopes_supported"})
"""Members whose value is a scope set, which the specification defines as unordered.

**Sorting these is canonicalisation, not masking, and the difference is the whole
justification.** ADR-0014 and #92 both put the granted scopes on the *stable*
side, so their values must survive the mask — and they do: what is dropped is an
order RFC 6749 §3.3 already says carries no meaning, *"the order of values does
not matter"*. Keycloak iterates an unordered collection when it builds both of
these, so two boots of the same realm advertise the same set in different orders;
without this, a required check would go red on a difference the specification
says is not one.

The same reading is everywhere else in this repository already —
`tokens.scope_set` returns a `frozenset`, and every suite that compares scopes
compares sets.
"""

SEPARATOR: Final = "─" * 78
"""What divides one exchange from the next, under its ordinal."""

_JWT: Final = re.compile(r"eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
"""A compact JSON Web Token, anywhere in the text — a header value or a JSON value."""

_REQUEST_LINE: Final = re.compile(r"^([A-Z]+) (\S+) (HTTP/[\d.]+)$")
"""`POST /mcp?x=1 HTTP/1.1` — the only line whose second field is a URL target."""

_HEADER_LINE: Final = re.compile(r"^([a-z0-9-]+): (.*)$")
"""A rendered header. Names are lower-cased and sorted by :func:`snapshot`."""

_FORM_BODY: Final = re.compile(r"^[^\s:\[]+=\S*(&[^\s:\[]+=\S*)*$")
"""A form-encoded body line, which carries no spaces and no `: ` — unlike the other two.

**No parameter name may open with `[`, which is what keeps an elision out.**
:func:`_body` renders a body it does not read as its bracketed media type, and
`[text/html;charset=utf-8]` carries no space and no `: ` either — so the
unqualified pattern matched it, `_mask_query` rewrote it as a query string, and
the artifact's one elided body read `[text/html;charset=<masked>`, its closing
bracket eaten by a mask that thought it was a value. `application/json` and
`application/x-www-form-urlencoded` are the media types rendered in full, so no
elision this can now miss is a form.
"""

_OPENS: Final = {"{": "}", "[": "]"}
"""The body openers :func:`_body` produces at column zero, each with its closer.

An array as well as an object, because `json.dumps(indent=2)` puts either at
column zero and a beat is free to answer with a list. Before #108 only `{` was
read, so an array body was never parsed: its members went unsorted, its volatile
values unreplaced, and only the line-level token rule reached it.
"""


@dataclass(frozen=True, slots=True)
class Exchange:
    """One request and the response it got, as they were at the moment they happened.

    Flat and copied rather than a pair of `httpx2` objects, for the reason the
    module docstring gives: the auth flow mutates a request after its first
    response has already come back, and a record that held the live object would
    render a credential that request never carried.

    Attributes:
        method: The HTTP method.
        target: The request target — path and query, as it went on the wire.
        sent: The request's headers, lower-cased and sorted.
        request_body: What the request carried, empty when it carried nothing.
        status: The response's status code.
        reason: Its reason phrase.
        received: The response's headers, lower-cased and sorted.
        response_body: What the response carried, empty when nothing read it.
    """

    method: str
    target: str
    sent: tuple[tuple[str, str], ...]
    request_body: bytes
    status: int
    reason: str
    received: tuple[tuple[str, str], ...]
    response_body: bytes

    @property
    def answered(self) -> bool:
        """Whether the server answered rather than refusing or redirecting."""
        return httpx2.codes.OK <= self.status < httpx2.codes.MULTIPLE_CHOICES


def snapshot(response: httpx2.Response) -> Exchange:
    """Copy one exchange out of the objects that made it.

    Takes the request from the response rather than as a second argument: every
    caller has a response, a response carries the request that produced it, and
    a second parameter is a second thing that can be handed the wrong pair.

    A body nothing has read — which here would only ever be an event stream this
    server does not open — is recorded as empty rather than read. Reading one at
    snapshot time would buffer until the server closed it, which is a hang rather
    than a failure.
    """
    request = response.request

    return Exchange(
        method=request.method,
        target=request.url.raw_path.decode("ascii"),
        sent=_headers(request.headers),
        request_body=_read(request),
        status=response.status_code,
        reason=response.reason_phrase,
        received=_headers(response.headers),
        response_body=_read(response),
    )


def calls(exchange: Exchange, method: str, name: str | None = None) -> bool:
    """Whether this exchange is one named JSON-RPC call, read from the request's own body.

    From the body rather than from the `Mcp-Method` and `Mcp-Name` headers,
    although both are present on every modern request. The headers are a routing
    contract the server checks *against* the body — `auth_bypass_via_method_
    header_mismatch` is the row about what happens when they disagree — so a
    selector keyed on them would be reading the caller's claim rather than the
    call.

    Args:
        exchange: One recorded request and its response.
        method: The JSON-RPC method, `tools/list` or `tools/call`.
        name: The tool, for a `tools/call`, or ``None`` to match any.

    Returns:
        Whether the request is that call.
    """
    try:
        body = json.loads(exchange.request_body)
    except ValueError:
        return False

    if not isinstance(body, dict) or body.get("method") != method:
        return False

    return name is None or body.get("params", {}).get("name") == name


def render(name: str, exchanges: Sequence[Exchange]) -> str:
    """One beat, as the text that gets committed.

    Args:
        name: The beat, which is also the file's own name.
        exchanges: What the run performed, in the order it performed them.

    Returns:
        The transcript, ending in a newline.

    Raises:
        KeyError: The beat has no title, which means it is not one of :data:`BEATS`.
    """
    lines = [TITLES[name], ""]

    for ordinal, exchange in enumerate(exchanges, start=1):
        lines.append(f"{ordinal} of {len(exchanges)}")
        lines.append(SEPARATOR)
        lines.append("")
        lines.extend(_exchange(exchange))
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def keep(name: str, fresh: str) -> bool:
    """Commit a fresh capture, and only when the mask says something substantive changed.

    This is the whole of the diff check's mechanism. A run always re-captures; a
    run that captured the same beat again writes nothing, so `git status
    --porcelain -- docs/transcripts` is red exactly when the wire said something
    different — never because a token was minted again or a clock moved.

    Args:
        name: The beat.
        fresh: What this run captured, verbatim.

    Returns:
        Whether the committed copy was rewritten.
    """
    path = COMMITTED / f"{name}{SUFFIX}"

    if path.exists() and mask(path.read_text(encoding="utf-8")) == mask(fresh):
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fresh.encode("utf-8"))

    return True


def mask(text: str) -> str:
    """Replace every volatile field and nothing stable, on whichever side is being compared.

    Applied to the committed copy and to the fresh capture alike, which is what
    makes the comparison a statement about the exhibit rather than about the
    minute it ran in. The rules are structural rather than lexical, and that is
    what keeps them from colliding: a JSON-RPC error's ``"code": -31010`` is a
    JSON member and stays, while an authorization response's ``code=…`` is a URL
    parameter and goes.

    **A JSON body is parsed rather than read line by line**, so that a key is a
    key and an array is an array. Two things follow, and both are the
    specification's readings rather than this file's: object members are
    re-serialised **sorted**, because RFC 8259 defines an object as unordered,
    and the members :data:`UNORDERED_SCOPE_SETS` names are sorted inside their
    own value, because RFC 6749 §3.3 says a scope set's order does not matter.
    Neither drops anything a beat claims. Everything else keeps the wire's order,
    including the result lists ADR-0003 gave a deterministic one.

    **A body is an object or an array, and a member may be a document itself.**
    Both follow from the same reading and #108 added both: `json.dumps(indent=2)`
    puts either container at column zero, and an MCP text content block carries
    its payload as a JSON document inside a string — where a rule that reads
    lines cannot see it.

    Args:
        text: A rendered transcript, from either side.

    Returns:
        The same transcript with the volatile fields replaced.
    """
    masked: list[str] = []
    held: list[str] | None = None
    closes = ""

    for line in text.split("\n"):
        if held is not None:
            held.append(line)
            if line == closes:
                masked.extend(_mask_document(held))
                held = None
            continue

        if line in _OPENS:
            held = [line]
            closes = _OPENS[line]
            continue

        request = _REQUEST_LINE.match(line)
        if request is not None:
            method, target, version = request.groups()
            masked.append(f"{method} {_mask_url(target)} {version}")
            continue

        header = _HEADER_LINE.match(line)
        if header is not None:
            masked.append(_mask_header(*header.groups()))
            continue

        if _FORM_BODY.match(line):
            masked.append(_mask_query(line))
            continue

        masked.append(_JWT.sub(MASKED_TOKEN, line))

    if held is not None:
        masked.extend(_mask_document(held))

    return "\n".join(masked)


def include(readme: str, transcript: str) -> str:
    """Put the README's one embedded proof between its markers, derived from the capture.

    ADR-0014 allows the README exactly one proof and requires it *"included from
    the captured set, never retyped"*. The captured set is the wire, and the wire
    here is two `tools/list` responses carrying every tool's full input and
    output schema — some forty kilobytes, which is not a five-minute read. So the
    README carries a **derivation** rather than an excerpt: every value in it is
    read out of `docs/transcripts/tools-list-for-two-tokens.txt` by :func:`proof`,
    and nothing in it is typed by hand.

    Args:
        readme: The README as committed.
        transcript: The committed capture the proof is derived from.

    Returns:
        The README with the marked region replaced.

    Raises:
        ValueError: The markers are missing or out of order. A README that lost
            them would otherwise render clean while carrying a proof nothing
            keeps current, which is the drift this whole mechanism is against.
    """
    opens = readme.find(PROOF_OPENS)
    closes = readme.find(PROOF_CLOSES)

    if opens < 0 or closes < opens:
        raise ValueError(f"README.md carries no {PROOF_OPENS} … {PROOF_CLOSES} region")

    body = "\n".join(["", "```", proof(transcript), "```", ""])

    return readme[: opens + len(PROOF_OPENS)] + body + readme[closes:]


def proof(transcript: str) -> str:
    """The README's embedded proof, read out of the committed capture.

    Four things per token, and every one of them is in the file: the request
    line, the `Mcp-Method` header, the credential as it was presented, and the
    names the listing came back with. The subject and the granted scope are
    decoded out of the token itself rather than restated — which is the same
    thing the write-up invites a reader to do, done by the machine that writes
    the README.

    Args:
        transcript: `docs/transcripts/tools-list-for-two-tokens.txt`, as committed.

    Returns:
        The block that goes between the markers, without its fence.

    Raises:
        ValueError: The capture carries no bearer token, or a different number of
            them than it carries listings — which means it is not the beat this
            derives from, and a proof derived from it would be a guess.
    """
    bearers = _bearers(transcript)
    listings = _listings(transcript)

    if not bearers or len(bearers) != len(listings):
        raise ValueError(
            f"{PROOF}{SUFFIX} carries {len(bearers)} bearer tokens and "
            f"{len(listings)} tool listings, and a proof needs one of each per caller"
        )

    lines: list[str] = []
    for token, names in zip(bearers, listings, strict=True):
        claims = decode_claims(token)
        lines.append("POST /mcp        Mcp-Method: tools/list")
        # Head **and** tail. Two tokens minted by one boot share a header and a
        # key identifier, so a leading slice of each would print the same
        # characters twice on a block whose whole claim is that these are two
        # different credentials. The signatures differ; the tail is where that
        # is visible.
        lines.append(f"authorization:   Bearer {token[:28]}…{token[-12:]}")
        lines.append(f"                 sub    {claims.get('sub')}")
        lines.append(f"                 scope  {claims.get('scope')}")
        lines.append("")
        lines.extend(f"    -> {name}" for name in names)
        lines.append("")

    return "\n".join(lines).rstrip("\n")


@dataclass(frozen=True, slots=True)
class Quotation:
    """One fenced block in a prose document, and what it says it was taken from.

    Attributes:
        beat: The marker's capture — a name in :data:`BEATS`, :data:`HAND_WRITTEN`,
            or `None` where the block carried no marker at all.
        body: The block's lines, without either fence.
        line: The opening fence's 1-based line number, so a failure names a place.
    """

    beat: str | None
    body: tuple[str, ...]
    line: int


def quotations(document: str) -> tuple[Quotation, ...]:
    """Every fenced block in a prose document, with the marker above it.

    The marker is the nearest preceding non-blank line, and it has to be the
    whole of that line. Reading only the line above means a block cannot inherit
    a marker from a paragraph three back that a later edit was written around.

    Args:
        document: The write-up, as committed.

    Returns:
        One :class:`Quotation` per fenced block, in the order they appear.
    """
    lines = document.splitlines()
    found: list[Quotation] = []

    index = 0
    while index < len(lines):
        if not lines[index].startswith(FENCE):
            index += 1
            continue

        opened = index
        index += 1
        body: list[str] = []
        while index < len(lines) and not lines[index].startswith(FENCE):
            body.append(lines[index])
            index += 1
        index += 1

        found.append(Quotation(beat=_marker(lines, opened), body=tuple(body), line=opened + 1))

    return tuple(found)


def misquoted(quotation: Quotation, transcript: str) -> bool:
    """Whether a block claims a transcript that does not contain it.

    **Contiguous, and in order.** The block's lines have to appear in the
    transcript as one unbroken run. An excerpt that elided its middle would be
    a claim about two places at once, and the honest form of that is two blocks.

    Trailing whitespace is stripped from both sides before comparing, and
    nothing else is. Editors strip it from Markdown and the capture does not, so
    a difference there is an artifact of where the bytes were typed rather than
    of what the wire said. Every other difference is drift and fails.

    Args:
        quotation: The block, which must name a beat rather than be hand-written.
        transcript: The committed capture the marker names.

    Returns:
        Whether the run is absent.
    """
    wanted = [line.rstrip() for line in quotation.body]
    held = [line.rstrip() for line in transcript.splitlines()]

    if not wanted:
        return True

    return not any(
        held[start : start + len(wanted)] == wanted for start in range(len(held) - len(wanted) + 1)
    )


def _marker(lines: list[str], fence: int) -> str | None:
    """The `<!-- excerpt: … -->` above a fence, or `None` if the line above is not one."""
    above = fence - 1
    while above >= 0 and not lines[above].strip():
        above -= 1

    if above < 0:
        return None

    found = QUOTED.fullmatch(lines[above].strip())

    return found.group(1) if found else None


def _exchange(exchange: Exchange) -> list[str]:
    """One request and one response, in the order they happened."""
    lines = [f"{exchange.method} {exchange.target} HTTP/1.1"]
    lines.extend(f"{name}: {value}" for name, value in exchange.sent)
    lines.extend(_body(exchange.sent, exchange.request_body))
    lines.append("")
    lines.append(f"HTTP/1.1 {exchange.status} {exchange.reason}")
    lines.extend(f"{name}: {value}" for name, value in exchange.received)
    lines.extend(_body(exchange.received, exchange.response_body))

    return lines


def _headers(headers: httpx2.Headers) -> tuple[tuple[str, str], ...]:
    """Every header, lower-cased and sorted.

    Sorted because HTTP field order carries no meaning and a run that emitted
    them in a different order would be a diff with nothing behind it. Nothing is
    dropped: what is volatile is masked inside the check, and the committed copy
    is what came off the wire.
    """
    return tuple(sorted((name.lower(), value) for name, value in headers.items()))


def _read(message: httpx2.Request | httpx2.Response) -> bytes:
    """What a message carried, or empty when nothing has read it."""
    try:
        return bytes(message.content)
    except (httpx2.RequestNotRead, httpx2.ResponseNotRead):
        return b""


def _body(headers: tuple[tuple[str, str], ...], content: bytes) -> list[str]:
    """A body, rendered whole when it is JSON or a form and as its media type otherwise."""
    if not content:
        return []

    declared = dict(headers).get("content-type", "")
    media = declared.split(";", 1)[0].strip().lower()

    if media == JSON_MEDIA_TYPE or media.endswith("+json"):
        try:
            document: Any = json.loads(content)
        except ValueError:
            pass
        else:
            return ["", json.dumps(document, indent=2, ensure_ascii=False)]

    if media == FORM_MEDIA_TYPE:
        return ["", content.decode("utf-8")]

    return ["", f"[{declared or 'no content type'}]"]


def _mask_header(name: str, value: str) -> str:
    """One header, by name: replaced wholesale, masked by parameter, or left alone."""
    if name in VOLATILE_HEADERS:
        return f"{name}: {MASKED}"
    if name == "location":
        return f"{name}: {_mask_url(value)}"

    return f"{name}: {_JWT.sub(MASKED_TOKEN, value)}"


def _mask_document(lines: list[str]) -> list[str]:
    """One JSON body, masked as a document and re-serialised in a canonical order.

    Falls back to the token rule alone on anything that does not parse — a body
    that is not JSON after all, or a transcript truncated mid-object — because a
    mask that raised would turn a malformed artifact into a stack trace instead
    of a diff.
    """
    try:
        document = json.loads("\n".join(lines))
    except ValueError:
        return [_JWT.sub(MASKED_TOKEN, line) for line in lines]

    rendered = json.dumps(_masked(document), indent=2, ensure_ascii=False, sort_keys=True)

    return [_JWT.sub(MASKED_TOKEN, line) for line in rendered.split("\n")]


def _masked(value: object) -> object:
    """One JSON value with its volatile members replaced and its scope sets canonicalised."""
    if isinstance(value, dict):
        return {
            name: MASKED if name in VOLATILE_CLAIMS else _canonical(name, _masked(member))
            for name, member in value.items()
        }
    if isinstance(value, list):
        return [_masked(member) for member in value]
    if isinstance(value, str):
        return _embedded(value)

    return value


def _embedded(value: str) -> str:
    """A string carrying a JSON document, masked as one — every other string untouched.

    An MCP text content block carries its payload as a document *inside* a
    string, so a volatile value there is one the structural rules cannot see:
    :func:`_masked` descends into members, and this is a member whose text is
    another document. Re-serialised the way :func:`_mask_document` re-serialises
    a body — sorted, indented — because it is the same reading of the same
    specification applied one level down.

    Latent when #108 named it: every such block in the six committed captures
    carries fixture data only. It becomes a required-check flake the first time a
    beat answers with a volatile value inside one, and the masked diff would then
    report it as substantive.
    """
    if not value.lstrip().startswith(("{", "[")):
        return value

    try:
        document = json.loads(value)
    except ValueError:
        return value

    if not isinstance(document, dict | list):
        return value

    return json.dumps(_masked(document), indent=2, ensure_ascii=False, sort_keys=True)


def _canonical(name: str, value: object) -> object:
    """A scope set in a fixed order, and everything else untouched.

    Both spellings, because the two documents that carry one disagree about the
    shape: a token response's `scope` is a space-delimited string and an
    authorization server's `scopes_supported` is an array.
    """
    if name not in UNORDERED_SCOPE_SETS:
        return value
    if isinstance(value, str):
        return " ".join(sorted(value.split()))
    if isinstance(value, list) and all(isinstance(member, str) for member in value):
        return sorted(value)

    return value


def _mask_url(target: str) -> str:
    """A URL or a request target, with its query masked and everything else kept.

    The path is stable and load-bearing — `/mcp`, the metadata document's
    path-inserted address, the realm's endpoints — so only the query moves.
    """
    parts = urlsplit(target)
    if not parts.query:
        return target

    return urlunsplit(parts._replace(query=_mask_query(parts.query)))


def _mask_query(query: str) -> str:
    """Query-string or form parameters, keeping only what :data:`STABLE_PARAMETERS` names.

    Rebuilt from the parsed pairs rather than substituted in place, so a value
    that happened to contain an ampersand cannot leave half of itself behind.
    Percent-encoding is deliberately not restored: a masked value has no encoding
    to preserve, and a kept one is shown as the server will have read it.
    """
    pairs = parse_qsl(query, keep_blank_values=True)
    if not pairs:
        return query

    return "&".join(
        f"{name}={value if name in STABLE_PARAMETERS else MASKED}" for name, value in pairs
    )


def _bearers(transcript: str) -> list[str]:
    """Every credential the capture presented, in the order it presented them."""
    return [
        line.split("Bearer ", 1)[1].strip()
        for line in transcript.split("\n")
        if line.startswith("authorization: Bearer ")
    ]


def _listings(transcript: str) -> list[list[str]]:
    """The tool names each `tools/list` in the capture answered with, sorted.

    Sorted rather than in wire order, because the two listings are shown side by
    side and the claim is *which tools* — the listing's own ordering is asserted
    by nothing, and `tests/matrix/` reads it as a set.
    """
    return [
        sorted(str(tool["name"]) for tool in document["result"]["tools"])
        for document in _documents(transcript)
        if isinstance(document, dict) and "tools" in document.get("result", {})
    ]


def _documents(transcript: str) -> list[Any]:
    """Every JSON body in a transcript, parsed.

    Found by :data:`_OPENS` at column zero, which is what :func:`_body` produces
    and nothing else in the rendering does: a header carries a `: `, a form body
    is one line with no braces at all, and an elision is bracketed on one line.
    So this reads the artifact rather than re-asking the server, which is the
    whole point of a committed capture.

    The same opener set as :func:`mask`, and for the same reason. Before #108
    both read `{` alone, and an array body would have been invisible to the mask
    and to the README's derived proof at once — two failures a reader would have
    had to connect, from one cause.
    """
    documents: list[Any] = []
    held: list[str] | None = None
    closes = ""

    for line in transcript.split("\n"):
        if held is None:
            if line in _OPENS:
                held = [line]
                closes = _OPENS[line]
            continue

        held.append(line)
        if line == closes:
            documents.append(json.loads("\n".join(held)))
            held = None

    return documents

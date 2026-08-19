"""ADR-0009's three seam assertions, and the question they were written to falsify.

Scenarios: `legacy_unauthenticated_refused`, `legacy_underscoped_same_denial_class`
and `legacy_discover_exemption_unavailable` — all three `basis: seam`, all three
`floor: true`, all three sourced to ADR-0009 §Three assertions, and they exist to
falsify rather than to sample.

    removal (1): Apply token verification inside the modern request path instead
                 of ahead of era routing.
    removal (2): Resolve scope from the era-specific handler rather than the
                 shared policy function.
    removal (3): Key the exemption on a default method name when `Mcp-Method` is
                 absent.

**What was open, and what the first run settled.** ADR-0008 chose a substrate on
which both eras are always on and neither can be disabled, which put the legacy
era into a state the map never named: *not built, and reachable*. What no
documentation settled is **where token verification sits relative to era
routing** — middleware wrapping the whole application, in which case both legs
are covered, or inside the modern request path, in which case the legacy leg is
unauthenticated and ADR-0009 is wrong. ADR-0009 recorded the second case as a
condition rather than a risk: *"if it sits behind, this reopens"*, with refusing
the era at the edge becoming the live option again.

**All three pass, and ADR-0009's condition is discharged rather than met.** The
gate chain is route-level middleware ahead of the protocol package's ASGI
application (ADR-0013, executed at #32), so era routing happens strictly below
it. `test_token_verification_precedes_era_routing` is what makes that an
observation rather than a reading of the wiring.

**These rows keep running, and their value is no longer where it was.** The
first run was the design input; every run after it is a regression check on a
leg nothing else in this repository exercises. They stay in the floor of 11 for
that reason.
"""

import httpx2
from mcp.shared.inbound import MCP_METHOD_HEADER
from mcp_types.jsonrpc import METHOD_NOT_FOUND
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_MODERN_VERSION

import rpc
from tokens import mint

TOOL = "list_requisitions"
"""The one tool that exists, and the only thing either leg can be asked to do."""

DISCOVER = "server/discover"
"""The one method answered without a token — on the leg that can prove it asked."""

READER = "tomas.weber"
"""One Person throughout, so that no assertion here can turn on who is calling.

Every difference these rows report has to be the era and nothing else, and a
second name in the module would be a second thing a red result could mean.
"""


def test_legacy_unauthenticated_refused() -> None:
    """A legacy-era call carrying no token is refused, exactly as a modern one is.

    Scenario: `legacy_unauthenticated_refused`.

    The ticket's criterion is *authorized identically*, so the assertion is
    equality against the modern twin rather than a `401` on its own: a leg that
    refused with a different status, or with a challenge naming a different
    document, would be answering a different question from the one the modern
    leg answers and this pair is what says so.
    """
    legacy = rpc.legacy_post("tools/call", {"name": TOOL, "arguments": {}})
    modern = rpc.post("tools/call", {"name": TOOL, "arguments": {}})

    assert legacy.status_code == modern.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(legacy) == rpc.challenge(modern)
    assert rpc.challenge(legacy)["resource_metadata"] == rpc.METADATA_URL
    # No `error` parameter on either leg: RFC 6750 draws the line at whether a
    # credential was presented, never at which era presented none.
    assert "error" not in rpc.challenge(legacy)


def test_the_legacy_leg_answers_when_the_token_is_there() -> None:
    """The control the refusal above means nothing without: this leg is live.

    Scenario: `legacy_unauthenticated_refused`.

    A `401` proves the leg is authorized only if the same request succeeds with
    a token. Without this, the identical refusal would be produced by a leg that
    was never reachable at all — which is the state the map assumed and ADR-0008
    took away — and the row would be asserting the absence of a surface rather
    than the guarding of one.
    """
    minted = mint(READER, ["erp.read"])

    result = rpc.result(
        rpc.legacy_post("tools/call", {"name": TOOL, "arguments": {}}, token=minted.access_token)
    )

    assert result["isError"] is False, result
    # Row scoping ran too, which is the point beneath the point: the legacy leg
    # reaches the same handler and the same policy chain, not a parallel one.
    assert result["structuredContent"]["requisitions"]


def test_token_verification_precedes_era_routing() -> None:
    """The open question, made observable: the gate runs, then the era is chosen.

    Scenario: `legacy_unauthenticated_refused` — this is the recorded removal's
    falsifier, and the reason ADR-0009 front-loaded these three rows rather than
    deferring them behind the matrix.

    ``initialize`` is the instrument, because it is the one method that exists on
    exactly one leg. The `2026-07-28` revision removed connection initialization
    entirely, so:

    - with a token and no version header it is **answered**, which can only have
      happened after era routing sent it to the handshake-era transport;
    - with the modern envelope it is `-32601`, which is what proves the answer
      above came from the legacy leg rather than from a method both eras share;
    - with no token it is a `401`, which the legacy transport has no concept of
      and could not have produced.

    Read together: a request that demonstrably reaches an era-routed handler is
    refused before it gets there. Had verification sat inside the modern request
    path, the third call would have returned the first call's answer to a caller
    holding nothing.
    """
    minted = mint(READER, ["erp.read"])
    handshake = {
        "protocolVersion": HANDSHAKE_PROTOCOL_VERSIONS[-1],
        "capabilities": {},
        "clientInfo": rpc.CLIENT_INFO,
    }

    answered = rpc.result(rpc.legacy_post("initialize", handshake, token=minted.access_token))
    assert answered["protocolVersion"] in HANDSHAKE_PROTOCOL_VERSIONS

    on_the_modern_leg = rpc.post("initialize", handshake, token=minted.access_token)
    assert rpc.error(on_the_modern_leg)["code"] == METHOD_NOT_FOUND

    refused = rpc.legacy_post("initialize", handshake)
    assert refused.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(refused)["resource_metadata"] == rpc.METADATA_URL


def test_legacy_underscoped_same_denial_class() -> None:
    """An under-scoped legacy call and its modern twin refuse in the same shape.

    Scenario: `legacy_underscoped_same_denial_class`.

    **The assertion is equality, not a pair of matching literals.** A denial
    class is what ADR-0002 keyed on *what would fix this for the caller*, and the
    two legs share one remedy — re-authorize for a wider scope — so they have to
    share one shape. Comparing the responses to each other rather than each to a
    written-down `403` means a change to the shape moves both sides at once and
    this row stays a statement about the two legs agreeing.

    One Person, two scope sets: `erp.write` is a real granted scope that simply
    is not the one this tool declares, which makes the refusal about the scope
    rather than about a token that fails for some other reason first.
    """
    minted = mint(READER, ["erp.write"])
    assert "erp.read" not in minted.granted_scopes, minted.granted_scopes

    legacy = rpc.legacy_post(
        "tools/call", {"name": TOOL, "arguments": {}}, token=minted.access_token
    )
    modern = rpc.call_tool(TOOL, token=minted.access_token)

    assert legacy.status_code == modern.status_code == httpx2.codes.FORBIDDEN
    assert rpc.challenge(legacy) == rpc.challenge(modern)
    assert rpc.challenge(legacy)["error"] == "insufficient_scope"


def test_legacy_discover_exemption_unavailable() -> None:
    """The one unauthenticated method is unreachable from the legacy leg.

    Scenario: `legacy_discover_exemption_unavailable`.

    The modern call is not decoration: it is what makes this a statement about
    the *leg* rather than about the exemption having been removed. Same method,
    same absent token, and the answers differ — which is only interesting
    because one of them is a `200`.
    """
    on_the_modern_leg = rpc.post(DISCOVER, {})
    assert rpc.result(on_the_modern_leg)["supportedVersions"] == [LATEST_MODERN_VERSION]

    refused = rpc.legacy_post(DISCOVER, {})
    assert refused.status_code == httpx2.codes.UNAUTHORIZED


def test_the_exemption_follows_from_absence_rather_than_from_a_default() -> None:
    """Sending ``Mcp-Method`` alone buys nothing, which is what the row asserts *why* about.

    Scenario: `legacy_discover_exemption_unavailable`.

    ADR-0009 separates this row from the first two on exactly this: the claim is
    about **why** the refusal happens. Gate 3 branches on the method gate 2
    *proved*, and gate 2 proves nothing on a leg carrying no version header — so
    the exemption is unavailable by construction rather than by a rule someone
    could relax.

    A request sending ``Mcp-Method: server/discover`` and no version header is
    what tells the two apart. It is a legacy request by era routing's own rule,
    it names the exempt method, and it is still refused. Under the recorded
    removal — keying the exemption on a defaulted method name — this is the call
    that would walk through, and nothing else in the suite would notice.
    """
    refused = rpc.legacy_post(DISCOVER, {}, headers={MCP_METHOD_HEADER: DISCOVER})

    assert refused.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(refused)["resource_metadata"] == rpc.METADATA_URL


def test_the_spoofed_header_buys_nothing_on_a_tool_call_either() -> None:
    """The same spoof against the method it would actually be worth something on.

    Scenario: `legacy_discover_exemption_unavailable`.

    ADR-0006 ordered the gate chain so that granting the exemption on a
    caller-controlled header before proving header and body agree is
    structurally impossible, and `auth_bypass_via_method_header_mismatch` is
    that ordering's falsifier on the modern leg. This is the legacy leg's
    version of the same attack, and it is a different route to the same door:
    there, the header disagrees with the body and gate 2 catches it; here, gate 2
    has nothing to compare and so proves nothing — and gate 3 needs a proof,
    not a header.
    """
    refused = rpc.legacy_post(
        "tools/call",
        {"name": TOOL, "arguments": {}},
        headers={MCP_METHOD_HEADER: DISCOVER},
    )

    assert refused.status_code == httpx2.codes.UNAUTHORIZED

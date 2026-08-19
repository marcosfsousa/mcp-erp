"""ADR-0009's three seam assertions, and the question they were written to falsify.

Scenarios: `legacy_unauthenticated_refused`, `legacy_underscoped_same_denial_class`
and `legacy_discover_exemption_unavailable` — all three `basis: seam`, all three
`floor: true`, all three sourced to ADR-0009 §Three assertions, and they exist to
falsify rather than to sample.

    removal (1): Apply token verification inside the modern request path instead
                 of ahead of era routing.
    removal (2): Run the scope gate on the modern leg alone, skipping it when no
                 `MCP-Protocol-Version` header is present.
    removal (3): Key the exemption on a default method name when `Mcp-Method` is
                 absent.

The open question underneath them — *where token verification sits relative to
era routing* — is ADR-0009's, and so is the answer: **all three pass, and the
condition is discharged**. ADR-0009 §The first run, and what it settled carries
the argument and is not repeated here. What is worth saying at this altitude is
what each test is *for*, because two of the seven are controls rather than
assertions and they read like padding otherwise.
"""

from collections.abc import Iterator

import httpx2
import pytest
from mcp.shared.inbound import MCP_METHOD_HEADER
from mcp_types.jsonrpc import METHOD_NOT_FOUND
from mcp_types.version import HANDSHAKE_PROTOCOL_VERSIONS, LATEST_MODERN_VERSION

import rpc
import seeded_requisitions
from tokens import mint

TOOL = "list_requisitions"

DISCOVER = "server/discover"

PERSON = "tomas.weber"
"""One Person throughout, so that no assertion here can turn on who is calling.

Every difference these rows report has to be the era and nothing else, and a
second name in the module would be a second thing a red result could mean. Named
for the Person rather than for what his token carries, because one test mints him
a write-only token and a constant called `READER` would then assert the opposite
of its own value — roles are not held on a Person, and neither are scopes.
"""


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Load the rows this module's control needs, rather than inheriting them.

    `test_list_partition_scoped.py` loads the same rows in the same way, and the
    duplication is deliberate: `load()` wipes and reloads, nothing here writes,
    and the two modules must each start from a known set. Depending on the other
    module's fixture would make this one pass or fail on **collection order** —
    which it did, silently, until a cold database made the control red.

    In the test module rather than in a `conftest.py` for the reason
    `test_list_partition_scoped.py` states: `tests/conftest.py` already exists
    and the types job runs over `tests/`, so a second file of that name is a
    duplicate module to mypy.

    #43 deletes `seeded_requisitions.py` and generates the rows from
    `matrix.yaml` instead, and this fixture goes with it.
    """
    seeded_requisitions.load()
    yield


def test_legacy_unauthenticated_refused() -> None:
    """A legacy-era call carrying no token is refused, exactly as a modern one is.

    Scenario: `legacy_unauthenticated_refused`.

    The ticket's criterion is *authorized identically*, so the assertion is
    equality against the modern twin rather than a `401` on its own: a leg that
    refused with a different status, or with a challenge naming a different
    document, would be answering a different question from the one the modern leg
    answers and this pair is what says so.
    """
    legacy = rpc.legacy_post("tools/call", {"name": TOOL, "arguments": {}})
    modern = rpc.post("tools/call", {"name": TOOL, "arguments": {}})
    challenge = rpc.challenge(legacy)

    assert legacy.status_code == modern.status_code == httpx2.codes.UNAUTHORIZED
    assert challenge == rpc.challenge(modern)
    assert challenge["resource_metadata"] == rpc.METADATA_URL
    # No `error` parameter on either leg: RFC 6750 draws the line at whether a
    # credential was presented, never at which era presented none.
    assert "error" not in challenge


def test_the_legacy_leg_is_authorized_identically_when_it_is_permitted() -> None:
    """The other half of *identically*: the granted case, not only the refusals.

    Scenario: `legacy_unauthenticated_refused`.

    Two things at once, and both are needed. **The leg is live**, which is what
    the `401` above is worth something against — an identical refusal from a leg
    that was never reachable would assert the absence of a surface rather than
    the guarding of one, and that is the state ADR-0008 took away.

    **And the rows are the same rows.** Set equality against the modern twin
    rather than a non-empty check, because row scoping is the part of the chain
    that runs *after* everything these rows assert on: a legacy leg reaching a
    parallel handler that skipped it would return more rows, pass a non-empty
    check, and leave the ADR claiming a scoping it had not proved.
    """
    minted = mint(PERSON, ["erp.read"])

    legacy = rpc.result(
        rpc.legacy_post("tools/call", {"name": TOOL, "arguments": {}}, token=minted.access_token)
    )
    modern = rpc.result(rpc.call_tool(TOOL, token=minted.access_token))

    assert legacy["isError"] is False, legacy
    assert _identifiers(legacy) == _identifiers(modern)
    # Against the seed rather than only against each other: two legs agreeing on
    # the wrong set would satisfy the line above and nothing else here.
    assert _identifiers(legacy) == seeded_requisitions.identifiers_in("CC-4100")


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
    minted = mint(PERSON, ["erp.read"])
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

    **The assertion is equality, not a pair of matching literals.** A denial class
    is what ADR-0002 keyed on *what would fix this for the caller*, and the two
    legs share one remedy — re-authorize for a wider scope — so they have to share
    one shape. Comparing the responses to each other rather than each to a
    written-down `403` means a change to the shape moves both sides at once and
    this row stays a statement about the two legs agreeing.

    One Person, two scope sets: `erp.write` is a real granted scope that simply is
    not the one this tool declares, which makes the refusal about the scope rather
    than about a token that fails for some other reason first.
    """
    minted = mint(PERSON, ["erp.write"])
    assert "erp.read" not in minted.granted_scopes, minted.granted_scopes

    legacy = rpc.legacy_post(
        "tools/call", {"name": TOOL, "arguments": {}}, token=minted.access_token
    )
    modern = rpc.call_tool(TOOL, token=minted.access_token)
    challenge = rpc.challenge(legacy)

    assert legacy.status_code == modern.status_code == httpx2.codes.FORBIDDEN
    assert challenge == rpc.challenge(modern)
    assert challenge["error"] == "insufficient_scope"


def test_legacy_discover_exemption_unavailable() -> None:
    """The one unauthenticated method is unreachable from the legacy leg.

    Scenario: `legacy_discover_exemption_unavailable`.

    The modern call is not decoration: it is what makes this a statement about the
    *leg* rather than about the exemption having been removed. Same method, same
    absent token, and the answers differ — which is only interesting because one
    of them is a `200`.
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
    what tells the two apart. It is a legacy request by era routing's own rule, it
    names the exempt method, and it is still refused. Under the recorded removal —
    keying the exemption on a defaulted method name — this is the call that would
    walk through, and nothing else in the suite would notice.
    """
    refused = rpc.legacy_post(DISCOVER, {}, headers={MCP_METHOD_HEADER: DISCOVER})

    assert refused.status_code == httpx2.codes.UNAUTHORIZED
    assert rpc.challenge(refused)["resource_metadata"] == rpc.METADATA_URL


def test_the_spoofed_header_buys_no_tool_call_either() -> None:
    """What removal 3 actually costs: the same spoof against a tool rather than a probe.

    Scenario: `legacy_discover_exemption_unavailable` — still this row, and not a
    claim on `auth_bypass_via_method_header_mismatch`. That row is the modern
    leg's, where the header disagrees with the body and gate 2 catches the
    disagreement; here gate 2 has nothing to compare and catches nothing, and what
    refuses the call is gate 3 needing a *proof* rather than a header. Different
    gate, different mechanism, same door.

    It sits with the third row because it is what makes the third row's removal
    worth recording. `server/discover` behind a `401` is a worse probe; this same
    request under that removal **executes a tool for a caller holding nothing**,
    which is the difference between an inconvenience and an authentication bypass.
    """
    refused = rpc.legacy_post(
        "tools/call",
        {"name": TOOL, "arguments": {}},
        headers={MCP_METHOD_HEADER: DISCOVER},
    )

    assert refused.status_code == httpx2.codes.UNAUTHORIZED


def _identifiers(result: dict[str, object]) -> set[str]:
    """The requisition identifiers in a tool result, as a set.

    Set rather than list: row scoping is a question of which rows come back, and
    no entity carries a timestamp, so there is no order the authorization model
    has an opinion about.
    """
    structured = result["structuredContent"]
    assert isinstance(structured, dict), result
    return {row["id"] for row in structured["requisitions"]}

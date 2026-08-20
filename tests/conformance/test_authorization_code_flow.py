"""The run map constraint `#1` calls primary: a real flow, completing, against a running server.

Every other suite in this repository is handed a token. This one earns one — the
authorization server dereferences a document GitHub Pages serves, a person logs
in, a person consents, and the code is redeemed — and then speaks the protocol
through the package's own `Client` rather than through a hand-built envelope.
`tests/rpc.py` exists to assert *what the server said*; this asserts *that the
protocol works*, and the two are different questions.

**The preflight is first on purpose.** ADR-0008's second mechanism, and the
reason the `Authorization code flow` job can block: without it, GitHub Pages
being unreachable and this server rejecting a valid flow present identically as
*the flow failed*. In continuous integration it runs as its own step before
`docker compose up`; here it runs first so a reader gets the same naming.
"""

from __future__ import annotations

import asyncio
import traceback
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from mcp.shared.exceptions import MCPError
from mcp_types import CallToolResult, ListToolsResult

import fixtures
import rpc
import transcripts
from conformance_client import CLIENT_ID, CONSENT, LOGIN, Bearer, Flow, connect, preflight
from tokens import ISSUER
from tokens import mint as minted_by_the_helper

CAPABILITY_SCOPES = frozenset({"erp.read", "erp.write", "erp.decide"})
"""Every scope this server publishes, which is what an unauthenticated challenge names.

The client does not choose it: the protocol package reads the `scope` parameter
off the `WWW-Authenticate` challenge, so what gets requested is derived from this
server's own metadata. Written out here because the assertion is that the
derivation reaches all three — a suite that recomputed it from the same source
would agree with itself.
"""

WITH_A_DECIDING_ROLE = "priya.raman"
"""Holds `approver`, so the authorization server grants every scope requested."""

WITHOUT_A_DECIDING_ROLE = "rafael.costa"
"""Holds `invoice_clerk` and neither deciding role, so `erp.decide` is declined.

ADR-0012 manufactured this situation deliberately — a role scope mapping listing
`approver` and `unlimited_approver`, and one Person entitled to neither — and
left what the authorization server *reports* about it as an open verification
item. This is the Person that item is answered with.
"""

TOOL = "list_requisitions"
"""One call, chosen because every Person in the Cast can make it and see rows."""

DECIDING_TOOL = "approve_requisition"
"""The tool ADR-0014 calls the exhibit's centrepiece, reached with an earned token.

Every other proof of `-31010` in this repository uses a token we minted for
ourselves — `tests/matrix/`'s `approve_refused_when_the_scope_carries_no_role`
and `tests/wire/`'s. This one uses a token a human consented to at a login
screen, and the duplication is the point: it is the same refusal, arrived at
through the only path a reader cannot call circular.
"""

ROLE_MISSING = -31010
"""The protocol error code a `403` would lie about, per ADR-0002."""


@pytest.fixture(scope="module", autouse=True)
def loaded_fixtures() -> Iterator[None]:
    """Wipe and reload the fixtures once before this module.

    Nothing here writes, and until #92 nothing here read the rows either — the
    call this leg makes was chosen because *every Person in the Cast can make it
    and see rows*, and how many was never the point.

    **It became the point when the call started being captured.** The flow's
    transcript ends on `list_requisitions`, so its last exchange is a picture of
    the database at the moment it ran — and the suites that run before this one
    in a whole-tree collection write to it. Found by reading a committed capture
    against a second run of it: one showed `req_0001` as `submitted` and the
    other as `approved`, because `tests/attack_suite` had approved it in the same
    process. The load is what makes the beat a fact about the seed rather than
    about collection order.
    """
    fixtures.load()
    yield


def audiences(claim: object) -> set[str]:
    """The `aud` claim as a set, since it is one value or a list of them.

    The same shape `tests/attack_suite/test_token_validation.py` reads it in, and
    copied rather than shared for the reason that file's own helper is private to
    it: two suites asking one question of one claim is not yet a third module.
    """
    if isinstance(claim, str):
        return {claim}
    if isinstance(claim, list):
        return {str(value) for value in claim}
    return set()


@dataclass(frozen=True, slots=True)
class Performed:
    """One completed flow, and what the wire answered afterwards.

    Attributes:
        flow: The auth object, which is also the record of what it did.
        listed: The `tools/list` result, filtered by the granted scope.
        called: One `tools/call`, which is the proof that a token earned this way
            reaches past the gate chain rather than merely existing.
    """

    flow: Flow
    listed: ListToolsResult
    called: CallToolResult


_PERFORMED: dict[str, Performed] = {}
"""One flow per Person, cached within the run and no longer.

The same reason `tokens.py` caches: this is three requests, two form posts and a
consent screen, and re-running it per assertion would make the suite's wall time
a function of how many things it checks. Not cached across runs, because
Keycloak re-imports from an empty database on every boot — and because a
remembered grant would let the consent assertion below start passing on history.
"""


def performed(username: str) -> Performed:
    """Earn a token for one Person through the hosted document, and use it once."""
    if username not in _PERFORMED:
        _PERFORMED[username] = asyncio.run(_perform(username))

    return _PERFORMED[username]


async def _perform(username: str) -> Performed:
    """The whole conversation: earn, connect, list, call.

    Written as one coroutine rather than four, because the flow happens *inside*
    the first request the client makes — the package performs it on the `401` —
    so there is no point at which the token exists and the client does not.
    """
    flow = Flow(username)

    async with connect(flow) as client:
        return Performed(flow, await client.list_tools(), await client.call_tool(TOOL, {}))


_REFUSED: dict[str, MCPError] = {}
"""The deciding tool's answer to one Person's earned token, cached like the flow itself."""


def refused_by_the_deciding_tool(username: str) -> MCPError:
    """Present this Person's **earned** token to `approve_requisition`, once.

    ADR-0014 §*The gating job performs the centrepiece* extends this leg by
    exactly one call, and the extension is a second `connect` on the *same*
    :class:`Flow` rather than a second flow. The wallet already holds the token,
    so the package attaches it and no `401` arrives — which is what keeps
    :attr:`Flow.posted` at one login and one consent, and keeps this a statement
    about the token rather than about earning a second one.
    """
    if username not in _REFUSED:
        _REFUSED[username] = asyncio.run(_refuse(performed(username).flow))

    return _REFUSED[username]


async def _refuse(flow: Flow) -> MCPError:
    """Call the deciding tool with a flow's own token and return what came back.

    **The identifier is the one no row carries, and that is the assertion rather
    than a shortcut.** ADR-0006 fixes the gate order, and the role step is ahead
    of anything that reads a row — so a caller holding `erp.decide` and no
    deciding role is refused before the resource is looked at. Naming a real
    fixture would make this leg depend on a seeded database that the
    `Authorization code flow` job does not load; naming the identifier no row
    carries makes it depend on the order instead, which is the property.

    Raises:
        AssertionError: The call was answered rather than refused. A tool that
            let this token through is the whole failure this leg exists to
            catch, and it has no exception of its own to raise.
    """
    async with connect(flow) as client:
        try:
            answered = await client.call_tool(
                DECIDING_TOOL, {"ids": [fixtures.ABSENT_IDENTIFIER], "decision": "approve"}
            )
        except MCPError as refusal:
            return refusal

    raise AssertionError(
        f"{DECIDING_TOOL} answered an earned token with no deciding role: {answered}"
    )


def test_the_published_document_answers_as_committed() -> None:
    """Name an external cause before anything of ours has run.

    A `200` whose body hashes to the committed file. Anything else — Pages down,
    egress blocked, a document that changed underneath its identifier — fails
    here, in one step, with the URL in the message, instead of surfacing four
    requests later as a flow that did not complete.
    """
    assert preflight()


def test_the_flow_completes_and_the_call_lands() -> None:
    """The whole of what ship line `#8`'s sixth item asks for, in one assertion.

    A client that is registered nowhere in the realm authenticates a person,
    earns a token, and reaches a tool through the gate chain. The tool answering
    at all is what makes this a run rather than a token: `tools/call` is behind
    every gate ADR-0006 orders, and a token that only decoded would prove none of
    them.
    """
    run = performed(WITH_A_DECIDING_ROLE)

    assert run.called.is_error is False, run.called
    assert run.called.structured_content is not None
    assert {tool.name for tool in run.listed.tools} >= {TOOL}


def test_both_forms_are_posted() -> None:
    """Login **and** consent, in that order.

    ADR-0012 called the consent post *"a build step not to discover on the day"*,
    and this is the assertion that keeps it from becoming one again. It cannot be
    inferred from the token: Keycloak remembers a grant, so a run against a warm
    realm would reach a token having posted one form. It is only because the
    database is empty at every boot that first-consent is the deterministic path,
    and only because the record is kept that the difference is visible.

    **The precondition is the boot, and it is stated rather than weakened.**
    ADR-0012 already rests on it — *"Keycloak state is fresh on every boot, so
    continuous integration always takes the first-consent path"* — so continuous
    integration is always cold. A reader who has already run the flow for this
    Person against this container has a warm one, and the message below says so
    rather than leaving a red check to be read as a broken consent post.
    """
    posted = performed(WITH_A_DECIDING_ROLE).flow.posted

    assert posted == [LOGIN, CONSENT], (
        f"posted {posted}: Keycloak remembers a grant per Person and client, so this "
        f"assertion is about the first flow of a boot. Run `docker compose down` and "
        f"up again if {WITH_A_DECIDING_ROLE} has already consented against this container."
    )


def test_the_request_is_derived_from_what_this_server_publishes() -> None:
    """The client asks for what the resource server said it needed, not for a list of its own.

    The `401` challenge carries `scope`, the package reads it, and the
    authorization request carries it back. That chain is what makes the
    requested-versus-granted comparison below a statement about the
    authorization server rather than about a constant this client happened to
    hold.
    """
    assert performed(WITH_A_DECIDING_ROLE).flow.requested == CAPABILITY_SCOPES


def test_the_token_is_bound_to_this_resource_and_to_the_hosted_identity() -> None:
    """Four claims, and the third is the one only this client can produce.

    `azp` naming the document URL is the proof that the Client Identity Metadata
    Document was actually used: no client with that identifier is registered in
    the realm, so the authorization server can only have got the name by
    dereferencing it.
    """
    claims = performed(WITH_A_DECIDING_ROLE).flow.claims

    assert claims["iss"] == ISSUER
    assert claims["sub"] == "priya-raman"
    assert claims["azp"] == CLIENT_ID
    # The audience the realm's mapper stamps, which is the string this server is
    # configured with. A token minted for anyone else is refused at gate 4.
    # Read as a set against `rpc.RESOURCE`, the way the attack suite reads it:
    # `aud` is one value or a list of them, and the resource identifier moves
    # with the deployment while this file must not.
    assert rpc.RESOURCE in audiences(claims.get("aud"))


def test_a_declined_scope_is_reported_in_the_scope_response_parameter() -> None:
    """**RFC 6749 §3.3, observed rather than assumed** — and it is honoured.

    > If the issued access token scope is different from the one requested by the
    > client, the authorization server MUST include the "scope" response
    > parameter to inform the client of the actual scope granted.

    ADR-0012 left this open deliberately, because Keycloak omits an unpermitted
    scope **silently** and whether it then says so was not something anyone here
    had measured. It says so: the parameter is present and equals the scope the
    token carries, so a client learns it was narrowed without decoding anything.

    The outcome is therefore a conformance proof and **not** a normative register
    row. A row would record a gap; there is none to record.
    """
    flow = performed(WITHOUT_A_DECIDING_ROLE).flow

    assert flow.narrowed == {"erp.decide"}
    assert flow.reported is not None, "no scope response parameter on a narrowed grant"
    assert set(flow.reported.split()) == flow.granted == CAPABILITY_SCOPES - {"erp.decide"}


def test_a_declined_scope_takes_its_tool_out_of_the_listing() -> None:
    """The narrowing is not cosmetic: it reaches the wire as absence.

    ADR-0002's fourth refusal. `approve_requisition` declares `decide`, the token
    does not carry `erp.decide`, so the tool is not in the listing at all — which
    is the same filter `tests/wire/` asserts on a minted token, reached here
    through a scope the authorization server itself decided.
    """
    run = performed(WITHOUT_A_DECIDING_ROLE)

    assert "approve_requisition" not in {tool.name for tool in run.listed.tools}
    assert run.called.is_error is False, run.called


def test_minting_and_earning_differ_by_exactly_one_object() -> None:
    """ADR-0008's packaging claim, as an assertion rather than a diagram.

    The same :func:`connect`, the same server, the same protocol conversation —
    with a token `tests/tokens.py` minted through a pre-registered client in
    place of one this client earned through a hosted document. If the two legs
    had drifted into a pair that only works with itself, they would not agree
    here.

    The scope sets are made equal on purpose. This is about the seam being one
    object wide, and a listing that differed because the two tokens carried
    different capabilities would be answering a question about scope instead.
    """
    earned = performed(WITH_A_DECIDING_ROLE)
    presented = minted_by_the_helper(WITH_A_DECIDING_ROLE, sorted(CAPABILITY_SCOPES))

    async def through_a_minted_token() -> ListToolsResult:
        async with connect(Bearer(presented.access_token)) as client:
            return await client.list_tools()

    listed = asyncio.run(through_a_minted_token())

    assert {tool.name for tool in listed.tools} == {tool.name for tool in earned.listed.tools}


def test_a_password_the_realm_does_not_hold_fails_at_the_login_form() -> None:
    """The negative that keeps the positive honest.

    Every assertion above rests on a form post that could have been silently
    skipped — a rejected password re-renders the login form with a `200`, which
    is the same status the consent screen arrives with. Without this, a client
    that posted nothing and read the re-rendered form as consent would still
    fail, but three steps later and with a message about a missing code.

    The failure is searched for across the whole exception tree rather than on
    the exception itself. The flow runs inside the transport's task group, so
    what reaches a caller is a `BaseExceptionGroup` wrapping the refusal, and
    matching on the group's own message would assert nothing.
    """

    async def attempt() -> None:
        async with connect(Flow("nobody.here")) as client:
            await client.list_tools()

    with pytest.raises(BaseException) as refused:
        asyncio.run(attempt())

    reported = "".join(traceback.format_exception(refused.value))
    assert "did not accept 'nobody.here'" in reported, reported


def test_an_earned_deciding_scope_still_meets_the_role_gate() -> None:
    """**The exhibit's centrepiece, performed rather than asserted** — ADR-0014's beat 2.

    Priya Raman holds `approver` in the realm and no role in the ERP. The
    authorization server therefore grants every capability she asks for, a real
    consent screen shows her the three of them as a delegation choice, and this
    server refuses her anyway. ADR-0007 calls that drift *"the walkthrough's most
    explainable moment"* and the seed authors it deliberately.

    `-31010` and not a `403`, because the token is not what is wrong with the
    request — ADR-0002: a `403` would tell a caller to go and get a better token,
    and there is no token that would help. The remedy is an administrator's, and
    the payload says so.

    The same refusal is proven twice elsewhere on a token we minted for
    ourselves. What this adds is the only path a reader cannot call circular.
    """
    refusal = refused_by_the_deciding_tool(WITH_A_DECIDING_ROLE)

    assert refusal.code == ROLE_MISSING, refusal.error
    assert refusal.data == {
        "reason": "role_missing",
        "remedy": "administrator_grant",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": False,
    }


def test_the_run_writes_the_transcripts_the_write_up_includes() -> None:
    """The three beats whose token was consented to at a login screen, committed.

    **A test because the record is a run's**, and this is the run. Keycloak
    remembers a grant per Person and client, so a second process performing the
    same flows would post one form where these posted two — and the transcript
    would record the difference. The three beats that need no consent screen are
    written by `tests/capture.py` from a command line, and both writers write
    into one directory that one check reads.

    **What it asserts is that each beat found its exchanges.** Committing is not
    an assertion — `keep` rewrites a file only when the mask says something
    substantive changed, and the verdict is `git status --porcelain --
    docs/transcripts` in the job that ran this. What could fail silently is a
    selector below matching nothing, which would commit an empty transcript over
    a good one, so that is what is checked here.
    """
    for name, exchanges in _beats().items():
        assert exchanges, f"{name}: this run recorded no exchange for the beat"
        transcripts.keep(name, transcripts.render(name, exchanges))


def _beats() -> dict[str, tuple[transcripts.Exchange, ...]]:
    """Which of the recorded exchanges each earned beat is.

    Selection rather than redaction. Every exchange this run performed is in one
    of the three or is an answered `tools/list`, which has a file of its own —
    the listing bodies carry every tool's full input and output schema, and one
    inside the flow's transcript as well would double the artifact to say nothing
    new.

    **The flow's own beat is a prefix, not a filter.** The record accumulates
    across both connections this leg opens, and the second one begins the way
    every connection does — with a `server/discover`. Ending the beat at the call
    that lands is what keeps a later connection's opening line out of it, and it
    is also what the beat claims: the flow completes *when the call lands*.
    """
    deciding = performed(WITH_A_DECIDING_ROLE)
    refused_by_the_deciding_tool(WITH_A_DECIDING_ROLE)
    narrowed = performed(WITHOUT_A_DECIDING_ROLE)

    earned = tuple(deciding.flow.exchanges)
    declined = tuple(narrowed.flow.exchanges)

    return {
        transcripts.FLOW_COMPLETES: tuple(
            exchange for exchange in _through_the_call_that_lands(earned) if not _listing(exchange)
        ),
        transcripts.SCOPE_WITHOUT_ROLE: tuple(
            exchange for exchange in earned if _deciding_call(exchange)
        ),
        transcripts.TOOLS_LIST_FOR_TWO_TOKENS: tuple(
            exchange for exchange in earned if _listing(exchange)
        )
        + tuple(exchange for exchange in declined if _listing(exchange)),
    }


def _through_the_call_that_lands(
    exchanges: tuple[transcripts.Exchange, ...],
) -> tuple[transcripts.Exchange, ...]:
    """Everything up to and including the first `tools/call` the server answered."""
    for position, exchange in enumerate(exchanges):
        if transcripts.calls(exchange, "tools/call", TOOL) and exchange.answered:
            return exchanges[: position + 1]

    return ()


def _listing(exchange: transcripts.Exchange) -> bool:
    """A `tools/list` the server answered — not the one it met with a challenge.

    The flow starts on a `tools/list` that arrives without a credential, and that
    `401` is the first beat's opening line rather than a listing. Both are the
    same request; only one of them is an answer.
    """
    return transcripts.calls(exchange, "tools/list") and exchange.answered


def _deciding_call(exchange: transcripts.Exchange) -> bool:
    """The one call ADR-0014 adds to this leg."""
    return transcripts.calls(exchange, "tools/call", DECIDING_TOOL)

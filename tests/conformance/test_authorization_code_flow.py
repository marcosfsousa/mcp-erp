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
from dataclasses import dataclass

import pytest
from mcp_types import CallToolResult, ListToolsResult

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

DECIDER = "priya.raman"
"""Holds `approver`, so the authorization server grants every scope requested."""

NARROWED = "rafael.costa"
"""Holds `invoice_clerk` and neither deciding role, so `erp.decide` is declined.

ADR-0012 manufactured this situation deliberately — a role scope mapping listing
`approver` and `unlimited_approver`, and one Person entitled to neither — and
left what the authorization server *reports* about it as an open verification
item. This is the Person that item is answered with.
"""

TOOL = "list_requisitions"
"""One call, chosen because every Person in the Cast can make it and see rows."""


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
    run = performed(DECIDER)

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
    posted = performed(DECIDER).flow.posted

    assert posted == [LOGIN, CONSENT], (
        f"posted {posted}: Keycloak remembers a grant per Person and client, so this "
        f"assertion is about the first flow of a boot. Run `docker compose down` and "
        f"up again if {DECIDER} has already consented against this container."
    )


def test_the_request_is_derived_from_what_this_server_publishes() -> None:
    """The client asks for what the resource server said it needed, not for a list of its own.

    The `401` challenge carries `scope`, the package reads it, and the
    authorization request carries it back. That chain is what makes the
    requested-versus-granted comparison below a statement about the
    authorization server rather than about a constant this client happened to
    hold.
    """
    assert performed(DECIDER).flow.requested == CAPABILITY_SCOPES


def test_the_token_is_bound_to_this_resource_and_to_the_hosted_identity() -> None:
    """Four claims, and the third is the one only this client can produce.

    `azp` naming the document URL is the proof that the Client Identity Metadata
    Document was actually used: no client with that identifier is registered in
    the realm, so the authorization server can only have got the name by
    dereferencing it.
    """
    claims = performed(DECIDER).flow.claims

    assert claims["iss"] == ISSUER
    assert claims["sub"] == "priya-raman"
    assert claims["azp"] == CLIENT_ID
    # The audience the realm's mapper stamps, which is the string this server is
    # configured with. A token minted for anyone else is refused at gate 4.
    assert claims["aud"] == "http://localhost:8080/mcp"


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
    flow = performed(NARROWED).flow

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
    run = performed(NARROWED)

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
    earned = performed(DECIDER)
    presented = minted_by_the_helper(DECIDER, sorted(CAPABILITY_SCOPES))

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

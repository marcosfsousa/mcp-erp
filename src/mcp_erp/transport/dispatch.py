"""Gate 6 and the two adapters that render what comes back from it.

Layer 1 learns the **shape** of a refusal — ``denial_class`` and cardinality —
never its grounds: not which rule fired, against which attribute, on which row.
That is the precise form of ADR-0013's title, and everything in this module
keys on one of those two facts.

Two of the three shapes are rendered here, because both fit inside a JSON-RPC
envelope: the ``-31010`` protocol error, and the tool result marked in error.
The third — a ``403`` carrying a challenge — cannot be produced once the
response is an envelope at ``200``, so gate 5 refuses it earlier, in
:class:`~mcp_erp.transport.gates.ScopeGate`.

**There is one wire shape: every POST is answered ``application/json``.**
ADR-0002 cut the SSE response mode, so nothing here chooses a mode. What
cardinality still decides is the *body*: one outcome renders directly, and N
outcomes **fold** into one result carrying N answers.

**The fold is here, and cardinality is the only thing it keys on.** One answer
per outcome, in the order the handler yielded them, under one key this module
owns — see :data:`FOLD_KEY`. A handler that yields nothing is refused loudly
rather than answered with an empty list, because *outcomes equal items
requested* is the invariant the fold rests on and a call answered with nothing
is what a silently dropped batch looks like.

**A folded answer is always a tool result.** A refusal that depends on the
*caller* is whole-call — a ``-31010`` is the response rather than something
inside one — so a denial class other than ``tool_result`` cannot ride in a fold,
and one arriving here is a handler that reached the item chain without settling
the call first (ADR-0002). It fails loudly for the same reason the challenge
class does below: rendering it would turn a refusal a client must act on into
one a model would try to self-correct past.

**A fourth thing is rendered here and is not a refusal.** Arguments a tool's
declared schema does not permit answer ``-32602``, the protocol's own code for a
request that cannot be acted on. Nothing was authorized or denied, so it carries
no ``Reason`` and no ``denial_class`` — giving it one would amend a closed
vocabulary for a spelling mistake. A handler says so with
:class:`~mcp_erp.authorization.arguments.UnusableArgument`, a name only a handler
raises: the catch spans the handler's whole iteration, and a type the standard
library shares with the store would make every failure below it the caller's
fault (#82).

**Containment is per callback, and since #109 that is the whole of one.** A
failure of ours is answered in our own words rather than left to escape, because
what an *unrecognised* failure looks like on the wire is the protocol package's
decision and the two eras decide it differently — the legacy dispatcher pins
``code: 0`` with ``str(error)`` for v1 compatibility, which puts whatever failed
into the envelope verbatim. #82 built that guard around the handler's iteration
alone, so the rendering below it and the whole of ``on_list_tools`` still
escaped: a handler yielding a ``Decimal`` answered a legacy caller *Object of
type Decimal is not JSON serializable*. Each callback is now one boundary, and an
``MCPError`` passes through it untouched — **an ``MCPError`` reaching it is
always this module's own**, because ADR-0013 has a handler return a domain
outcome or a refused ``Decision`` and *never anything protocol-shaped*, and
nothing else under ``src/`` names the type. Re-wrapping one would replace a
``-31010`` carrying its ``Reason`` with a generic failure, which is the refusal
shape ADR-0002 built being thrown away by the guard meant to protect it.

Nothing here keys on a tool's name — the negative guarantee the cut did not
touch, and the one worth keeping.
"""

import json
import logging
from collections.abc import Mapping, Sequence
from typing import Any, Final

import mcp_types as types
from mcp import MCPError
from mcp.server import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp_types.jsonrpc import INTERNAL_ERROR, INVALID_PARAMS
from starlette.requests import Request

from mcp_erp.authorization import (
    Decision,
    DenialClass,
    Principal,
    Reason,
    UnusableArgument,
)
from mcp_erp.transport import refusals
from mcp_erp.transport.gates import PRINCIPAL_STATE, TOKEN_STATE
from mcp_erp.transport.registry import Outcome, Registry
from mcp_erp.transport.tokens import ValidatedToken

FOLD_KEY: Final = "outcomes"
"""What holds the N answers when a call yields more than one.

ADR-0013's own word for what a handler yields per item, and ``CONTEXT.md``
records that spending: *outcome* is barred as a word for a ``Decision`` and is
spent twice besides — once on the whole-call ``GateOutcome``, once on this. The
key says nothing about which tool answered or which of its arguments was the
batch, which is the negative guarantee the fold had to be built without
breaking.

**Layer 3 spells it a second time**, beside the schema that declares the folded
body, for the reason ``Handler`` is spelled twice: the two packages import
nothing from each other, and a constant they shared would have to live in layer
2 — which would then hold a value describing how layer 1 renders. Nothing on
either side can catch the two drifting apart, so the equality is asserted at the
one altitude that sees both:
``tests/wire/test_the_fold.py::test_the_declared_key_and_the_rendered_one_are_one_key``.
"""

INTERNAL_FAILURE: Final = "Internal server error"
"""What a caller is told when the failure was ours, and it says nothing else.

Word for word the protocol package's own generic message on the modern leg, so
converting an escaped exception here changes what a **legacy** caller reads and
leaves a modern one's answer exactly as it was. Two eras, one body: which leg a
caller arrived on is not a fact this server discloses either.

**Scoped to a callback, which since #109 is the whole of one.** The equality was
written against #82's guard around the handler's iteration and held for exactly
that much; the rendering below it and the whole of ``on_list_tools`` diverged.
Both are inside now, and ``tests/wire/test_the_cause_a_refusal_names.py`` asserts
the equality at four places rather than one: a failure out of the handler's
iteration, one rendering a single outcome through :func:`_render`, one rendering
several through :func:`_fold`, and one inside the listing.
"""

CALL_TOOL: Final = "tools/call"
"""The method behind ``on_call_tool``, as a contained failure's record names it.

**Not a routing decision.** The protocol package routes on the method itself and
hands the matching callback a typed parameter object; nothing here compares this
against what a caller sent. It is the label on a log line, and it is public so
that a suite driving the callback names it from here rather than spelling it
again — which is the second routing table this would otherwise become.
"""

LIST_TOOLS: Final = "tools/list"
"""The method behind ``on_list_tools``, on the same terms as :data:`CALL_TOOL`."""

_LOGGER: Final = logging.getLogger(__name__)
"""Where a failure of ours goes now that it no longer goes to the caller.

The package logs an unrecognised exception itself, and converting one into an
``MCPError`` stops it doing so — an ``MCPError`` is a *recognised* failure and is
rendered rather than reported. This restores what the conversion takes away
rather than introducing a practice: without it, closing the disclosure would have
closed the only record that anything went wrong.

Nothing collects it in this process's own right — uvicorn configures no root
handler, so it reaches ``stderr`` through :data:`logging.lastResort` and Compose
collects the container's ``stderr``. That is established rather than assumed, and
:data:`mcp_erp.transport.keys._LOGGER` is where the establishing is written down.
"""

MAXIMUM_LISTING_TTL_MS: Final = 300_000
"""Five minutes, the cap in ``ttlMs = min(5 min, remaining token lifetime)``.

The token lifetime is the half that makes the listing safe to cache at all: the
listing filters on granted scope alone, so it is a pure function of the access
token, and new scopes mean a new token and therefore a different cache key under
``private``. The cap covers the only other input — which tools are deployed.

ADR-0007 set the realm's token lifetime to five minutes so that this ``min`` is
a real choice rather than decoration: sixty seconds would degenerate it to
always picking the token, an hour would make the cap decoration.
"""

INSTRUCTIONS: Final = (
    "An MCP server exposing a mock enterprise resource planning system as a "
    "portfolio exhibit, with OAuth 2.0 as a first-class concern. Access tokens "
    "are validated locally and must be audience-bound to this resource. The set "
    "of tools returned by tools/list varies with the granted scopes the caller's "
    "token carries; a tool the caller may not reach is absent rather than "
    "refused. Results are additionally scoped per caller, and what is scoped "
    "away is omitted rather than refused."
)
"""What ``server/discover`` tells strangers, and it says nothing about purchasing.

This is the one endpoint that answers without a token, so the deletion test
applies hardest exactly here: a portable layer-2 pattern whose public face
narrates requisitions is not portable. Every noun above is protocol or
authorization vocabulary (ADR-0006).
"""


def build(registry: Registry) -> Server[None]:
    """The protocol server, with layer 3's tools reachable through two callbacks.

    The low-level server rather than the convenience wrapper, for two reasons
    that are both about this exhibit rather than about taste: the listing has to
    set its own freshness hint **per request**, because the hint depends on the
    caller's token lifetime and a server-wide hint cannot; and a refusal has to
    choose between a protocol error and a tool result, which is a decision the
    convenience wrapper makes for you.
    """

    async def on_list_tools(
        context: ServerRequestContext[None, Request],
        parameters: types.PaginatedRequestParams | None,
    ) -> types.ListToolsResult:
        """The tools this caller's **token** permits, with the freshness hint they earn.

        Raises:
            MCPError: The gate chain did not run, or anything below the listing
                failed — the second refused in this server's own words rather
                than in whatever the thing that failed happened to say.
        """
        try:
            return _listing(registry, context)
        except MCPError:
            raise
        except Exception as failure:
            raise _contained(LIST_TOOLS) from failure

    async def on_call_tool(
        context: ServerRequestContext[None, Request],
        parameters: types.CallToolRequestParams,
    ) -> types.CallToolResult:
        """Run one tool's handler and render its outcomes.

        Raises:
            MCPError: No tool has that name, the arguments are not ones the
                tool's schema permits, the handler refused with a protocol-error
                denial class, or anything below this callback failed.
        """
        try:
            return await _called(registry, context, parameters)
        except MCPError:
            raise
        except Exception as failure:
            raise _contained(CALL_TOOL, tool=parameters.name) from failure

    return Server(
        "mcp-erp",
        title="mcp-erp",
        instructions=INSTRUCTIONS,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


def _contained(method: str, *, tool: str | None = None) -> MCPError:
    """Record the failure being handled, and answer for it in this server's own words.

    **Both halves in one call, because doing one without the other is the defect
    this exists to close.** An exception that merely escapes is not contained —
    the protocol package decides what an unrecognised failure looks like on the
    wire and the two eras decide it differently: the modern entry logs and
    answers a generic ``INTERNAL_ERROR``, and the legacy dispatcher pins
    ``code=0`` with ``str(error)`` as the message for v1 compatibility, which
    would put a driver's host, port and role name in the envelope verbatim.
    ADR-0009 is why that is ours to answer for rather than the package's: not
    built is not unreachable, and this server serves both legs. And converting it
    stops the package reporting it, so a conversion that did not log would close
    the disclosure by closing the only record that anything went wrong.

    Called from inside an ``except`` block, which is what
    :meth:`logging.Logger.exception` reads the traceback from. It **returns**
    the error rather than raising it so that the caller writes ``raise ... from
    failure`` and the chain survives for anything reading it below.

    Args:
        method: Which callback failed.
        tool: What the caller named, from the callback that takes a name.
            **Read off the request rather than off a registration**, so a failure
            that never reached one still records what was asked for; it is the
            caller's own string, and nothing here inspects it or sends it
            anywhere. Omitted by the listing, which names no tool because it
            answers about all of them.

    Returns:
        The refusal to raise, carrying the modern leg's own generic wording.
    """
    named = f" for {tool!r}" if tool is not None else ""
    _LOGGER.exception("the %s callback raised%s", method, named)
    return MCPError(INTERNAL_ERROR, INTERNAL_FAILURE)


def _listing(
    registry: Registry, context: ServerRequestContext[None, Request]
) -> types.ListToolsResult:
    """The listing itself, with the containment boundary left to the callback above.

    Raises:
        MCPError: The gate chain did not run, so there is no principal or no
            validated token in request state.
    """
    principal = _principal(context)
    token = _token(context)
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name=registration.name,
                title=registration.title,
                description=registration.description,
                input_schema=registration.input_schema,
                output_schema=registration.output_schema,
            )
            for registration in registry.listed_for(principal)
        ],
        # `private` is forced rather than chosen: the specification warns that a
        # `public` result from an authenticated endpoint may be shared between
        # callers, and a scope-filtered listing marked public is a
        # cross-principal leak (ADR-0002).
        cache_scope="private",
        ttl_ms=min(MAXIMUM_LISTING_TTL_MS, token.remaining_lifetime_ms()),
    )


async def _called(
    registry: Registry,
    context: ServerRequestContext[None, Request],
    parameters: types.CallToolRequestParams,
) -> types.CallToolResult:
    """One tool's handler run and its outcomes rendered, inside the callback's boundary.

    Raises:
        MCPError: No tool has that name, the arguments are not ones the tool's
            schema permits, the handler yielded nothing, or a refusal's denial
            class is one this module cannot render here.
    """
    registration = registry.get(parameters.name)
    if registration is None:
        raise MCPError(INVALID_PARAMS, f"no such tool: {parameters.name!r}")

    principal = _principal(context)
    try:
        outcomes = [
            outcome async for outcome in registration.handler(principal, parameters.arguments or {})
        ]
    except UnusableArgument as unusable:
        # **Not a refusal, and deliberately not one.** Nothing was authorized or
        # denied here — the arguments are not ones the declared schema permits —
        # so it gets the protocol's own code for a request that cannot be acted
        # on rather than a `Reason`, which would amend a closed vocabulary for a
        # spelling mistake.
        #
        # **The span is the handler's whole iteration and the type is what
        # narrows it.** Until #82 this caught `ValueError`, on the argument that
        # a handler could then signal without importing anything layer 1 owns —
        # and the store is awaited inside that iteration, so any `ValueError`
        # from below it answered *the arguments are not ones the declared schema
        # permits*, with whatever the thing that failed happened to say as the
        # message. A type only a handler raises is what makes this catch mean
        # what the paragraph above claims; the span could not be narrowed
        # instead, because an async generator's body does not run until it is
        # iterated.
        #
        # **This is the only catch left here, and #109 is why.** Everything else
        # out of this iteration used to be caught beside it, which read as though
        # the iteration were the thing that needed containing; it is the callback
        # above that does, and the rest of this function is inside that boundary
        # exactly like the iteration is. What stayed is the one catch that is
        # about a *type* rather than about a span.
        #
        # Layer 1 still learns no grounds: the message is the handler's, and this
        # module never inspects it.
        raise MCPError(INVALID_PARAMS, str(unusable)) from unusable

    if not outcomes:
        # A handler answers, always. Nothing at all is what a batch that dropped
        # every item it was given looks like, and "outcomes equal items
        # requested" is the rule that distinction is the whole of — so it is
        # refused here rather than rendered as an empty fold, which would be this
        # module inventing an answer on a handler's behalf.
        raise MCPError(INTERNAL_ERROR, f"{registration.name!r} produced no outcome at all")

    if len(outcomes) == 1:
        return _render(outcomes[0])

    return _fold(outcomes)


def _render(outcome: Outcome) -> types.CallToolResult:
    """One outcome as a tool result, or as the protocol error its class demands.

    **The challenge class is a stated residual, not a defended-against case.**
    A handler's ``decide_call`` re-runs the scope step — the deliberate N+1 — so
    it *can* return ``insufficient_scope``, and what keeps that unreachable is
    gate 5 having already refused the same call. ADR-0002's ``403`` contract
    therefore rests on one gate rather than on two, and the honest thing to do
    when it is reached anyway is to fail loudly: rendering it as a tool result
    would turn a re-authorize into a self-correct, which is the collapse
    ADR-0002's three shapes exist to prevent.

    Raises:
        MCPError: The refusal's denial class is ``protocol_error``, or is
            ``challenge``, which nothing here can render.
    """
    if not isinstance(outcome, Decision):
        return _result(outcome, is_error=False)

    reason = _stated_reason(outcome)
    payload = refusals.refusal_payload(reason)
    if reason.denial_class is DenialClass.PROTOCOL_ERROR:
        raise MCPError(refusals.ROLE_DENIED_CODE, reason.value, data=payload)
    if reason.denial_class is DenialClass.TOOL_RESULT:
        return _result(payload, is_error=True)

    raise MCPError(
        INTERNAL_ERROR,
        f"the {reason.denial_class.value!r} denial class cannot be rendered at dispatch",
    )


def _fold(outcomes: Sequence[Outcome]) -> types.CallToolResult:
    """N outcomes as one result body, one answer per item the request named.

    **In the order the handler yielded them, and this adds no identifier of its
    own.** A caller maps answers to items by position, which is what they have
    and layer 1 does not — it never sees the request's items at all. A permitted
    answer does carry a row, because the row *is* the answer and the handler put
    it there; a **refusal** carries none, and that is the half that matters: a
    refusal that named the row it was about would make ``not_found`` on a foreign
    row distinguishable from ``not_found`` on a row that never existed, which is
    the existence oracle ADR-0002 declined to ship. Position costs the caller
    nothing — they wrote the list.

    **Marked in error when any one item was refused.** That is the same reading a
    single-item refusal has, applied to a call with more than one item on it: the
    specification's tool-execution error is *actionable feedback a model can
    self-correct on*, and a batch with a refusal in it has something to act on.
    It invites a retry of the whole call, and per-item idempotency is precisely
    what makes that harmless — ADR-0002 states the promise in those terms.

    Raises:
        MCPError: A permitted ``Decision`` was yielded as an outcome, or an
            answer's denial class is one no result body can carry.
    """
    answers: list[Mapping[str, Any]] = []
    refused = False
    for outcome in outcomes:
        payload, is_refusal = _answer(outcome)
        answers.append(payload)
        refused = refused or is_refusal

    return _result({FOLD_KEY: answers}, is_error=refused)


def _answer(outcome: Outcome) -> tuple[Mapping[str, Any], bool]:
    """One item's answer inside a fold, and whether it is a refusal.

    Raises:
        MCPError: The denial class is not ``tool_result``. Caller-level refusals
            are whole-call and item-level refusals are per-item (ADR-0002), so a
            ``-31010`` or a challenge reaching here means a handler walked its
            items without settling the call first. Both would have to be the
            *response* rather than a line inside one, and rendering either as a
            per-item answer would tell a model to route around a wall it cannot
            route around.
    """
    if not isinstance(outcome, Decision):
        return outcome, False

    reason = _stated_reason(outcome)
    if reason.denial_class is not DenialClass.TOOL_RESULT:
        raise MCPError(
            INTERNAL_ERROR,
            f"the {reason.denial_class.value!r} denial class cannot ride in a folded result",
        )
    return refusals.refusal_payload(reason), True


def _stated_reason(decision: Decision) -> Reason:
    """The reason a refused outcome carries.

    Raises:
        MCPError: There is none. A permitted ``Decision`` is layer 2's answer
            that a handler may proceed, never something for it to hand back —
            the two types exist so a permit cannot be mistaken for an answer, and
            this is that distinction reaching the wire.
    """
    reason = decision.reason
    if reason is None:
        raise MCPError(INTERNAL_ERROR, "a permitted Decision is not an outcome")
    return reason


def _result(payload: Mapping[str, Any], *, is_error: bool) -> types.CallToolResult:
    """Both halves of a result, for the two audiences ADR-0002 named.

    The structured half is what the decision matrix asserts on; the text half is
    what a model reads. One result serves both rather than a choice between them.
    """
    return types.CallToolResult(
        content=[types.TextContent(text=json.dumps(payload, indent=2, sort_keys=True))],
        structured_content=dict(payload),
        is_error=is_error,
    )


def _principal(context: ServerRequestContext[None, Request]) -> Principal:
    """The principal the token gate resolved, read from request state.

    Raises:
        MCPError: Dispatch was reached with no principal in state, which means
            the gate chain did not run — a wiring failure, refused rather than
            defaulted.
    """
    principal = _state(context).get(PRINCIPAL_STATE)
    if not isinstance(principal, Principal):
        raise MCPError(INTERNAL_ERROR, "no principal in request state")
    return principal


def _token(context: ServerRequestContext[None, Request]) -> ValidatedToken:
    """The validated token, for the listing's freshness hint.

    Raises:
        MCPError: As above.
    """
    token = _state(context).get(TOKEN_STATE)
    if not isinstance(token, ValidatedToken):
        raise MCPError(INTERNAL_ERROR, "no validated token in request state")
    return token


def _state(context: ServerRequestContext[None, Request]) -> Mapping[str, Any]:
    """The ASGI scope's state, as dispatch sees it.

    #32 confirmed by execution that a value written to ``scope["state"]`` by
    route-level middleware is readable here as ``ctx.request.state.<name>``.
    """
    request = context.request
    if request is None:
        return {}
    state: Mapping[str, Any] = request.scope.get("state", {})
    return state

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

**The fold is specified and not implemented.** No tool yields more than one
outcome yet, so a cardinality above one is refused loudly rather than folded,
and the refusal names the ticket that lands it. That is stated here and in
ADR-0013 §Streaming, restated portably, rather than left as a difference between
a document and this module.

**A fourth thing is rendered here and is not a refusal.** Arguments a tool's
declared schema does not permit answer ``-32602``, the protocol's own code for a
request that cannot be acted on. Nothing was authorized or denied, so it carries
no ``Reason`` and no ``denial_class`` — giving it one would amend a closed
vocabulary for a spelling mistake.

Nothing here keys on a tool's name — the negative guarantee the cut did not
touch, and the one worth keeping.
"""

import json
from collections.abc import Mapping
from typing import Any, Final

import mcp_types as types
from mcp import MCPError
from mcp.server import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp_types.jsonrpc import INTERNAL_ERROR, INVALID_PARAMS
from starlette.requests import Request

from mcp_erp.authorization import Decision, DenialClass, Principal
from mcp_erp.transport import refusals
from mcp_erp.transport.gates import PRINCIPAL_STATE, TOKEN_STATE
from mcp_erp.transport.registry import Outcome, Registry
from mcp_erp.transport.tokens import ValidatedToken

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
        """The tools this caller's **token** permits, with the freshness hint they earn."""
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
            # `private` is forced rather than chosen: the specification warns
            # that a `public` result from an authenticated endpoint may be
            # shared between callers, and a scope-filtered listing marked public
            # is a cross-principal leak (ADR-0002).
            cache_scope="private",
            ttl_ms=min(MAXIMUM_LISTING_TTL_MS, token.remaining_lifetime_ms()),
        )

    async def on_call_tool(
        context: ServerRequestContext[None, Request],
        parameters: types.CallToolRequestParams,
    ) -> types.CallToolResult:
        """Run one tool's handler and render its outcomes.

        Raises:
            MCPError: No tool has that name, the arguments are not ones the
                tool's schema permits, or the handler refused with a
                protocol-error denial class.
        """
        registration = registry.get(parameters.name)
        if registration is None:
            raise MCPError(INVALID_PARAMS, f"no such tool: {parameters.name!r}")

        principal = _principal(context)
        try:
            outcomes = [
                outcome
                async for outcome in registration.handler(principal, parameters.arguments or {})
            ]
        except ValueError as unusable:
            # **Not a refusal, and deliberately not one.** Nothing was authorized
            # or denied here — the arguments are not ones the declared schema
            # permits — so it gets the protocol's own code for a request that
            # cannot be acted on rather than a `Reason`, which would amend a
            # closed vocabulary for a spelling mistake.
            #
            # `ValueError` because it is the standard library's name for exactly
            # this, so a handler signals it without importing anything layer 1
            # owns. The catch stays wrapped around the handler's own iteration
            # and nothing else, and layer 1 still learns no grounds: the message
            # is the handler's, and this module never inspects it.
            raise MCPError(INVALID_PARAMS, str(unusable)) from unusable

        if len(outcomes) != 1:
            # N outcomes fold into one result body — specified by ADR-0013 and
            # not implemented, because no tool yields more than one yet. Loud
            # rather than silently rendering the first, because a batch quietly
            # answering for one item is the failure the rule "outcomes equal
            # items requested" exists to prevent.
            #
            # The message names a ticket rather than a capability, so it stays
            # true until the fold lands rather than until something is "built".
            raise MCPError(
                INTERNAL_ERROR,
                f"{registration.name!r} produced {len(outcomes)} outcomes; "
                "no tool yields more than one yet, and the fold that folds them "
                "into one result lands with issue 41",
            )

        return _render(outcomes[0])

    return Server(
        "mcp-erp",
        title="mcp-erp",
        instructions=INSTRUCTIONS,
        on_list_tools=on_list_tools,
        on_call_tool=on_call_tool,
    )


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

    reason = outcome.reason
    if reason is None:
        raise MCPError(INTERNAL_ERROR, "a permitted Decision is not an outcome")

    payload = refusals.refusal_payload(reason)
    if reason.denial_class is DenialClass.PROTOCOL_ERROR:
        raise MCPError(refusals.ROLE_DENIED_CODE, reason.value, data=payload)
    if reason.denial_class is DenialClass.TOOL_RESULT:
        return _result(payload, is_error=True)

    raise MCPError(
        INTERNAL_ERROR,
        f"the {reason.denial_class.value!r} denial class cannot be rendered at dispatch",
    )


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

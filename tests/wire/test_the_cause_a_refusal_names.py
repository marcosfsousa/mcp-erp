"""What layer 1 answers when the failure is its own, and what it records instead.

#82's reading of one seam, asked in three places, and #109's reading of the same
seam's other side, asked in two more. Layer 1 catches a category of failure and
answers with a word; each claim below is that the word is one the code has
grounds for, **and that answering it did not close the only record of what went
wrong**.

**Two of the first three are refusals and the third deliberately is not** — the
`-32602` path authorizes and denies nothing, which is the distinction half #82
exists to keep. So the file is named for what they share, which is a cause being
named, rather than for a kind they do not.

- **A key-set document layer 1 cannot read is a fruitless fetch**, refused
  `unknown_key` like any other. The failure it forbids is the one the catch in
  `KeySet._refetch` was written to prevent and did not: an exception carrying
  facts about our own infrastructure leaving the token gate.
- **A token with no `iss` is `malformed`, and only a wrong one is
  `issuer_mismatch`.** `iss` is a required claim, so an absent one is missing
  rather than mismatched — and the pair is asserted together, because a fix that
  answered `malformed` for both would make `foreign_issuer_token`'s recorded
  removal unobservable.
- **A failure raised below a handler's argument parsing is not an argument
  problem.** Both halves are here, because what has to hold is a difference: an
  `UnusableArgument` answers `-32602` carrying the handler's own message, and
  everything else answers the caller nothing at all.
- **A failure inside the key-set fetch leaves a record naming it, and the caller
  learns none of what the record holds** (#109). One claim in two directions,
  asserted
  as two tests: a silent refusal and a disclosing one are both wrong, and a fix
  can satisfy either alone. Beside it sits the falsifier for the claim
  `keys.py` rested on and nothing checked — **cancellation is not caught**, so a
  torn-down request still tears down.
- **Containment at dispatch spans the callback, not the handler's iteration**
  (#109). The third bullet's claim, at the scope it was always written as having
  and did not: `_render`, `_fold`, `_result` and the whole of `on_list_tools`
  reached a legacy caller as `code: 0` carrying the failure's own words.

**Why these sit in a wire directory, in process.** ADR-0013 gives layers 1 and 3
no test directory and routes assertions about them over the wire; this directory
holds what the server states regardless of the caller, and none of these varies
with one. Several are not reachable over HTTP at all — a real authorization
server does not serve a key set PyJWT cannot read, does not fail its fetch on
request and does not get cancelled to order, and a real store does not raise what
layer 1 was catching — so they are driven in process, on the precedent
`test_the_fold.py` set: *the alternative was a sixth directory holding one file*.

**No scenario row was minted, and that is ADR-0010's rule rather than an
omission.** Membership of `scenarios.yaml` is one row per clause this project
enforces, each recording the removal that makes it pass. Nothing gets through any
of these: the caller is refused either way, and what changes is which word the
refusal carries and whether anybody on this side of the wire can tell why.
Minting rows to house them would move a number three documents track, to record
something that is not an attack.

**The issuer one is additionally asserted over the wire**, in
`tests/attack_suite/test_token_validation.py`, as a second test on the
`foreign_issuer_token` row rather than a row of its own — the shape `unknown_key`
already carries there. Of the five above it is the one a real authorization
server's own flow can be made to produce, and the row it sits on is the row it is
a near miss for. The overlap with the assertion here is the one
`tests/authorization/test_identity.py` already takes against `Seed renders
clean`: two altitudes, neither implying the other, and this half runs without
Compose.
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator, Coroutine, Mapping
from decimal import Decimal
from typing import Any, cast

import httpx2
import jwt
import mcp_types as types
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import MCPError
from mcp.server import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import (
    StreamableHTTPASGIApp,
    StreamableHTTPSessionManager,
)
from mcp_types.jsonrpc import INTERNAL_ERROR, INVALID_PARAMS
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send

import rpc
from mcp_erp.authorization import (
    Action,
    Capability,
    Claims,
    Decision,
    Principal,
    PrincipalDirectory,
    Resource,
    UnusableArgument,
)
from mcp_erp.transport.dispatch import INTERNAL_FAILURE, build
from mcp_erp.transport.gates import PRINCIPAL_STATE, TOKEN_STATE, TokenGate
from mcp_erp.transport.keys import KeySet, UnknownKeyIdentifier
from mcp_erp.transport.registry import Handler, Registry, ToolRegistration
from mcp_erp.transport.tokens import (
    ISSUER_MISMATCH,
    MALFORMED,
    TokenRefusal,
    ValidatedToken,
    validate,
)
from tokens import ISSUER, NEIGHBOUR_REALM, REALMS_ROOT

AUDIENCE = rpc.RESOURCE
"""This server's resource identifier, from the suite that owns the spelling.

`ISSUER` arrives the same way, off the seed. Nothing here dials either: the key
set's transport is mocked and every token is minted in process, so these are the
strings the assertions compare against rather than addresses anything reaches.
"""

NEIGHBOUR_ISSUER = f"{REALMS_ROOT}/{NEIGHBOUR_REALM}"
"""ADR-0007's second realm, built from the seed's own parse rather than spelled again."""

JWKS_ADDRESS = f"{ISSUER}/protocol/openid-connect/certs"
"""Where the discovery document below points, and the address the transport answers."""

FAR_FUTURE = 4102444800
"""2100-01-01, as an expiry that cannot arrive while this suite runs."""


def _key_set(document: object) -> KeySet:
    """A key set whose fetch answers with `document`, over a real client.

    `httpx2.MockTransport` rather than a stub client, so `raise_for_status` and
    `json` are the ones production calls and only the socket is replaced.
    """

    def respond(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == JWKS_ADDRESS:
            return httpx2.Response(200, json=document)
        return httpx2.Response(200, json={"issuer": ISSUER, "jwks_uri": JWKS_ADDRESS})

    return KeySet(ISSUER, client=httpx2.AsyncClient(transport=httpx2.MockTransport(respond)))


def _key_set_whose_transport_raises(failure: BaseException) -> KeySet:
    """A key set whose key-set request fails the way `failure` says.

    Discovery answers first, so the failure lands on the fetch itself rather than
    on the step before it — which is the block whose record and whose teardown are
    what the two tests below are about.
    """

    def respond(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == JWKS_ADDRESS:
            raise failure
        return httpx2.Response(200, json={"issuer": ISSUER, "jwks_uri": JWKS_ADDRESS})

    return KeySet(ISSUER, client=httpx2.AsyncClient(transport=httpx2.MockTransport(respond)))


def _token(claims: Mapping[str, Any]) -> str:
    """A token carrying exactly these claims, signed with a key nobody published.

    The key costs nothing: every assertion below is about a refusal reached
    *before* the signature is checked.
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return jwt.encode(dict(claims), key, algorithm="RS256", headers={"kid": "unpublished"})


# ─── The key set, when the document is not one ────────────────────────────────


@pytest.mark.parametrize(
    ("shape", "document"),
    [
        ("no `keys` member at all", {}),
        ("a `keys` member holding nothing", {"keys": []}),
        ("a `keys` member that is not a list", {"keys": "not-a-list"}),
        ("keys of a type nothing can build", {"keys": [{"kty": "nonsense"}]}),
        ("a document that is not an object", []),
    ],
)
def test_a_key_set_document_layer_1_cannot_read_is_a_fruitless_fetch(
    shape: str, document: object
) -> None:
    """Every unreadable key set answers the caller as an unreachable one does.

    Parameterised over shapes rather than asserted once, because the defect was
    an exception list enumerated by hand: one case would be one more hand-written
    entry, and what has to hold is that no shape escapes.
    """
    key_set = _key_set(document)

    with pytest.raises(UnknownKeyIdentifier):
        asyncio.run(key_set.signing_key("unpublished"))


def test_a_readable_key_set_still_answers_with_its_keys() -> None:
    """The control. Widening what is suppressed must not swallow the success path."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    published = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    key_set = _key_set({"keys": [dict(published, kid="published", alg="RS256")]})

    assert asyncio.run(key_set.signing_key("published")) is not None


def test_a_malformed_key_set_reaches_the_token_gate_as_a_refusal() -> None:
    """The same claim at the response, which is the altitude the disclosure is at.

    `signing_key` raising the wrong exception is a defect; the token gate
    answering `500` where it owes `401 unknown_key` is what a caller sees, and
    ADR-0006's rule is about what reaches them.
    """

    async def reached(request: Request) -> PlainTextResponse:
        """The application behind the gate, which this request must never reach."""
        return PlainTextResponse("reached")

    gated = TokenGate(
        Starlette(routes=[Route("/mcp", reached, methods=["POST"])]),
        key_set=_key_set({"keys": []}),
        directory=PrincipalDirectory(()),
        audience=AUDIENCE,
        metadata_url=f"{AUDIENCE}/.well-known/oauth-protected-resource",
        scopes_supported=("erp.read",),
    )
    presented = _token({"iss": ISSUER, "sub": "s", "aud": AUDIENCE, "exp": FAR_FUTURE})

    with TestClient(gated, raise_server_exceptions=False) as client:
        response = client.post(
            "/mcp",
            headers={
                "Authorization": f"Bearer {presented}",
                "Content-Type": "application/json",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        )

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    assert "unknown_key" in response.headers["www-authenticate"]


# ─── The fetch that failed, and the two things that must leave it ─────────────

UNREACHABLE = "[Errno 111] Connection refused: keycloak:8081"
"""What the outbound leg says when the authorization server is down.

A host and a port, which is the class of fact ADR-0006 keeps out of a refusal —
and the class of fact an operator needs in order to tell an outage from a defect
of ours. The two tests below are the two directions of that one sentence.
"""


def test_a_failure_inside_the_fetch_leaves_a_record_naming_what_failed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The fetch is contained, not silenced.

    Containment and silence were one act until #109: a defect inside `_refetch`
    left `self._keys` as it was and refused the caller, which is exactly what an
    authorization server that is down does, and nothing anywhere distinguished
    them. What is asserted is that the record exists **and carries the traceback**
    — a bare message would name the block and not the line, which is the same
    silence with more code.
    """
    key_set = _key_set_whose_transport_raises(httpx2.ConnectError(UNREACHABLE))

    with (
        caplog.at_level(logging.ERROR, logger="mcp_erp.transport.keys"),
        pytest.raises(UnknownKeyIdentifier),
    ):
        asyncio.run(key_set.signing_key("unpublished"))

    recorded = [record for record in caplog.records if record.name == "mcp_erp.transport.keys"]
    assert len(recorded) == 1
    assert recorded[0].exc_info is not None
    assert UNREACHABLE in caplog.text


def test_the_caller_is_told_none_of_what_that_record_holds() -> None:
    """The other direction, and the reason the record is worth having at all.

    The same failure, asked at the caller's altitude: `UnknownKeyIdentifier`
    carries the key identifier the *caller* sent and nothing about the leg that
    could not be reached. A fix that logged by widening what reaches the caller
    would pass the test above and fail this one.
    """
    key_set = _key_set_whose_transport_raises(httpx2.ConnectError(UNREACHABLE))

    with pytest.raises(UnknownKeyIdentifier) as refused:
        asyncio.run(key_set.signing_key("unpublished"))

    assert str(refused.value) == "unpublished"
    assert UNREACHABLE not in str(refused.value)


def test_a_cancellation_inside_the_fetch_still_tears_the_request_down() -> None:
    """The falsifier for the one claim `keys.py` makes and nothing asserted.

    `_refetch` catches every exception a fetch can raise and says in its own
    docstring that cancellation is not among them, because `CancelledError`
    descends from `BaseException` — so a request being torn down still tears down
    rather than being converted into a refusal the caller would retry.

    **It is written here because the catch it constrains is the one #109
    rewrote.** A widening to `BaseException` — the obvious way to make the record
    above cover *everything* — keeps every other test in this file green and
    turns this one red, which is the whole reason it exists.
    """
    key_set = _key_set_whose_transport_raises(asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(key_set.signing_key("unpublished"))


# ─── The issuer, absent and wrong ─────────────────────────────────────────────


def test_a_token_with_no_issuer_is_refused_as_missing_rather_than_mismatched() -> None:
    """`iss` is in `REQUIRED_CLAIMS`, so nothing was mismatched — something was absent."""
    token = _token({"sub": "s", "aud": AUDIENCE, "exp": FAR_FUTURE})

    with pytest.raises(TokenRefusal) as refused:
        asyncio.run(validate(token, key_set=_key_set({}), issuer=ISSUER, audience=AUDIENCE))

    assert refused.value.description == MALFORMED


def test_a_token_naming_another_issuer_is_still_refused_as_a_mismatch() -> None:
    """The other half, and the reason both are asserted in one file.

    `foreign_issuer_token`'s recorded removal is *skip the `iss` check against the
    configured issuer*, and it is observable only because this description differs
    from every other. Collapsing the two would delete that row's evidence without
    touching the row.
    """
    token = _token({"iss": NEIGHBOUR_ISSUER, "sub": "s", "aud": AUDIENCE, "exp": FAR_FUTURE})

    with pytest.raises(TokenRefusal) as refused:
        asyncio.run(validate(token, key_set=_key_set({}), issuer=ISSUER, audience=AUDIENCE))

    assert refused.value.description == ISSUER_MISMATCH


# ─── The catch at dispatch, and what it is allowed to span ────────────────────

STORE_FAILURE = "connection to '10.0.0.7' failed: FATAL: role 'erp' does not exist"
"""What a driver says when a deployment has come apart. Nothing a caller may read."""

UNUSABLE_ARGUMENT = "'id' must be a string"
"""What a handler says about an argument its declaration forbids. The caller's to read."""

MODERN = "modern"
LEGACY = "legacy"
"""The two eras this server answers, as the two legs a claim about the wire needs."""


class _Context:
    """Everything dispatch reads of a request context, which is the ASGI state."""

    def __init__(self) -> None:
        """Hold a request carrying what the gate chain would have resolved."""
        self.request = _Request()


class _Request:
    """The half of a Starlette request dispatch reaches through."""

    def __init__(self) -> None:
        """Hold the scope's state mapping, under the two keys the token gate writes."""
        self.scope: dict[str, Any] = {"state": dict(RESOLVED)}


def _handler_raising(error: BaseException) -> Handler:
    """A handler that parses its argument, then fails the way `error` says.

    The parsing succeeds first, deliberately: the claim is about where in the
    handler's own iteration the failure came from, not about which exception type
    reaches an argument check.
    """

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """Yield nothing; raise where a store would have been awaited."""
        identifier = arguments.get("id")
        if not isinstance(identifier, str):
            raise UnusableArgument(UNUSABLE_ARGUMENT)
        raise error
        yield {}  # pragma: no cover — unreachable, and what makes this a generator

    return handler


TOOL = "get_requisition"
"""One tool name, since layer 1 keys on nothing else about it."""

ARGUMENTS = {"id": "req_0001"}
"""Arguments the handler below parses successfully, so nothing here is a bad argument."""

PRINCIPAL = Principal(
    issuer=ISSUER,
    subject="hana-kovac",
    granted_scopes=frozenset({"erp.read"}),
    roles=frozenset({"requester"}),
    partition="CC-100",
)
"""What the gate chain would have resolved by the time dispatch is reached."""

TOKEN = ValidatedToken(
    claims=Claims(
        issuer=PRINCIPAL.issuer,
        subject=PRINCIPAL.subject,
        granted_scopes=PRINCIPAL.granted_scopes,
    ),
    expires_at=FAR_FUTURE,
)
"""The other half of what the gate chain writes, which the **listing** reads.

`on_call_tool` never touches it and `on_list_tools` cannot answer without it —
the freshness hint is `min(5 min, remaining token lifetime)`. Absent, the listing
refuses `no validated token in request state`, which is an `MCPError` and
therefore already contained: the probe below would pass while testing the wrong
containment.
"""

RESOLVED: Mapping[str, Any] = {PRINCIPAL_STATE: PRINCIPAL, TOKEN_STATE: TOKEN}
"""The request state the gate chain leaves behind, under the gate's own key names."""


def _registry_of(handler: Handler) -> Registry:
    """A registry carrying one tool whose handler is the argument."""
    action: Action[Resource] = Action(
        namespace="erp",
        capability=Capability.READ,
        required_roles=frozenset(),
        rules=(),
        partition_bypass=frozenset(),
    )
    return Registry(
        [
            ToolRegistration(
                name=TOOL,
                title="Get requisition",
                description="",
                # Declared rather than empty, because one claim below drives the
                # **listing**, and the protocol package validates a rendered
                # `inputSchema` against JSON Schema's own requirement of a
                # `type`. A tool this suite never varies needs only the shape.
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                action=action,
                handler=handler,
            )
        ]
    )


def _served(registry: Registry) -> Server[None]:
    """The protocol server over that registry, with both callbacks registered.

    A `Registry` rather than a handler, because one of the claims below is about
    the callback that reaches **no** handler: `on_list_tools` walks the registry
    and answers, and a failure inside that walk is contained by the same rule.
    """
    return build(registry)


def _call(handler: Handler) -> types.CallToolResult:
    """Drive `tools/call` at the callback layer 1 registers, with a resolved principal."""
    entry = _served(_registry_of(handler)).get_request_handler("tools/call")
    assert entry is not None

    parameters = types.CallToolRequestParams(name=TOOL, arguments=ARGUMENTS)

    # Two casts, and both are about what a real context costs rather than about
    # what dispatch reads. `_state` reaches `context.request.scope["state"]` and
    # nothing else, so the object above is the whole of what is used; building the
    # declared type would mean a live `ServerSession`. The second is the handler
    # entry's return, which the registry types as the union of every callback's.
    context = cast("ServerRequestContext[None, Request]", _Context())
    handled = cast("Coroutine[Any, Any, types.CallToolResult]", entry.handler(context, parameters))

    return asyncio.run(handled)


def _application(registry: Registry) -> Starlette:
    """The composition root's wiring for the tool endpoint, minus the gate chain.

    One `Route` holding a `StreamableHTTPASGIApp` over a stateless,
    `json_response` session manager — `app.py`'s two flags, for the reasons
    `app.py` gives — and a middleware writing the principal the token gate would
    have resolved. What that buys over `_call` is **the protocol package's own
    exception handling**, which is the thing under test: everything about how a
    handler failure becomes an envelope happens above dispatch, and no assertion
    made before the envelope exists can see any of it.
    """
    sessions = StreamableHTTPSessionManager(
        app=_served(registry), stateless=True, json_response=True
    )

    class _Resolved:
        """Stands in for the gate chain, writing the two things dispatch reads."""

        def __init__(self, app: ASGIApp) -> None:
            """Wrap the application the route serves."""
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            """Write the principal and the validated token into state, then hand on."""
            scope.setdefault("state", {}).update(RESOLVED)
            await self.app(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        """Run the session manager's task group, which nothing else will."""
        async with sessions.run():
            yield

    return Starlette(
        lifespan=lifespan,
        routes=[
            Route(
                "/mcp",
                endpoint=StreamableHTTPASGIApp(sessions),
                methods=["POST"],
                middleware=[Middleware(_Resolved)],
            )
        ],
    )


CALL = "tools/call"
LIST = "tools/list"
"""The two methods layer 1 registers a callback for, and the two `_over_http` drives."""


def _over_http(registry: Registry, *, era: str = MODERN, method: str = CALL) -> dict[str, Any]:
    """One request through the package's transport, as the response body.

    **Both eras, because this server answers both and they do not share an error
    path.** The package maps an unrecognised handler failure differently on each
    leg — its own words for that mapping are *"`JSONRPCDispatcher` currently pins
    `code=0` for v1 compat, the modern HTTP entry uses `INTERNAL_ERROR`"* — so a
    claim about what reaches a caller is two claims until both are made. ADR-0009
    is the reason it matters here rather than being somebody else's problem: not
    built is not unreachable, and the legacy leg is served by the package's own
    handler rather than by anything this repository wrote.

    **Both methods, since #109.** The divergence above is the *dispatcher's*, so
    it is keyed on neither the method nor the handler: every callback layer 1
    registers reaches the same two legs, and a containment claim made about one
    of them is a claim about one of them.
    """
    # The suite's own envelope and headers rather than a second spelling of them.
    # `rpc` builds what each era carries — the modern `_meta` block a removed
    # handshake used to establish and the header pair that must agree with it,
    # and the legacy shape by subtraction from it — and a hand-written copy would
    # be a second rule to keep equal.
    parameters: dict[str, Any] = {"name": TOOL, "arguments": ARGUMENTS} if method == CALL else {}
    modern = era == MODERN
    headers = rpc.routing_headers(method, parameters) if modern else dict(rpc.TRANSPORT_HEADERS)
    body = (
        rpc.envelope(method, parameters)
        if modern
        else {"jsonrpc": "2.0", "id": 1, "method": method, "params": parameters}
    )

    with TestClient(_application(registry), raise_server_exceptions=False) as client:
        response = client.post("/mcp", headers=headers, json=body)

    parsed: dict[str, Any] = response.json()
    return parsed


def test_an_argument_a_declaration_forbids_is_still_invalid_params() -> None:
    """The half that must not move. A handler's own message is the caller's to read."""
    with pytest.raises(MCPError) as refused:
        _call(_handler_raising(UnusableArgument(UNUSABLE_ARGUMENT)))

    assert refused.value.code == INVALID_PARAMS
    assert str(refused.value) == UNUSABLE_ARGUMENT


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(ValueError(STORE_FAILURE), id="the-type-layer-1-used-to-catch"),
        pytest.param(RuntimeError(STORE_FAILURE), id="a-statement-that-stopped-being-one"),
        pytest.param(KeyError(STORE_FAILURE), id="a-row-shaped-other-than-declared"),
    ],
)
def test_a_failure_below_the_argument_check_is_not_reported_as_a_bad_argument(
    failure: BaseException,
) -> None:
    """No code reaching the caller claims they can fix what the store did.

    `ValueError` is the row that matters and the reason the other two are beside
    it: the exception layer 1 caught was the one a handler used to raise, so the
    same type from two places got one answer. What is asserted is the difference
    — a failure of ours is refused as ours, rather than arriving as *the
    arguments are not ones the declared schema permits*.

    The other half of the claim — that the store's words do not reach the caller
    either — is not visible at this altitude, and the test below is where it is
    made.
    """
    with pytest.raises(MCPError) as refused:
        _call(_handler_raising(failure))

    assert refused.value.code == INTERNAL_ERROR
    assert refused.value.code != INVALID_PARAMS
    assert STORE_FAILURE not in str(refused.value)


@pytest.mark.parametrize("era", [MODERN, LEGACY])
@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(ValueError(STORE_FAILURE), id="the-type-layer-1-used-to-catch"),
        pytest.param(RuntimeError(STORE_FAILURE), id="a-statement-that-stopped-being-one"),
        pytest.param(KeyError(STORE_FAILURE), id="a-row-shaped-other-than-declared"),
    ],
)
def test_nothing_the_store_says_reaches_the_caller(failure: BaseException, era: str) -> None:
    """The disclosure half, asserted on the response body because that is where it is.

    **This is the assertion the in-process one above cannot make, and the reason
    it is worth a second altitude.** An exception that merely escapes dispatch is
    not contained, because what an unrecognised failure looks like on the wire is
    the protocol package's decision and the two eras decide it differently: the
    modern entry logs and answers a generic `INTERNAL_ERROR`, and the legacy
    dispatcher pins `code=0` with `str(error)` as the message for v1
    compatibility. On that leg *escaped* and *disclosed* were the same outcome —
    the driver's host, port and role name in the envelope verbatim.

    **Both eras, because ADR-0009 says not built is not unreachable.** The legacy
    leg is served by the package's own handler rather than by anything here, and
    a claim about what reaches a caller that holds on one leg is not the claim.

    It is the key set's rule one gate lower: ADR-0006's non-disclosure is about
    **what reaches the caller**, and only a response can answer that.
    """
    body = _over_http(_registry_of(_handler_raising(failure)), era=era)
    rendered = json.dumps(body)

    assert STORE_FAILURE not in rendered
    assert "10.0.0.7" not in rendered
    assert body["error"]["code"] == INTERNAL_ERROR
    assert body["error"]["message"] == INTERNAL_FAILURE


def test_the_two_eras_answer_a_failure_of_ours_identically() -> None:
    """One body, so which leg a caller arrived on is not disclosed either.

    Asserted as an equality rather than as two expectations, because that is the
    claim: the eras diverge in the package and converge here, and two tests
    expecting the same literal twice would keep both halves and lose the fact
    that they have to agree.
    """
    failure = ValueError(STORE_FAILURE)

    modern = _over_http(_registry_of(_handler_raising(failure)), era=MODERN)
    legacy = _over_http(_registry_of(_handler_raising(failure)), era=LEGACY)

    assert modern["error"] == legacy["error"]


# ─── The span of that catch, and the two places it did not reach ──────────────

UNSERIALISABLE = Decimal("41.00")
"""An outcome no `json.dumps` will take, and the one a domain plausibly yields.

`purchase_to_pay` stringifies its amounts before they reach layer 1, so this is a
mechanism rather than a live disclosure: what a `Decimal` probes is the **span**
of dispatch's catch, not a defect in the tools this exhibit ships. The type is
chosen because it is what a store hands back for a money column, and a handler
that forgot the conversion is the ordinary way this arrives.
"""

LISTING_FAILURE = "'/srv/.venv/lib/python3.13/site-packages/mcp_types' is not a package"
"""What a failure below the listing says. A filesystem path, so ours and not the caller's.

Not `STORE_FAILURE`, and the difference is the point: `on_list_tools` reaches no
store — it walks the registry and reads the token's expiry — so a driver's words
are the wrong words for what could go wrong there. The class of fact is the same
one ADR-0006 keeps out of a refusal.
"""


def _handler_yielding(*outcomes: Mapping[str, Any]) -> Handler:
    """A handler that raises nothing and yields exactly these outcomes.

    The failure this provokes is **after** the iteration has completed, in the
    rendering, which is the half of dispatch the catch did not span. One outcome
    reaches `_render` and two reach `_fold`; both end at `_result`.
    """

    async def handler(
        principal: Principal, arguments: Mapping[str, Any]
    ) -> AsyncIterator[Mapping[str, Any] | Decision]:
        """Yield each outcome in turn, having decided nothing."""
        for outcome in outcomes:
            yield outcome

    return handler


class _RegistryWhoseListingFails(Registry):
    """A registry whose listing filter fails the way a defect below it would.

    Subclassed rather than stubbed, because what has to run is layer 1's callback
    over a real `Registry`: `on_list_tools` reaches no handler at all, so the one
    question it asks is the only seam a failure can be constructed at.
    """

    def listed_for(self, principal: Principal) -> tuple[ToolRegistration, ...]:
        """Fail where the filter would have answered."""
        raise RuntimeError(LISTING_FAILURE)


def _listing_that_fails() -> Registry:
    """The registry above, carrying the same one registration as everything else here."""
    return _RegistryWhoseListingFails(_registry_of(_handler_yielding({})).listed_for(PRINCIPAL))


@pytest.mark.parametrize("era", [MODERN, LEGACY])
@pytest.mark.parametrize(
    "cardinality",
    [
        pytest.param(1, id="one-outcome-through-render"),
        pytest.param(2, id="two-outcomes-through-fold"),
    ],
)
def test_a_failure_rendering_an_outcome_is_contained_like_one_inside_the_handler(
    cardinality: int, era: str
) -> None:
    """Containment is per-dispatch since #109, where it was per-iteration.

    #82 wrapped `async for outcome in registration.handler(...)` and said so in a
    comment. Everything after it — `_render`, `_fold`, `_result` — sat outside,
    and on the legacy leg *escaped* and *disclosed* are the same outcome: the
    package's v1-compatible dispatcher pins `code: 0` and puts `str(error)` in
    the message. A handler yielding a `Decimal` reached a legacy caller as
    *Object of type Decimal is not JSON serializable*.

    Both cardinalities, because they are two paths into the same renderer and the
    span has to cover the pair rather than whichever one a test happened to take.
    """
    registry = _registry_of(_handler_yielding(*({"amount": UNSERIALISABLE},) * cardinality))

    body = _over_http(registry, era=era)
    rendered = json.dumps(body)

    assert "Decimal" not in rendered
    assert body["error"]["code"] == INTERNAL_ERROR
    assert body["error"]["message"] == INTERNAL_FAILURE


def test_the_two_eras_answer_a_rendering_failure_identically() -> None:
    """*Both eras answer identically* now covers the dispatch, not just the iteration.

    Asserted as an equality rather than as two expectations of one literal, for
    the reason its sibling below the handler catch gives: the eras diverge in the
    package and converge here, and what has to hold is that they agree.
    """
    registry = _registry_of(_handler_yielding({"amount": UNSERIALISABLE}))

    modern = _over_http(registry, era=MODERN)
    legacy = _over_http(registry, era=LEGACY)

    assert modern["error"] == legacy["error"]


@pytest.mark.parametrize("era", [MODERN, LEGACY])
def test_a_failure_inside_the_listing_is_contained_too(era: str) -> None:
    """The other callback, which had no containment of any kind.

    `on_call_tool` had a catch spanning part of itself; `on_list_tools` had none,
    so anything raised anywhere in it reached a legacy caller as `code: 0`
    carrying the failure's own words. It reaches no store today — which is why
    this was a mechanism left open rather than a disclosure that shipped — and
    *what could go wrong there* is not a list layer 1 gets to enumerate on the
    deployment's behalf.
    """
    body = _over_http(_listing_that_fails(), era=era, method=LIST)
    rendered = json.dumps(body)

    assert LISTING_FAILURE not in rendered
    assert "site-packages" not in rendered
    assert body["error"]["code"] == INTERNAL_ERROR
    assert body["error"]["message"] == INTERNAL_FAILURE


def test_the_two_eras_answer_a_listing_failure_identically() -> None:
    """The same equality, on the callback the claim did not previously reach."""
    modern = _over_http(_listing_that_fails(), era=MODERN, method=LIST)
    legacy = _over_http(_listing_that_fails(), era=LEGACY, method=LIST)

    assert modern["error"] == legacy["error"]


def test_the_listing_still_answers_when_nothing_below_it_fails() -> None:
    """The control. Wrapping a callback must not swallow the answer it was wrapping."""
    body = _over_http(_registry_of(_handler_yielding({})), method=LIST)

    assert "error" not in body
    assert [tool["name"] for tool in body["result"]["tools"]] == [TOOL]

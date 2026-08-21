"""Three answers layer 1 gives, and whether it established the cause each names.

#82's reading of one seam, asked in three places. Layer 1 catches a category of
failure and answers with a word; each claim below is that the word is one the
code has grounds for.

**Two of the three are refusals and the third deliberately is not** — the
`-32602` path authorizes and denies nothing, which is the distinction half this
change exists to keep. So the file is named for what they share, which is a cause
being named, rather than for a kind they do not.

- **A key-set document layer 1 cannot read is a fruitless fetch**, refused
  `unknown_key` like any other. The failure it forbids is the one the suppression
  in `KeySet._refetch` was written to prevent and did not: an exception carrying
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

**Why these sit in a wire directory, in process.** ADR-0013 gives layers 1 and 3
no test directory and routes assertions about them over the wire; this directory
holds what the server states regardless of the caller, and none of the three
varies with one. Two of them are not reachable over HTTP at all — a real
authorization server does not serve a key set PyJWT cannot read, and a real store
does not raise what layer 1 was catching — so they are driven in process, on the
precedent `test_the_fold.py` set: *the alternative was a sixth directory holding
one file*.

**No scenario row was minted, and that is ADR-0010's rule rather than an
omission.** Membership of `scenarios.yaml` is one row per clause this project
enforces, each recording the removal that makes it pass. Nothing gets through any
of these three: the caller is refused either way, and what changes is which word
the refusal carries. Minting rows to house them would move a number three
documents track, to record something that is not an attack.

**The issuer one is additionally asserted over the wire**, in
`tests/attack_suite/test_token_validation.py`, as a second test on the
`foreign_issuer_token` row rather than a row of its own — the shape `unknown_key`
already carries there. That is the one of the three a real authorization server's
own flow can be made to produce, and the row it sits on is the row it is a near
miss for. The overlap with the assertion here is the one
`tests/authorization/test_identity.py` already takes against `Seed renders
clean`: two altitudes, neither implying the other, and this half runs without
Compose.
"""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator, Coroutine, Mapping
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
    Decision,
    Principal,
    PrincipalDirectory,
    Resource,
    UnusableArgument,
)
from mcp_erp.transport.dispatch import INTERNAL_FAILURE, build
from mcp_erp.transport.gates import TokenGate
from mcp_erp.transport.keys import KeySet, UnknownKeyIdentifier
from mcp_erp.transport.registry import Handler, Registry, ToolRegistration
from mcp_erp.transport.tokens import ISSUER_MISMATCH, MALFORMED, TokenRefusal, validate
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

    def __init__(self, principal: Principal) -> None:
        """Hold a request carrying the principal the gate chain would have resolved."""
        self.request = _Request(principal)


class _Request:
    """The half of a Starlette request dispatch reaches through."""

    def __init__(self, principal: Principal) -> None:
        """Hold the scope's state mapping, under the key the token gate writes."""
        self.scope: dict[str, Any] = {"state": {"principal": principal}}


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


def _served_by(handler: Handler) -> Server[None]:
    """The protocol server, carrying one tool whose handler is the argument."""
    action: Action[Resource] = Action(
        namespace="erp",
        capability=Capability.READ,
        required_roles=frozenset(),
        rules=(),
        partition_bypass=frozenset(),
    )
    return build(
        Registry(
            [
                ToolRegistration(
                    name=TOOL,
                    title="Get requisition",
                    description="",
                    input_schema={},
                    output_schema={},
                    action=action,
                    handler=handler,
                )
            ]
        )
    )


def _call(handler: Handler) -> types.CallToolResult:
    """Drive `tools/call` at the callback layer 1 registers, with a resolved principal."""
    entry = _served_by(handler).get_request_handler("tools/call")
    assert entry is not None

    parameters = types.CallToolRequestParams(name=TOOL, arguments=ARGUMENTS)

    # Two casts, and both are about what a real context costs rather than about
    # what dispatch reads. `_state` reaches `context.request.scope["state"]` and
    # nothing else, so the object above is the whole of what is used; building the
    # declared type would mean a live `ServerSession`. The second is the handler
    # entry's return, which the registry types as the union of every callback's.
    context = cast("ServerRequestContext[None, Request]", _Context(PRINCIPAL))
    handled = cast("Coroutine[Any, Any, types.CallToolResult]", entry.handler(context, parameters))

    return asyncio.run(handled)


def _application(handler: Handler) -> Starlette:
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
        app=_served_by(handler), stateless=True, json_response=True
    )

    class _Resolved:
        """Stands in for the gate chain, writing the one thing dispatch reads."""

        def __init__(self, app: ASGIApp) -> None:
            """Wrap the application the route serves."""
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            """Write the principal into the scope's state, then hand on."""
            scope.setdefault("state", {})["principal"] = PRINCIPAL
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


def _over_http(handler: Handler, *, era: str = MODERN) -> dict[str, Any]:
    """One `tools/call` through the package's transport, as the response body.

    **Both eras, because this server answers both and they do not share an error
    path.** The package maps an unrecognised handler failure differently on each
    leg — its own words for that mapping are *"`JSONRPCDispatcher` currently pins
    `code=0` for v1 compat, the modern HTTP entry uses `INTERNAL_ERROR`"* — so a
    claim about what reaches a caller is two claims until both are made. ADR-0009
    is the reason it matters here rather than being somebody else's problem: not
    built is not unreachable, and the legacy leg is served by the package's own
    handler rather than by anything this repository wrote.
    """
    # The suite's own envelope and headers rather than a second spelling of them.
    # `rpc` builds what each era carries — the modern `_meta` block a removed
    # handshake used to establish and the header pair that must agree with it,
    # and the legacy shape by subtraction from it — and a hand-written copy would
    # be a second rule to keep equal.
    parameters = {"name": TOOL, "arguments": ARGUMENTS}
    modern = era == MODERN
    headers = (
        rpc.routing_headers("tools/call", parameters) if modern else dict(rpc.TRANSPORT_HEADERS)
    )
    body = (
        rpc.envelope("tools/call", parameters)
        if modern
        else {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": parameters}
    )

    with TestClient(_application(handler), raise_server_exceptions=False) as client:
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
    body = _over_http(_handler_raising(failure), era=era)
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

    modern = _over_http(_handler_raising(failure), era=MODERN)
    legacy = _over_http(_handler_raising(failure), era=LEGACY)

    assert modern["error"] == legacy["error"]

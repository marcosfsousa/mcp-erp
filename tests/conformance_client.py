"""The conformance client: one authorization code flow, earned through the hosted document.

ADR-0008 packages this as **one library surface with two entry points** — the
suite in `tests/conformance/` imports it, and the `__main__` block below performs
the flow from a command line. That is not a compromise between two designs. In
`mcp` 2.0.0 the unified `Client` takes no authentication parameter, so
authentication attaches to the HTTP client underneath the transport, and every
line of *connect, call, assert* is identical whichever object is attached.
:class:`Flow` earns a token through the Client Identity Metadata Document;
:class:`Bearer` presents one `tests/tokens.py` already minted. **Mint versus earn
is a constructor argument, not an architecture**, and :func:`connect` is where
that stops being a claim: it takes an `httpx2.Auth` and knows nothing else.

**This is the client under test, not the fixture minter.** `tokens.py` drives the
same three forms against a client registered in the realm; this one is not
registered anywhere. Its identity is a URL that GitHub Pages serves, the
authorization server dereferences that URL on the authorization request, and the
whole point is that a client we did not pre-provision can complete a flow.

**What is shared with `tokens.py`, and what is copied.** The two drive the same
three forms, so the overlap is real and worth being explicit about rather than
noticed later.

*Shared, imported from there:* every pure function and every constant —
`form_action`, `redirect_error`, `rebase`, `scope_set`, `decode_claims`,
`PASSWORD`, `LOGIN_FORM`, `MAX_AUTHORIZATION_STEPS`. Two of those were made
public for this module, which is the shape sharing takes when it can be taken.

*Copied, deliberately:* everything that touches a client — the request helpers,
the cookie concession, the walk to the callback. They cannot be shared, and not
for a reason a little more effort would remove: that helper is **synchronous and
speaks `httpx`**, this one is **asynchronous and speaks `httpx2`**, and both
packages are in this environment on purpose — the 2.x line is what the protocol
package carries and the 0.x line belongs to the fixture minter. Bridging them
means an abstraction over two HTTP packages and two concurrency models, to save
a handful of functions whose whole content is *do one request and raise with the
server's words*. The copy is the cheaper honesty. Where the two diverge in more
than colour — the cookie concession, the consent step being recorded — the
function that differs says so at its own definition.

**Preflight, and why it runs before Compose.** ADR-0008's second mechanism.
Without it, Pages being unreachable and this server rejecting a valid flow
present identically as *the flow failed*. :func:`preflight` fetches the document
URL, refuses anything but a `200`, and hashes the body against the committed
bytes — so an external cause fails a **named step before our server has run at
all**. The `Authorization code flow` job runs it as its own step, ahead of
`docker compose up`; the suite asserts it first for a reader running locally.

**Two addresses, one identity**, on exactly the terms `tokens.py` states. The
issuer is `http://keycloak:8081/...`, and the protocol package follows a
discovered endpoint verbatim — it has no rebasing hook of its own. So a reader
without the `127.0.0.1 keycloak` line in their hosts file points the transport
somewhere reachable, and :class:`Rebased` moves the address the requests go to
and never the issuer they assert::

    KEYCLOAK_BASE_URL=http://localhost:8081

Standalone, which is what a reader runs to watch the flow happen::

    uv run python tests/conformance_client.py --preflight
    uv run python tests/conformance_client.py priya.raman
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections.abc import AsyncGenerator, AsyncIterator, Generator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final
from urllib.parse import parse_qs, urljoin, urlparse

import httpx2
from mcp.client import Client
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

import rpc
from tokens import (
    BASE_URL as KEYCLOAK_BASE_URL,
)
from tokens import (
    ISSUER_ORIGIN,
    LOGIN_FORM,
    MAX_AUTHORIZATION_STEPS,
    PASSWORD,
    decode_claims,
    form_action,
    rebase,
    redirect_error,
    scope_set,
)
from transcripts import Exchange, snapshot

REPO = Path(__file__).parents[1]

DOCUMENT = REPO / "public" / "clients" / "conformance" / "1.json"
"""The committed copy of the Client Identity Metadata Document.

The same bytes `.github/workflows/pages.yml` publishes and the
`Published documents are immutable` job refuses to see modified. `.gitattributes`
pins it `-text` so no checkout rewrites its line endings — which is what makes
the digest comparison in :func:`preflight` mean anything.
"""

METADATA: Final[Mapping[str, Any]] = json.loads(DOCUMENT.read_text(encoding="utf-8"))
"""What the document says, read once and never restated in Python.

Every property this client acts on comes from here rather than from a constant
beside it — with the single exception :data:`GRANT_TYPES` states and argues. A
second copy of `redirect_uris` would be a second thing to keep equal to a file
that **cannot be corrected in place**: the `client_id` is the URL, so a
divergence is not a bug to fix but a new document version to publish.
"""

CLIENT_ID = str(METADATA["client_id"])
"""The client identifier, which is the document's own URL and its own address.

Read out of the document rather than written beside it, so the identifier this
client presents and the identifier :func:`preflight` fetches cannot come apart.
Draft `-00` §4.2 puts the authorization server under a `MUST` to check that the
two agree, and a client that could fail that check by editing one of two
constants would be testing our copy-paste rather than their validation.
"""

SERVER = f"{rpc.BASE_URL}{rpc.ENDPOINT}"
"""The address the tool endpoint answers at — the gateway's, like every suite's."""

GRANT_TYPES: Final = ["authorization_code"]
"""What the client tells **its own library** it can do, and the one place that is not the document.

The published document names `refresh_token` as well, deliberately, and **the
run still drives the document as published** — because under a hosted document
the `client_metadata` handed to the package is local configuration rather than
anything sent. There is no registration request to put it in. Exactly two of its
members leave this process: `redirect_uris[0]`, on the authorization request,
and `scope`, which the package overwrites from this server's own metadata before
it is used. `grant_types` is never one of them. The authorization server reads
`grant_types` off the document it fetched for itself, and it still issues this
client a refresh token.

The protocol package reads it for exactly one other purpose. SEP-2207 appends
`offline_access` to the requested scope when the client declares `refresh_token`
**and** the authorization server advertises that scope — both true here, since
Keycloak lists `offline_access` in `scopes_supported` in every realm. This realm
issues rotating refresh tokens with zero reuse, so the append asks for something
it will not get.

**One Person is the exception, and it is this one.** #93 granted Priya Raman the
`offline_access` role so Claude Code — which requests the scope unconditionally
and offers no way to turn it off — can be recorded driving this server;
`docs/adr/0007-the-realm-is-the-exhibit.md` §Token lifetimes argues it. This run
logs in as her, so the exception and this client meet. It changes nothing here:
the append is what `GRANT_TYPES` above declines to trigger, so the request this
run sends carries the three capability scopes and no fourth, whoever holds what.
**Adding `refresh_token` to the list above would now succeed for her rather than
fail**, which is a worse outcome than the failure this docstring was written
against — it would issue an offline token inside the run that captures the
exhibit's transcripts, silently.

**And it does not degrade into a narrowing, which is the part worth recording.**
Keycloak refuses an unentitled `offline_access` at the token endpoint outright —
`not_allowed: Offline tokens not allowed for the user or client` — rather than
omitting it from the grant the way a role scope mapping omits `erp.decide`. So
the RFC 6749 §3.3 behaviour this run exists to observe is real but not general,
and a client that asked anyway would fail at the last step of the flow for a
reason that has nothing to do with what it was demonstrating.
"""

JSON_MEDIA_TYPE: Final = "application/json"
"""What RFC 6749 §5.1 requires a token response to be, and what :meth:`Flow._record` gates on."""

EVENT_STREAM_MEDIA_TYPE: Final = "text/event-stream"
"""What a request naming it in `accept` is prepared to read, and :class:`Unhurried` gates on."""

TIMEOUT: Final = 30.0
"""How long a wait may take. Four things, one number, and one wait deliberately exempt.

**The three requests.** A form post, the preflight fetch, a tool call. For each
of those it is the whole request — all four waits, connect through read — and it
is one number rather than three because none of the three is slow for a reason
of its own: everything here talks to a container on the same machine or to a
static file, so anything approaching this is stuck rather than busy.

**One of the three is not a request `httpx2` resolves a timeout for**, which is
why :class:`Unhurried` applies this number rather than only lifting a wait off
it. `AsyncClient.send` stamps the client's waits onto the request it is handed
and onto nothing else, and the form post is not that request: the package's auth
flow *yields* it, freshly constructed, and `_send_handling_auth` passes it
straight to the transport. Same for the discovery `GET`s that precede it. A
request that arrives carrying no waits is unbounded on every one of them — so
until this became a rule the transport enforces, the token exchange named above
was the one request here with no timeout of any kind, and the discovery chain in
front of it had none either.

**And the fourth thing, which is not a request.** The same number reaches the
long-lived `GET` stream `streamable_http` opens for server-initiated messages,
through the same client :func:`connect` hands the package — and there the
argument above stops holding for exactly one of the four waits. A stream that is
healthy and simply quiet is *idle*, which is the state *stuck rather than busy*
has no name for. Its connect, write and pool waits are still bounded by this
number — a stream that will not open, or a pool that will not lend a connection,
is stuck in the ordinary way — and :class:`Unhurried` lifts the **read** wait
off it alone.

That is also what keeps the fix a statement about requests. A second constant on
the client would have moved the tool call's read wait along with the stream's,
and the tool call is one of the three this number is *for*.

**Whether that stream is opened at all is the server's to decide, and against
this one it is not.** `get_stream_removed` is this repository's own name for
why — the modern leg answers a version-bearing `GET` with `405`, and the stream
that row keeps out of the modern era is the legacy leg's. This client negotiates
the modern one, so the package never starts the stream: it starts on the
`initialized` notification and abandons it without an `Mcp-Session-Id`, and
`server/discover` sends the first no more than this server sends the second.
**Every site that repeats this points here rather than restating it**, because
one server upgrade would falsify it everywhere at once.

That is a fact about which era is negotiated rather than a property of either
constant, and it is why
[#86](https://github.com/marcosfsousa/mcp-erp/issues/86) was found by reading. A
green flow says nothing about this number in either direction; what was wrong
with it was that it enumerated three things and governed four.
"""

CONSENT = "consent"
"""The second form, and the one ADR-0012 warned would be discovered on the day."""

LOGIN = "login"
"""The first form. Recorded, with :data:`CONSENT`, on :attr:`Flow.posted`.

ADR-0012 called the consent post *"a build step not to discover on the day"*, and
a run that silently skipped it would still end in a token — Keycloak remembers a
grant, and only an empty database on every boot makes first-consent the
deterministic path. So the run asserts that both were posted rather than
inferring it from the token that came back.
"""


UNATTRIBUTED: Final = (
    "the authorization server's response is not attributed to the issuer this client "
    "redirected to, so what it says is not repeated here"
)
"""What an unattributable refusal is reported as — and the whole of what is reported.

The specification's authorization-response rules and RFC 9207 §2.4 put a client
under a `MUST NOT` to *"act on or display error, error_description, or
error_uri"* from a response it has not attributed to the authorization server it
redirected to, and repeating those words to a caller is displaying them. So this
sentence is a fixed string with nothing of the response in it, and
:meth:`Flow._callback` decides between it and the server's own words rather than
deciding whether to say anything.

It names the reason that is actually true. A client that reported the other
server's `error` would send a reader to debug a request this client never made,
which is the failure `mixup_iss_mismatch` exists to describe.
"""


class PreflightFailure(RuntimeError):
    """The published document did not answer as committed.

    A named exception rather than an assertion, because its whole purpose is to
    be attributable: everything it reports is **outside this repository's
    running code** — GitHub Pages, egress from the runner, or a document whose
    bytes are no longer the committed ones.
    """


def preflight(*, timeout: float = TIMEOUT) -> str:
    """Fetch the hosted document and refuse anything but the committed bytes.

    Redirects are deliberately **not** followed. The `client_id` is the URL, so
    a document served from somewhere else is a different client wearing this
    one's identifier — the substitution ADR-0008 spends its argument preventing.
    A `301` here is a finding, not a hop.

    Returns:
        The SHA-256 digest of the body, hexadecimal, which equals the digest of
        the committed file.

    Raises:
        PreflightFailure: The document is unreachable, did not answer `200`, or
            does not hash to the committed copy.
    """
    committed = hashlib.sha256(DOCUMENT.read_bytes()).hexdigest()

    try:
        response = httpx2.get(CLIENT_ID, timeout=timeout, follow_redirects=False)
    except httpx2.HTTPError as unreachable:
        raise PreflightFailure(f"{CLIENT_ID} could not be fetched: {unreachable}") from unreachable

    if response.status_code != httpx2.codes.OK:
        raise PreflightFailure(f"{CLIENT_ID} answered {response.status_code}, expected 200")

    served = hashlib.sha256(response.content).hexdigest()
    if served != committed:
        raise PreflightFailure(
            f"{CLIENT_ID} serves {served}, and {DOCUMENT.name} hashes to {committed}"
        )

    return served


class Rebased(httpx2.AsyncBaseTransport):
    """The transport that moves an address without moving an identity.

    The protocol package resolves the authorization server from the protected
    resource metadata document and then requests **exactly** the endpoints it
    discovers. That is correct of it and leaves no hook: `tokens.py` can rebase
    because it builds its own requests, and this client cannot because it does
    not build them.

    So the rebase moves down to where it belongs. A transport rewrites transport
    — the host a connection is opened to, and the `Host` header that names it —
    and nothing above it changes: the issuer in the discovered metadata, the
    `iss` on the redirect and the `iss` claim in the token are all still the
    seed's, and the package compares them itself under RFC 9207 and SEP-2468.

    Inert unless `KEYCLOAK_BASE_URL` names something other than the issuer's own
    origin, which is the ordinary case.

    **It is not a general replacement for :func:`rebase`, and the form-driving
    client must still call that.** A transport sees a request after the cookie
    jar has already read its host to decide what to send, so a request built
    against the issuer's name and rewritten down here would be sent without the
    session cookies Keycloak set under the address it was actually reached at —
    and the flow would die at the login post with *Restart login cookie not
    found*, which reads like a rejected password. Requests this client builds are
    therefore rebased where they are built; this exists for the ones it does not
    build.
    """

    def __init__(self, *, origin: str, onto: str) -> None:
        """Prepare a transport that rewrites one origin onto another.

        Args:
            origin: The scheme and authority the discovered endpoints carry —
                the issuer's, which is identity and never moves.
            onto: The scheme and authority the requests actually go to.
        """
        self._origin = origin
        self._onto = urlparse(onto)
        self._inner = httpx2.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Send one request, on the rewritten address when the origin matches."""
        if f"{request.url.scheme}://{request.url.netloc.decode('ascii')}" == self._origin:
            request.url = request.url.copy_with(
                scheme=self._onto.scheme, host=self._onto.hostname, port=self._onto.port
            )
            request.headers["host"] = self._onto.netloc

        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        """Close the transport underneath."""
        await self._inner.aclose()


class Unhurried(httpx2.AsyncBaseTransport):
    """The transport that lets a stream be quiet without letting a request be slow.

    A timeout reaches `httpx2`'s transports as four separate waits — connect,
    read, write and pool — in `request.extensions`, which is the last place any
    of them can still be told apart. :data:`TIMEOUT` is the right number for all
    four of them on every request this client makes, with one exception this
    exists for: the read wait on the long-lived `GET` stream the protocol package
    opens, where *nothing has arrived for thirty seconds* describes a healthy
    idle stream exactly as well as it describes a stuck one.

    So the read wait is lifted off that request and nothing else changes. **Not
    raised to a larger number**, because a larger number would be the same claim
    with a different threshold: there is no length of quiet that means a stream
    is broken, which is why the package's own reconnect loop is driven by the
    stream ending or erroring rather than by a clock. Nothing waits on this
    stream either — it carries server-initiated messages, no assertion is
    blocked on one, and :func:`connect` cancels the task on the way out — so an
    unbounded read cannot become a run that hangs.

    **What it gives up, since a rule should state its cost beside its argument.**
    The read wait is the only thing on this stream that would ever notice a peer
    going away without saying so. A half-open connection — the server's process
    gone, its host dropped, a middlebox having discarded the state — reads
    exactly like a healthy quiet one, and with no wait nothing distinguishes
    them: the stream stays open until the run ends, and a server-initiated
    message sent over it is lost with no error raised anywhere. That is accepted
    rather than mitigated, on the ground above — nothing is waiting on those
    messages, so what is lost is a notification nobody read. It stops being
    acceptable the day something here blocks on this stream, which is the change
    that should bring this paragraph back up for argument.

    **This also has to supply the waits, not only adjust them.** `AsyncClient`
    resolves its timeout onto the request it is *handed* and onto no other:
    `send` stamps the extension once, and the requests an `httpx2.Auth` yields
    are constructed by the auth flow and passed to the transport without ever
    going through it. Those arrive here with no `timeout` extension at all, which
    `httpcore` reads as *no wait on anything* — so the discovery chain and the
    token form post were unbounded on all four waits while the constant beside
    them said otherwise. Applying the number here is what makes it one rule about
    requests rather than a claim that holds for whichever of them the client
    happened to build.

    **The stream exemption is a rule with nothing to apply to today**, and
    deliberately kept anyway. :data:`TIMEOUT` records which era this server
    negotiates and why no such stream is opened under it. What the rule buys is
    that the constant beside it is true, rather than a number whose docstring
    stops describing it on the day something opens one.

    **The stream is recognised by what the request declares it will read.** A
    `GET` whose `accept` names `text/event-stream` is opening one; discovery
    `GET`s carry a protocol version and no such `accept`, and the `POST`s are
    requests whatever they are answered with. That is the same structural gate
    :meth:`Flow._record` uses on the way back, and for the same reason: it does
    not require this client to know which request the package was making.

    So it covers the resumption `GET` as well as the long-lived one, which is
    right rather than incidental: a resumed stream is the same wait, quiet for
    the same reasons, and a rule that had excluded it would have been a rule
    about an address instead.
    """

    def __init__(self, inner: httpx2.AsyncBaseTransport, *, timeout: float = TIMEOUT) -> None:
        """Wrap the transport that actually sends.

        Args:
            inner: What sends the request once the waits have been decided —
                :class:`Rebased` here, since the address still has to be right.
            timeout: What to bound a request with when it arrives carrying no
                waits of its own. The same number :func:`protocol_client` gives
                the client, passed a second time because the client cannot give
                it to a request it never built.
        """
        self._inner = inner
        self._waits = httpx2.Timeout(timeout).as_dict()

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Send one request, bounded by the waits it carries, with a stream's read lifted."""
        waits = request.extensions.get("timeout")
        if not isinstance(waits, dict):
            waits = self._waits

        if _opens_a_stream(request):
            waits = {**waits, "read": None}

        request.extensions = {**request.extensions, "timeout": waits}

        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        """Close the transport underneath."""
        await self._inner.aclose()


def _opens_a_stream(request: httpx2.Request) -> bool:
    """Whether this request opens a stream rather than being one of the requests around it."""
    accept = request.headers.get("accept", "")

    return request.method == "GET" and EVENT_STREAM_MEDIA_TYPE in accept


@dataclass
class Wallet:
    """Where one flow's tokens and client record live, and nowhere else.

    The protocol package asks for a `TokenStorage`, and every implementation of
    one is a decision about persistence. This one keeps nothing past the process,
    for the reason `tokens.py`'s cache keeps nothing past the run: Keycloak
    re-imports from an empty in-memory database on every boot, so a token cannot
    outlive the authorization server that issued it and a stored one would be
    signed by keys that no longer exist.

    It is also what makes the run honest about consent. A client record that
    survived would let a second run reuse a grant instead of posting the consent
    form again, and the assertion that both forms were posted would start passing
    on history.
    """

    tokens: OAuthToken | None = None
    client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        """The tokens this flow has earned so far, which is none until it has."""
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        """Keep what the token endpoint answered with."""
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        """The client record, which under a hosted document is never a registration."""
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        """Keep the record the package built from the document URL."""
        self.client_info = client_info


class Flow(httpx2.Auth):
    """One authorization code flow, performed headlessly — and the record of it.

    **The auth object and the observation are one object on purpose.** ADR-0008
    makes the auth object the entire difference between this client and a
    pre-minted token, so anything the run needs to assert about the flow has to
    travel on it or :func:`connect` grows a second parameter and the claim stops
    being literally true.

    What it wraps is the package's own `OAuthClientProvider`, which performs
    discovery, the Client Identity Metadata Document path, Proof Key for Code
    Exchange and the token exchange. What it adds is a browser that is not one —
    :meth:`_open` posts the login form and the consent form — one reading taken
    off the wire on the way past, and, since #92, the whole conversation kept on
    :attr:`exchanges` for the transcripts ADR-0014 commits.

    **The `scope` response parameter is read here because it is unreadable
    afterwards.** RFC 6749 §3.3 puts a `MUST` on the authorization server to send
    it when the granted scope differs from the requested one, and the package
    conformantly fills an absent one in from what it asked for (RFC 6749 §5.1),
    which erases the distinction this run exists to observe. Wrapping the auth
    flow sees the token response before that happens, and uses only public
    API — a package that renamed something internal would leave
    :attr:`reported` at `None`, which fails the assertion rather than quietly
    weakening it.
    """

    def __init__(self, username: str, *, timeout: float = TIMEOUT) -> None:
        """Prepare a flow for one Person, without performing anything yet.

        Args:
            username: What the Person types at the login form — `priya.raman`,
                not the subject. The subject is what comes back in the token.
            timeout: How long any one of the three form requests may take.
        """
        self.username = username
        self.posted: list[str] = []
        """Every form this flow posted, in order — `login`, then `consent`.

        **Every** form, not the last flow's: it accumulates if the client
        authorizes twice in one process. That is the record being honest rather
        than a leak to reset. One earned grant is what a run performs — the
        wallet holds the token, so a second `401` means something reauthorized —
        and an assertion of `[login, consent]` that quietly tolerated a second
        pair would be hiding exactly that.
        """

        self.reported: str | None = None
        """The token response's own `scope` parameter, verbatim, or `None`."""

        self.exchanges: list[Exchange] = []
        """Every exchange this flow saw, in the order it saw them.

        **Snapshots rather than the live objects**, and that is not tidiness:
        `httpx2` reuses one `Request` across an authenticated retry — the auth
        flow sets `Authorization` on the very request the `401` came back from —
        so a record holding the object would render a credential that request
        never carried. Found by reading a capture that showed exactly that.

        ADR-0014 makes the captured transcripts an artifact class of their own —
        *"a run writes them, a committed copy is what the write-up includes, and
        a check refuses a diff"* — and this is the record they are written from.
        It travels on the auth object for the reason :attr:`posted` and
        :attr:`reported` do: the auth object is the entire difference between
        this client and a pre-minted token, so what a run needs to say about the
        flow has to travel on it or :func:`connect` grows a second parameter.

        It spans **both** of this module's clients. The form posts arrive through
        :meth:`_seen`, and everything the package sends — discovery, the token
        exchange, and every protocol request afterwards — arrives through
        :meth:`async_auth_flow`, which an `httpx2.Auth` is invited into once per
        request. So the record is the whole conversation rather than the half
        this module happens to build itself.

        Bodies are read on the way past, except an event stream's. Nothing
        assertable depends on the record, so a beat the selectors miss is a
        transcript that does not get written rather than a run that fails —
        which is why `tests/conformance/test_authorization_code_flow.py` asserts
        that each beat found its exchanges before it commits one.
        """

        self.wallet = Wallet()
        self._timeout = timeout
        self._callback_location: str | None = None
        self._provider = OAuthClientProvider(
            server_url=SERVER,
            client_metadata=OAuthClientMetadata.model_validate(
                {**METADATA, "grant_types": GRANT_TYPES}
            ),
            storage=self.wallet,
            redirect_handler=self._open,
            callback_handler=self._callback,
            client_metadata_url=CLIENT_ID,
        )

    @property
    def requested(self) -> frozenset[str]:
        """What the client asked the authorization server for.

        Not ours to choose, and that is the point. The package selects the scope
        from what the resource server publishes — the `WWW-Authenticate`
        challenge first, then `scopes_supported` — so the request is derived from
        this server's own metadata rather than from a list written twice.
        """
        return scope_set(self._provider.context.client_metadata.scope)

    @property
    def discovered_issuer(self) -> str | None:
        """The issuer the package discovered before redirecting, or `None` before it has.

        Read off the provider's own discovery result rather than from a constant
        beside it, for the reason :attr:`requested` gives: what this client
        asserts against has to be what the flow actually found, and a value
        written twice would agree with itself.

        `None` until the authorization server metadata has been fetched — which
        :meth:`_callback` treats as *not attributable*, because that is what it
        is.
        """
        discovered = self._provider.context.oauth_metadata

        return str(discovered.issuer) if discovered is not None else None

    @property
    def granted(self) -> frozenset[str]:
        """What the access token actually carries.

        Read from the token's own claim rather than from the response parameter,
        for the reason `tokens.py` gives: the token is the artifact that is
        definitely authoritative, and whether the response parameter agrees with
        it is the question this run was opened to answer.
        """
        return scope_set(str(self.claims.get("scope", "")))

    @property
    def narrowed(self) -> frozenset[str]:
        """Requested scopes the authorization server declined to grant."""
        return self.requested - self.granted

    @property
    def access_token(self) -> str:
        """The token this flow earned.

        Raises:
            RuntimeError: The flow has not completed, so there is none.
        """
        if self.wallet.tokens is None:
            raise RuntimeError("the flow has not earned a token yet")

        return self.wallet.tokens.access_token

    @property
    def claims(self) -> Mapping[str, Any]:
        """The access token's payload, decoded and **deliberately not verified**.

        The resource server is the party under a `MUST` to verify, and a run
        whose client validated its own token would prove the client.
        """
        return decode_claims(self.access_token)

    async def async_auth_flow(
        self, request: httpx2.Request
    ) -> AsyncGenerator[httpx2.Request, httpx2.Response]:
        """Drive the package's auth flow, reading the token response on the way past."""
        inner = self._provider.async_auth_flow(request)
        outbound = await inner.__anext__()

        while True:
            response = yield outbound
            await self._seen(response)
            await self._record(response)

            try:
                outbound = await inner.asend(response)
            except StopAsyncIteration:
                return

    async def _seen(self, response: httpx2.Response) -> None:
        """Read what came back and keep it on :attr:`exchanges`, or keep it unread.

        **The stream is excluded structurally, not by knowing which request was
        which.** Reading a `text/event-stream` buffers until the server closes
        it, which is a hang rather than a failure — the same hazard
        :meth:`_record` gates on and the same gate, one media type rather than
        the token response's. This server never opens one, for the reason
        :data:`TIMEOUT` records; the gate is here so that stays a fact about the
        era rather than a thing this method assumes.

        A response that arrives already read is left alone: `aread` caches, so
        the second call is the first one's bytes.
        """
        if not response.headers.get("content-type", "").startswith(EVENT_STREAM_MEDIA_TYPE):
            await response.aread()

        self.exchanges.append(snapshot(response))

    async def _record(self, response: httpx2.Response) -> None:
        """Keep the `scope` parameter off a token response, and read nothing else.

        Recognised by the body carrying an `access_token` rather than by the
        address, so the reading does not depend on this client having resolved
        the token endpoint to the same string the package did — under
        :class:`Rebased` it would not have, since a rewritten request no longer
        carries the discovered host.

        **The content-type gate is a safety property, not a shortcut.** Every
        response the client sends passes through here, including the transport's
        own — and `streamable_http` opens a long-lived `text/event-stream` GET
        through the same client. Reading that one buffers until the server closes
        the stream, which is a hang rather than a failure. RFC 6749 §5.1 requires
        a token response to be `application/json`, so gating on it excludes the
        stream structurally rather than by knowing which request was which.
        """
        if response.status_code not in (httpx2.codes.OK, httpx2.codes.CREATED):
            return

        if not response.headers.get("content-type", "").startswith(JSON_MEDIA_TYPE):
            return

        try:
            body = json.loads(await response.aread())
        except ValueError:
            return

        if isinstance(body, dict) and "access_token" in body:
            self.reported = body.get("scope")

    async def _open(self, authorization_url: str) -> None:
        """Be the browser: fetch the authorization request, then log in and consent.

        The package hands over a URL and expects a person to appear at the other
        end of it. What arrives instead is one cookie jar across three requests,
        with redirects followed by hand — the last one **must not** be followed,
        because it points at a callback port nothing is listening on and the code
        is in its `Location` header.
        """
        async with httpx2.AsyncClient(
            follow_redirects=False,
            timeout=self._timeout,
            transport=_reaching_the_issuer(),
            # The other half of :attr:`exchanges`. A response hook rather than a
            # recording transport, because a transport sees a request after the
            # cookie jar has read its host and before the redirect policy has
            # seen the answer — this module already carries one transport that
            # rewrites at that altitude, and a second object there would be a
            # second place the address story lives.
            event_hooks={"response": [self._seen]},
        ) as http:
            page = await _get(http, rebase(authorization_url))
            _keep_the_session_over_plain_http(http)

            answered = await _post(
                http,
                _action_of(page),
                {"username": self.username, "password": PASSWORD, "credentialId": ""},
            )
            self.posted.append(LOGIN)
            _keep_the_session_over_plain_http(http)

            # A rejected password re-renders the login form with a `200`, which
            # the walk below would otherwise post an `accept` to.
            if LOGIN_FORM in answered.text:
                raise RuntimeError(f"the authorization server did not accept {self.username!r}")

            self._callback_location = await self._walk_to_the_callback(http, answered)

    async def _walk_to_the_callback(self, http: httpx2.AsyncClient, page: httpx2.Response) -> str:
        """Follow the authorization server's own steps until one redirects to the client.

        **Consent arrives as a redirect, not as a page.** A logged-in caller who
        has not consented is sent to
        `login-actions/required-action?execution=OAUTH_GRANT`, and the screen is
        what answers *that* — so this is a loop rather than a single `if`, and
        the shape that fails here fails by reporting a missing code rather than a
        missing consent.

        Returns:
            The `Location` of the redirect back to the client.

        Raises:
            RuntimeError: The authorization server kept asking for something. A
                step count rather than a timeout, so a realm that grew a required
                action fails naming the step it stopped on.
        """
        callback = str(METADATA["redirect_uris"][0])

        for _ in range(MAX_AUTHORIZATION_STEPS):
            location: str | None = page.headers.get("location")

            if location is not None and location.startswith(callback):
                return location

            if location is not None:
                page = await _get(http, rebase(location))
            else:
                page = await _post(http, _action_of(page), {"accept": "Yes"})
                self.posted.append(CONSENT)

            _keep_the_session_over_plain_http(http)

        raise RuntimeError(
            f"the authorization server never redirected back to the client; "
            f"stopped at {page.headers.get('location') or page.url}"
        )

    async def _callback(self) -> AuthorizationCodeResult:
        """Hand the redirect's parameters back, repeating a refusal only once it is ours.

        **`state` is still deliberately unchecked, and so is `iss` on the way
        through.** The package generated the `state` and compares it itself with
        a constant-time comparison, and it validates the RFC 9207 `iss` against
        the issuer it discovered. Re-checking either on the success path would be
        this client marking its own homework.

        **The error path is not covered by that argument, because the package
        never reaches it.** `AuthorizationCodeResult` requires a `code`, and a
        refused response carries an `error` and none — so it cannot be expressed
        in the type at all and cannot be handed over, and the party that would
        attribute it never sees it. The `MUST NOT` in :data:`UNATTRIBUTED` is
        therefore this client's own to keep, on the only line where it can be
        kept: the attribution is made here, before :func:`redirect_error` is
        consulted, and it chooses **which** of two things is reported rather than
        whether anything is. `tests/tokens.py`'s `authorization_code` keeps the
        same clause in the same order for the client that module drives, and
        `mixup_iss_mismatch` is the row both answer to.

        **A refusal that names no issuer is not attributed either.** The package
        tolerates an absent `iss` unless the authorization server advertised
        support for it, which is right for a response it can still check other
        ways; here there is nothing else to go on, so absence is not agreement.

        Raises:
            RuntimeError: No redirect arrived; or it carried a refusal — in the
                authorization server's own words when the response is attributed
                to the issuer this flow discovered, and as :data:`UNATTRIBUTED`
                when it is not.
        """
        if self._callback_location is None:
            raise RuntimeError("the authorization server never redirected back to the client")

        query = parse_qs(urlparse(self._callback_location).query)
        attributed = (
            self.discovered_issuer is not None
            and query.get("iss", [None])[0] == self.discovered_issuer
        )

        refusal = redirect_error(self._callback_location)
        if refusal is not None:
            raise RuntimeError(refusal if attributed else UNATTRIBUTED)

        return AuthorizationCodeResult(
            code=query.get("code", [""])[0],
            state=query.get("state", [None])[0],
            iss=query.get("iss", [None])[0],
        )


@dataclass(frozen=True, slots=True)
class Bearer(httpx2.Auth):
    """A token somebody else already minted, presented as the same kind of object.

    The other half of ADR-0008's *"mint versus earn is a constructor argument"* —
    and the half that makes the claim falsifiable, because :func:`connect` runs
    the same protocol conversation against the same server with this in place of
    :class:`Flow` and nothing else changes.
    """

    access_token: str

    def auth_flow(self, request: httpx2.Request) -> Generator[httpx2.Request, httpx2.Response]:
        """Present the token, once, and read no response."""
        request.headers["authorization"] = f"Bearer {self.access_token}"
        yield request


@asynccontextmanager
async def connect(auth: httpx2.Auth) -> AsyncIterator[Client]:
    """The whole client, over Streamable HTTP, authenticated by exactly one object.

    This is the library surface ADR-0008 describes and the runnable entry point
    below uses unchanged. It takes an `httpx2.Auth` and knows nothing else about
    it: `mcp` 2.0.0's unified `Client` takes no authentication parameter, so
    authentication attaches to the HTTP client underneath the transport, and
    *connect, call, assert* is identical whichever object is attached.

    Args:
        auth: :class:`Flow` to earn a token through the hosted document, or
            :class:`Bearer` to present one already minted.

    Yields:
        A connected client, with the protocol era already negotiated.
    """
    async with protocol_client(auth) as http:
        # The transport is handed over unentered: `Client` owns its lifetime, and
        # entering it here would hand `Client` a pair of streams instead.
        async with Client(streamable_http_client(SERVER, http_client=http)) as client:
            yield client


def protocol_client(auth: httpx2.Auth, *, timeout: float = TIMEOUT) -> httpx2.AsyncClient:
    """The HTTP client the protocol package is handed, and the waits it carries.

    A function rather than four lines inside :func:`connect`, because the waits
    are the one thing about this object that a completed flow does not
    demonstrate — :class:`Unhurried`'s exemption and the bound either side of it
    both end in a run that passes. `tests/test_conformance_client.py` builds this
    same client with a small `timeout` and drives it against a socket, which is
    what makes *the stream is exempt and the requests are not* an assertion.

    Public for that module, which is the shape sharing takes here when it can be
    taken, and it does not make :func:`connect` any less the surface ADR-0008
    describes: this returns the client rather than a connected one, and nothing
    that speaks the protocol comes out of it.

    Args:
        auth: What authenticates every request the package makes.
        timeout: What bounds each of them — every wait on every request, except
            the read wait on the long-lived `GET` stream. Given twice on
            purpose: the client resolves it for the requests it builds, and
            :class:`Unhurried` applies it to the ones `auth` yields, which the
            client never sees.
    """
    return httpx2.AsyncClient(
        auth=auth,
        timeout=timeout,
        transport=Unhurried(_reaching_the_issuer(), timeout=timeout),
    )


def _keep_the_session_over_plain_http(http: httpx2.AsyncClient) -> None:
    """Clear `Secure` on the session cookies, because this exhibit runs on plain HTTP.

    The measurement, the reasoning and why relaxing the *policy* does not work
    are all in `tokens.py`'s function of the same name, and are not restated
    here. What is worth stating is that this is a second copy rather than a
    shared one: that helper takes an `httpx.Client` and this takes an
    `httpx2.AsyncClient`, and the two packages are both in this environment
    deliberately — the 2.x line is what the protocol package carries, and the
    0.x line belongs to the fixture minter.

    Verified rather than assumed to carry over: `httpx2` rebuilds the jar per
    request the same way — `Cookies(self.cookies)` copies each cookie into a
    fresh `CookieJar()` with the default policy — so the flag has to be cleared
    on the `Cookie` objects, which survive that copy by reference.
    """
    for cookie in http.cookies.jar:
        cookie.secure = False


def _reaching_the_issuer() -> Rebased:
    """The transport both of this module's clients open, built the one way.

    Two clients rather than one is not a choice: the forms need their own cookie
    jar and their own redirect policy, and the protocol package owns the other.
    What they must not differ on is *where the authorization server is*, and a
    pair of constructor calls is a pair of places for that to stop being true.
    """
    return Rebased(origin=ISSUER_ORIGIN, onto=KEYCLOAK_BASE_URL)


def _action_of(response: httpx2.Response) -> str:
    """Where a page's form posts to, absolute and reachable.

    The two forms differ, and only one of them says so: the login form's action
    is absolute and carries the *issuer's* host, while the consent form's is a
    bare path. Resolving against the page's own URL handles both.
    """
    return rebase(urljoin(str(response.url), form_action(response.text)))


async def _get(http: httpx2.AsyncClient, url: str) -> httpx2.Response:
    """One GET, with the authorization server's own words on a failure."""
    response = await http.get(url)
    if response.status_code >= httpx2.codes.BAD_REQUEST:
        raise RuntimeError(f"GET {url} answered {response.status_code}: {response.text}")

    return response


async def _post(http: httpx2.AsyncClient, url: str, data: dict[str, str]) -> httpx2.Response:
    """One form post, raising with the server's own body on a `4xx` or `5xx`.

    A `302` is the expected answer at both posts and is left alone; the redirect
    *is* the result, and following it would fetch a callback URL nothing serves.
    """
    response = await http.post(url, data=data)
    if response.status_code >= httpx2.codes.BAD_REQUEST:
        raise RuntimeError(f"POST {url} answered {response.status_code}: {response.text}")

    return response


async def _run(username: str) -> int:
    """Perform the flow, call one tool, and print what the wire said."""
    flow = Flow(username)

    async with connect(flow) as client:
        listed = await client.list_tools()

    print(f"client_id   {CLIENT_ID}")
    print(f"posted      {' then '.join(flow.posted)}")
    print(f"issuer      {flow.claims.get('iss')}")
    print(f"subject     {flow.claims.get('sub')}")
    print(f"audience    {flow.claims.get('aud')}")
    print(f"authorized  {flow.claims.get('azp')}")
    print(f"requested   {' '.join(sorted(flow.requested))}")
    print(f"granted     {' '.join(sorted(flow.granted))}")
    print(f"reported    {flow.reported!r}")
    if flow.narrowed:
        print(f"declined    {' '.join(sorted(flow.narrowed))}")
    print(f"tools       {' '.join(sorted(tool.name for tool in listed.tools))}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the preflight, or the whole flow, from a command line.

    Two modes rather than two commands, because they are two halves of one job
    and the continuous-integration job runs them in this order — the preflight
    before `docker compose up`, the flow after it::

        uv run python tests/conformance_client.py --preflight
        uv run python tests/conformance_client.py priya.raman
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("username", nargs="?", help="the login name, e.g. priya.raman")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="only check that the hosted document answers as committed, and stop",
    )
    arguments = parser.parse_args(argv)

    if arguments.preflight:
        print(f"{CLIENT_ID}\n{preflight()}  matches {DOCUMENT.name}")
        return 0

    if arguments.username is None:
        parser.error("a username is required unless --preflight is given")

    preflight()

    return asyncio.run(_run(arguments.username))


if __name__ == "__main__":
    sys.exit(main())

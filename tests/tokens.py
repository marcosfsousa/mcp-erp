"""The token helper: one authorization code flow, per Person and scope set, cached.

ADR-0008 asked for this to be built *"once and deliberately"* — both proof
artifacts depend on it, and it is the piece most likely to become slow and
duplicated if it grows organically. So it is one module, above all four test
directories rather than inside any of them, because shared tooling that lives in
one artifact's directory becomes that artifact's and gets copied by the next.

**It performs the real flow.** ADR-0007 disables direct access grants on every
client and asserts the refusal, so there is no shortcut to a token: the helper
requests an authorization code with Proof Key for Code Exchange, posts
Keycloak's login form, posts its consent form, and redeems the code. That is the
same sequence the conformance client performs — the difference is that the
client under test earns its token through a hosted identity document while this
mints one for a suite, which ADR-0008 calls *"a constructor argument, not an
architecture"*.

**Nothing here validates a token.** The claims are decoded, never verified. The
resource server is the party under a `MUST` to verify, and a suite whose
fixtures validate their own tokens proves the fixture.

**Two addresses, one identity.** The issuer is `http://keycloak:8081/...` and it
is what every token says and what the principal directory joins on. That name
resolves inside the Compose network by Compose's own DNS; outside it, it needs
one `127.0.0.1 keycloak` line in the host's hosts file, which ADR-0005 priced
and accepted. A reader who has not added that line can point the helper
somewhere reachable instead::

    KEYCLOAK_BASE_URL=http://localhost:8081

The issuer does not move when that does — only the address the requests go to.
The helper asserts that the metadata it discovers still names the issuer, so a
rebased run cannot quietly become a run against a different authorization
server.

Standalone, which is #36's own acceptance criterion — mint a token, decode it,
confirm subject and granted scopes::

    uv run python tests/tokens.py priya.raman erp.read erp.write
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from mcp_erp.authorization.identity import SEED, read_identity_seed

REPO = Path(__file__).parents[1]

_SEED = read_identity_seed((REPO / SEED).read_text(encoding="utf-8"))

ISSUER = _SEED.issuer
"""What every token minted here says, and what the principal directory joins on."""

REALM = _SEED.realm
"""The realm the Cast lives in, derived from the issuer rather than authored twice."""

NEIGHBOUR_REALM = f"{REALM}-neighbour"
"""The second issuer, for a token that is perfect except for who minted it."""

PASSWORD = _SEED.password
"""One conspicuously fake password, shared by the whole Cast."""

REALMS_ROOT = ISSUER.rsplit("/", 1)[0]
"""Everything in the issuer up to the realm name, so a second realm is not a second parse."""

ISSUER_ORIGIN = REALMS_ROOT.rsplit("/realms", 1)[0]
"""The issuer's scheme and authority — the half `KEYCLOAK_BASE_URL` replaces."""

BASE_URL = os.environ.get("KEYCLOAK_BASE_URL", ISSUER_ORIGIN).rstrip("/")
"""Where the requests actually go. Identity is the issuer; this is transport.

Normalised once, here. :func:`rebase` both compares against this value and
substitutes it, and a trailing slash surviving into only one of the two would
make every rebase a no-op — quietly, by sending the requests to the issuer's own
host, which is the address the override exists because a reader cannot reach.
"""

REDIRECT_URI = "http://localhost:8085/callback"
"""Registered on every client, and never served.

The authorization server validates a redirect URI against its registration and
then answers with a `302`. Reading the code out of that `Location` header means
the helper needs no listener, no thread and no free port — and it is why a
callback URL that nothing answers at is not a defect here.
"""

CONFORMANCE_CLIENT = "mcp-conformance"
"""The client every normal mint goes through."""

NEIGHBOUR_CLIENT = "mcp-neighbour"
"""The neighbour realm's only client.

Named because the two realms share no clients at all — they are separate
issuers, not two views of one — so a caller who changes the realm and not the
client gets `invalid_client`.
"""

MAX_AUTHORIZATION_STEPS = 8
"""How many redirects and forms the flow may take before the helper gives up.

A count rather than a timeout, so a realm that grew a required action fails
naming the step it stopped on instead of hanging. Four is the shape today —
login post, redirect to the grant step, the consent screen, the redirect home.
"""

LOGIN_FORM = "kc-form-login"
"""Keycloak's own identifier for the login form, and the only way to tell it apart.

A rejected password re-renders that form with a `200` — the same status the
consent screen arrives with — so the page has to be distinguished by what is on
it rather than by what the response says.
"""

_CACHE: dict[tuple[str, str, str, frozenset[str]], Minted] = {}
"""Minted tokens, keyed by everything that changes one.

Cached *within a run* and no longer: the realm is re-imported from an empty
database on every boot, so a token cannot outlive the Keycloak that issued it
and a cache that survived the process would hand a suite a token signed by keys
that no longer exist.
"""


@dataclass(frozen=True, slots=True)
class Minted:
    """One access token, with the two things a caller asserts against.

    Attributes:
        access_token: The token itself, for an `Authorization: Bearer` header.
        refresh_token: The refresh token, which rotates with zero reuse — so
            redeeming it twice revokes the grant, which `refresh_token_replay`
            is the assertion of.
        claims: The access token's payload, decoded and **not verified**.
        requested_scopes: What the client asked for.
        granted_scopes: What the token carries. The two differ whenever a role
            scope mapping declines a scope, which Keycloak does silently — the
            gap RFC 6749 §3.3 obliges the authorization server to report, and
            which ADR-0012 left as an open verification item.
    """

    access_token: str
    refresh_token: str | None
    claims: Mapping[str, Any]
    requested_scopes: frozenset[str]
    granted_scopes: frozenset[str]

    @property
    def subject(self) -> str:
        """The `sub` claim — the half of the directory key the token carries."""
        subject = self.claims.get("sub")
        if not isinstance(subject, str):
            raise ValueError(f"token carries no subject claim: {self.claims!r}")
        return subject

    @property
    def narrowed(self) -> frozenset[str]:
        """Requested scopes the authorization server declined to grant."""
        return self.requested_scopes - self.granted_scopes


def mint(
    username: str,
    scopes: Iterable[str] = (),
    *,
    client_id: str = CONFORMANCE_CLIENT,
    realm: str = REALM,
) -> Minted:
    """Mint an access token for one Person and one scope set, or return the cached one.

    Args:
        username: What the Person types at the login form — `priya.raman`, not
            the subject. The subject is what comes back in the token, and
            asserting on it is half of what a caller does with the result.
        scopes: The capability scopes to request. `openid` is added, because a
            realm without it answers the authorization request with a login page
            and no code.
        client_id: Which of ADR-0007's clients performs the flow. The default is
            the one with our audience and a five-minute token; the others exist
            to make a specific refusal reachable.
        realm: Which issuer mints it. The neighbour realm is the whole of what
            makes a foreign-issuer token real rather than invented.

    Returns:
        The minted token, its decoded claims, and both scope sets.

    Raises:
        RuntimeError: The authorization server refused a step, with what it said.
    """
    key = cache_key(realm, client_id, username, scopes)

    if key not in _CACHE:
        _CACHE[key] = _perform(username, key[3], client_id=client_id, realm=realm)

    return _CACHE[key]


def cache_key(
    realm: str, client_id: str, username: str, scopes: Iterable[str]
) -> tuple[str, str, str, frozenset[str]]:
    """Everything that changes a token, and nothing that does not.

    A named function rather than a tuple built inline, because both halves of
    what #36 asks for live in it. A key that varies with the *order* scopes were
    written in mints twice for one token, which is the slow half and never shows
    up as a failure. A key that fails to vary with the Person or the client
    hands a suite somebody else's token, which is the duplicated half and shows
    up as a row passing for the wrong reason.

    `openid` joins the set here, so the key matches what is actually requested:
    a realm without it answers the authorization request with a login page and
    no code.
    """
    return (realm, client_id, username, frozenset(scopes) | {"openid"})


def default_client_for(realm: str) -> str:
    """The client to use when the caller named a realm and no client.

    Two realms, one client each worth defaulting to. Anything else is a
    deliberate choice — the decoy, the bare client and the expiry probe all
    exist to make one specific refusal reachable, so none of them is what a
    caller who said nothing meant.
    """
    return NEIGHBOUR_CLIENT if realm == NEIGHBOUR_REALM else CONFORMANCE_CLIENT


def metadata(realm: str = REALM) -> Mapping[str, Any]:
    """The authorization server metadata, discovered path-inserted.

    RFC 8414 §3 inserts the well-known segment between host and path rather than
    appending it, and ADR-0005 verified that Keycloak serves the
    `oauth-authorization-server` form and deliberately 404s the OpenID Connect
    one. This is the same address the resource server discovers through, so a
    helper that could not reach it is a helper testing a different server.

    Raises:
        RuntimeError: The document names an issuer other than the one the seed
            declares, which means the realm and the renderings have come apart.
    """
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        response = http.get(f"/.well-known/oauth-authorization-server/realms/{realm}")
        response.raise_for_status()
        document: Mapping[str, Any] = response.json()

    expected = f"{REALMS_ROOT}/{realm}"
    if document.get("issuer") != expected:
        raise RuntimeError(f"discovered issuer {document.get('issuer')!r}, expected {expected!r}")

    return document


def challenge_for(verifier: str) -> str:
    """The `S256` code challenge for one verifier, unpadded as RFC 7636 §4.2 requires."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()

    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def refused_authorization_response(realm: str, client_id: str) -> tuple[str, str]:
    """One real authorization error response, and the issuer that produced it.

    Obtained by asking for the weak challenge method, which ADR-0007 pins per
    client — so the authorization server answers with a redirect carrying
    `error`, `error_description` and, per RFC 9207, `iss`. An honest server
    refusing an honest question, which is exactly the document a mix-up attack
    puts in front of the wrong client: nothing about it is forged, and the only
    thing that makes it unreadable to a client is who it came from.

    **Shared rather than copied, because two rows need the same document.**
    `mixup_iss_mismatch` hands it to this module's own client and
    `tests/conformance/` hands it to the conformance client — the two clients
    this project authors, under the same `MUST NOT` — and a second definition
    would let the two assert about responses that had quietly stopped being
    alike.

    Args:
        realm: Which issuer refuses. Named rather than defaulted, because the
            point of the row asking for this is usually that it is **not** the
            realm the client under test redirected to.
        client_id: A client registered in that realm. The two realms share none,
            so a caller who changes one and not the other gets `invalid_client`
            instead of the refusal this exists to produce.

    Returns:
        The redirect's `Location`, and the issuer the realm declares.

    Raises:
        RuntimeError: The authorization server answered something other than a
            redirect, which means it refused the request itself rather than
            refusing through one — a different document from the one asked for.
    """
    document = metadata(realm)

    with httpx.Client(follow_redirects=False, timeout=30.0) as http:
        answer = http.get(
            rebase(str(document["authorization_endpoint"])),
            params={
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": REDIRECT_URI,
                "scope": "openid erp.read",
                "state": secrets.token_urlsafe(16),
                "code_challenge": challenge_for(secrets.token_urlsafe(64)),
                "code_challenge_method": "plain",
            },
        )

    if answer.status_code != httpx.codes.FOUND:
        raise RuntimeError(
            f"the authorization server answered {answer.status_code} rather than "
            f"redirecting with a refusal: {answer.text}"
        )

    return str(answer.headers["location"]), str(document["issuer"])


def form_action(html: str) -> str:
    """The `action` of the first form on a page, with its HTML entities resolved.

    Keycloak's login action carries `execution` and `tab_id` query parameters
    that arrive escaped, and posting the raw attribute sends `&amp;` inside a
    parameter value — which the authorization server answers by re-rendering the
    form, so the failure looks like a rejected password.

    Raises:
        ValueError: The page has no form, which is what an error page looks
            like from here.
    """
    match = re.search(r"<form[^>]*\saction=(\"|')(.*?)\1", html, flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        raise ValueError("no form on the page returned by the authorization server")

    return match.group(2).replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')


def redirect_error(location: str) -> str | None:
    """The authorization server's own words when a redirect carries a refusal, or `None`.

    Separate from :func:`authorization_code` because the two questions have
    different owners. Whoever generated `state` is the party that can check it,
    and the conformance client does not: it hands the redirect to the protocol
    package, which generated the value and compares it itself (#46). *Was this
    refused, and in what words* has no such owner — it is the same question from
    both sides, and reading it twice is how a refusal becomes a missing code
    three lines later.

    Returns:
        `"<error>: <description>"`, or the bare error where the authorization
        server sent no description, or `None` when the redirect carries neither.
    """
    query = parse_qs(urlparse(location).query)

    if "error" not in query:
        return None

    description = query.get("error_description", [""])[0]

    return f"{query['error'][0]}: {description}".strip(": ")


def authorization_code(location: str, *, expected_state: str, expected_issuer: str) -> str:
    """The `code` from a redirect back to the client, once the response is ours to read.

    Nothing here is a browser, so `state` is not doing the cross-site job it
    exists for. It is checked anyway because it is sent anyway: what it catches
    is the flow crossing wires — a cached redirect, or a session belonging to a
    different mint — which would otherwise surface as a token for the wrong
    Person, three assertions later, in a suite about something else.

    **`iss` is checked first, and the order is the whole of what the mix-up row
    asserts.** RFC 9207 §2.4 and the specification's authorization-response
    rules put a client under a `MUST NOT` to *"act on or display error,
    error_description, or error_uri"* from a response it has not attributed to
    the authorization server it redirected to. An implementation that reads the
    error first is the common shape and it fails exactly here: handed an honest
    server's error response, it reports that server's words as though they
    answered its own request. So the attribution runs before :func:`redirect_error`
    is consulted, and `mixup_iss_mismatch` is the falsifier.

    Args:
        location: The `Location` of the redirect back to the client.
        expected_state: The value sent with the authorization request.
        expected_issuer: The issuer discovered **before** redirecting. Required
            rather than defaulted: a check a caller can omit is a check the next
            caller omits, and the omission is invisible until somebody replays
            another server's response.

    Returns:
        The authorization code.

    Raises:
        ValueError: The response is attributed to another issuer, or carries
            somebody else's `state`; or it carries an `error` instead, reported
            in the authorization server's own words rather than as an absent
            code three lines later.
    """
    query = parse_qs(urlparse(location).query)

    returned_issuer = query.get("iss", [""])[0]
    if returned_issuer != expected_issuer:
        raise ValueError(
            f"redirect is attributed to issuer {returned_issuer!r}, expected {expected_issuer!r}"
        )

    refusal = redirect_error(location)
    if refusal is not None:
        raise ValueError(refusal)

    returned = query.get("state", [""])[0]
    if returned != expected_state:
        raise ValueError(f"redirect carries state {returned!r}, expected {expected_state!r}")

    if "code" not in query:
        raise ValueError(f"no code and no error in redirect: {location!r}")

    return query["code"][0]


def decode_claims(token: str) -> dict[str, Any]:
    """The payload of a JSON Web Token, decoded and deliberately not verified.

    Raises:
        ValueError: The token is not three dot-separated segments, which an
            opaque token would otherwise decode into nonsense.
    """
    segments = token.split(".")
    if len(segments) != 3:
        raise ValueError(f"expected three segments, got {len(segments)}")

    padded = segments[1] + "=" * (-len(segments[1]) % 4)
    claims: dict[str, Any] = json.loads(base64.urlsafe_b64decode(padded))

    return claims


def scope_set(value: str | None) -> frozenset[str]:
    """A `scope` string as the set it denotes.

    RFC 6749 §3.3 makes these space-delimited, case-sensitive strings, so
    nothing here lowercases anything — `scope_exact_match` asserts the same rule
    at the resource server, and a helper that normalised would make that row
    untestable from this side.
    """
    return frozenset((value or "").split())


def _perform(
    username: str,
    requested: frozenset[str],
    *,
    client_id: str,
    realm: str,
) -> Minted:
    """Drive the whole flow once: authorize, log in, consent, redeem.

    One client throughout, because Keycloak's authentication session is a cookie
    and a second client would arrive at the login form as a stranger. Redirects
    are not followed: the redirect *is* the result at two of the three steps
    below.
    """
    document = metadata(realm)
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(16)

    with httpx.Client(follow_redirects=False, timeout=30.0) as http:
        page = _get(
            http,
            rebase(str(document["authorization_endpoint"])),
            params={
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": REDIRECT_URI,
                "scope": " ".join(sorted(requested)),
                "state": state,
                "code_challenge": challenge_for(verifier),
                "code_challenge_method": "S256",
                # Sent although Keycloak ignores it — RFC 8707 §2 asks the
                # client to send it regardless of server support, and register
                # deviation 1 is precisely that this server does not honour it.
                "resource": os.environ.get("MCP_RESOURCE_URL", "http://localhost:8080/mcp"),
            },
        )

        _keep_the_session_over_plain_http(http)

        response = _post(
            http,
            _action_of(page),
            data={"username": username, "password": PASSWORD, "credentialId": ""},
        )
        _keep_the_session_over_plain_http(http)

        # A rejected password re-renders the login form with a `200`, which the
        # loop below would otherwise post an `accept` to.
        if LOGIN_FORM in response.text:
            raise RuntimeError(f"the authorization server did not accept {username!r}")

        location = _walk_to_the_callback(http, response)

        redeemed = _post(
            http,
            rebase(str(document["token_endpoint"])),
            data={
                "grant_type": "authorization_code",
                "client_id": client_id,
                "code": authorization_code(
                    location,
                    expected_state=state,
                    # The issuer discovered before redirecting, which is what
                    # the response has to be attributable to.
                    expected_issuer=str(document["issuer"]),
                ),
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
        )

    payload = redeemed.json()
    access_token = str(payload["access_token"])
    claims = decode_claims(access_token)

    return Minted(
        access_token=access_token,
        refresh_token=payload.get("refresh_token"),
        claims=claims,
        requested_scopes=requested,
        # The token's own claim, not the response parameter. Keycloak omits an
        # unpermitted scope silently, and whether it then reports the narrowing
        # in the response is ADR-0012's open verification item — so the granted
        # set is read from the artifact that is definitely authoritative.
        granted_scopes=scope_set(claims.get("scope")),
    )


def _walk_to_the_callback(http: httpx.Client, response: httpx.Response) -> str:
    """Follow the authorization server's own steps until one redirects to the client.

    **Consent arrives as a redirect, not as a page**, which is why this is a loop
    rather than a single `if`: a logged-in caller who has not consented is sent
    to `login-actions/required-action?execution=OAUTH_GRANT`, and the screen is
    what answers *that*. Treating the login response as either a redirect home
    or the consent page directly is the shape that fails here, and it fails by
    reporting a missing code rather than a missing consent.

    Consent is required on all four clients and the database is empty at every
    boot, so this is always the first-consent path — deterministic rather than
    sometimes-remembered.

    Redirects are followed by hand, rather than by `follow_redirects=True`,
    because the last one must **not** be followed: it points at a callback port
    nothing is listening on, and the code is in its `Location` header.

    Returns:
        The `Location` of the redirect back to the client.

    Raises:
        RuntimeError: The authorization server kept asking for something. The
            bound is a step count rather than a timeout, so a realm that grew a
            required action fails with the address of the step it stopped on.
    """
    for _ in range(MAX_AUTHORIZATION_STEPS):
        location: str | None = response.headers.get("location")

        if location is not None and location.startswith(REDIRECT_URI):
            return location

        if location is not None:
            response = _get(http, rebase(location))
        else:
            response = _post(http, _action_of(response), data={"accept": "Yes"})

        _keep_the_session_over_plain_http(http)

    raise RuntimeError(
        f"the authorization server never redirected back to the client; "
        f"stopped at {response.headers.get('location') or response.url}"
    )


def _action_of(response: httpx.Response) -> str:
    """Where a page's form posts to, absolute and reachable.

    The two forms differ, and only one of them says so: the login form's action
    is absolute and carries the *issuer's* host, while the consent form's is
    a bare path. Resolving against the page's own URL handles both, and the
    rebase afterwards puts the result back on the address these requests can
    reach.
    """
    return rebase(urljoin(str(response.url), form_action(response.text)))


def _keep_the_session_over_plain_http(http: httpx.Client) -> None:
    """Clear `Secure` on the session cookies, because this exhibit runs on plain HTTP.

    **Measured, not assumed.** Keycloak sets `AUTH_SESSION_ID`, `KC_RESTART` and
    `KC_AUTH_SESSION_HASH` with `Secure; SameSite=None`. Verified against 26.7.1
    under an `http://keycloak:8081` hostname *and* under an
    `http://localhost:18081` one, so it is not a consequence of which name the
    issuer carries: `SameSite=None` requires `Secure`, Keycloak needs the former
    for its cross-origin form post, and it emits both whatever the scheme is. It
    says so at boot — *"the server is running in an insecure context. Secure
    contexts are required for full functionality, including cross-origin
    cookies."*

    A conforming jar therefore declines to send them back over `http://`, and
    the flow dies at the login post with *Restart login cookie not found*, which
    reads like a rejected password.

    **The flag is cleared rather than the policy relaxed, and that is not a
    preference.** A `DefaultCookiePolicy` subclass returning true from
    `return_ok_secure` has no effect: httpx rebuilds the jar for every request —
    `Cookies(self.cookies)` copies each cookie into a fresh `CookieJar()` with
    the default policy — so the policy is gone by the time the header is built.
    The `Cookie` objects survive that copy by reference, so clearing the flag on
    them does.

    Browsers never hit any of this, and the exemption is narrower than it looks:
    a browser treats `http://localhost` and `http://127.0.0.1` as trustworthy
    origins and keeps `Secure` cookies for them, deciding on the **name** — so a
    host that merely resolves to a loopback address gets no such pass.

    This is normative register row 2 reaching further than the row states.
    The concession is confined to the client that mints fixtures; nothing the
    exhibit ships makes it.
    """
    for cookie in http.cookies.jar:
        cookie.secure = False


def rebase(url: str) -> str:
    """Point a discovered endpoint at the address these requests can reach.

    A no-op in the ordinary case, where `KEYCLOAK_BASE_URL` is the issuer's own
    origin. It is what lets a reader who has not added the hosts-file line still
    mint a token, and it deliberately rewrites *transport only* — `metadata()`
    has already refused a document naming any issuer but ours, so this cannot
    silently retarget the run.

    **Public because the conformance client shares it** (#46). That client earns
    its token through the protocol package rather than minting one here, and the
    package follows a discovered endpoint verbatim — so the one address a reader
    may need to move has to be movable from both sides by one rule, not two.
    """
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    return url if origin == BASE_URL else url.replace(origin, BASE_URL, 1)


def _get(http: httpx.Client, url: str, *, params: dict[str, str] | None = None) -> httpx.Response:
    """One GET, with the authorization server's own words on a failure."""
    response = http.get(url, params=params)
    if response.status_code >= httpx.codes.BAD_REQUEST:
        raise RuntimeError(f"GET {url} answered {response.status_code}: {response.text}")
    return response


def _post(http: httpx.Client, url: str, *, data: dict[str, str]) -> httpx.Response:
    """One form post, raising with the server's own body on a `4xx` or `5xx`.

    A `302` is the expected answer at two of the three posts and is left alone;
    the redirect *is* the result, and following it would fetch a callback URL
    nothing serves.
    """
    response = http.post(url, data=data)
    if response.status_code >= httpx.codes.BAD_REQUEST:
        raise RuntimeError(f"POST {url} answered {response.status_code}: {response.text}")
    return response


def main(argv: list[str] | None = None) -> int:
    """Mint one token from the command line, decode it, and print what it carries.

    This is #36's *verifiable standalone* criterion, executable::

        uv run python tests/tokens.py priya.raman erp.read erp.write
        uv run python tests/tokens.py tomas.weber erp.read --realm mcp-erp-neighbour

    The client defaults per realm rather than to one name, because the realms
    share no clients: `mcp-conformance` does not exist next door, so a fixed
    default would make the second line above fail with `invalid_client` — a
    message about the client, on a flag the caller never touched.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("username", help="the login name, e.g. priya.raman")
    parser.add_argument("scopes", nargs="*", help="capability scopes to request")
    parser.add_argument("--client-id", default=None, help="defaults to the realm's own client")
    parser.add_argument("--realm", default=REALM)
    parser.add_argument("--token", action="store_true", help="print the raw access token too")
    arguments = parser.parse_args(argv)

    minted = mint(
        arguments.username,
        arguments.scopes,
        client_id=arguments.client_id or default_client_for(arguments.realm),
        realm=arguments.realm,
    )

    print(f"issuer      {minted.claims.get('iss')}")
    print(f"subject     {minted.subject}")
    print(f"audience    {minted.claims.get('aud')}")
    print(f"requested   {' '.join(sorted(minted.requested_scopes))}")
    print(f"granted     {' '.join(sorted(minted.granted_scopes))}")
    if minted.narrowed:
        print(f"declined    {' '.join(sorted(minted.narrowed))}")
    if arguments.token:
        print(f"\n{minted.access_token}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

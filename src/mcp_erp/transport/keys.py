"""Discovery, and the signing keys — refetched on a miss, never on a timer.

ADR-0006 chose local validation over introspection, which makes the key set this
server's own problem rather than Keycloak's. Rotation is not theoretical here:
the realm boots from an empty in-memory database, so **new signing keys are
minted on every restart** and a key identifier this process has never seen is
the ordinary case rather than the exceptional one.

::

    token names an unknown key identifier?
      cooldown elapsed  -> fetch the key set once, retry the lookup
      cooldown active   -> reject
    fetch fails         -> reject, and record what failed

A fixed refresh interval alone would mean every restart produces a window of
blanket failure. The cooldown is what stops the same mechanism becoming an
amplifier: without it, anyone can force outbound fetches by sending tokens with
random key identifiers.

**Discovery is path-inserted** (RFC 8414 §3): the well-known segment goes
between host and path, never appended. ADR-0005 verified that Keycloak serves
the ``oauth-authorization-server`` form and deliberately 404s the OpenID Connect
one, and this is the same address the token helper discovers through — so a
server that could not reach it would be a server testing a different
authorization server.
"""

import logging
from dataclasses import dataclass
from typing import Any, Final

import anyio
import httpx2
from jwt import PyJWK, PyJWKSet

from mcp_erp.transport.configuration import origin_of, path_of

_LOGGER: Final = logging.getLogger(__name__)
"""Where a failed fetch goes, now that it does not go to the caller.

The refusal a fetch failure becomes says ``unknown_key`` and nothing else, which
is ADR-0006's rule and is not reopened here. What that leaves is a defect of ours
being **indistinguishable from an outage and invisible at the same time**: both
leave the key set as it was, both refuse every caller `401 unknown_key`, and both
retry silently once per cooldown for as long as the process runs. The record is
the half that tells them apart, and it is on the server's side of the line
ADR-0006 draws.

**Where it goes is established rather than assumed.** uvicorn's own
``LOGGING_CONFIG`` configures ``uvicorn``, ``uvicorn.error`` and
``uvicorn.access`` and **no root handler**, so a record from this module reaches
:data:`logging.lastResort` — a ``stderr`` stream handler at ``WARNING``. ``ERROR``
clears that threshold, and the default formatter appends the traceback, so what
lands on ``stderr`` is the message and the frames with no level or timestamp in
front of them. Compose collects the container's ``stderr`` under the default
``json-file`` driver, which is what ``docker compose logs server-1`` reads and
what continuous integration dumps when a Compose job fails. See
``server/README.md`` §*Where a failure of ours is recorded*.
"""

DISCOVERY_SEGMENT: Final = "/.well-known/oauth-authorization-server"
"""Inserted between host and path, which is the half implementations miss."""

DEFAULT_COOLDOWN_SECONDS: Final = 10.0
"""How long a failed or fruitless fetch suppresses the next one.

Short enough that a Keycloak restart costs one rejected request rather than a
minute of them, and long enough that a caller sending random key identifiers
cannot turn this server into a load generator pointed at its own authorization
server. ADR-0006 fixed the mechanism and left the number to the build.
"""

DEFAULT_TIMEOUT_SECONDS: Final = 10.0
"""The outbound budget. A hung authorization server must fail this request, not hold it."""


class UnknownKeyIdentifier(Exception):
    """The token names a key this server cannot obtain.

    One exception for both halves of the fail-closed rule — the key set does not
    contain it, and the fetch that would have found it did not happen or did not
    succeed — because the caller's remedy is identical and neither half is a
    fact about the caller's own token that ADR-0006 permits disclosing.
    """


@dataclass(frozen=True, slots=True)
class AuthorizationServerMetadata:
    """The two fields this server reads from the discovery document.

    Everything else the document publishes is the client's business. A resource
    server that read more would be inventing a coupling ADR-0005's one-string
    swap exists to prevent.
    """

    issuer: str
    jwks_uri: str


class KeySet:
    """The issuer's signing keys, held in memory and refetched on a miss.

    Not a general-purpose cache: it holds exactly one issuer's keys, because a
    resource server with two issuers is a different design and this one is
    configured with one string.
    """

    def __init__(
        self,
        issuer: str,
        *,
        client: httpx2.AsyncClient,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        """Hold the issuer and the client; fetch nothing yet.

        Nothing is fetched at construction, so building the application never
        depends on the authorization server being up — the first token pays for
        the first fetch, and a Compose ordering accident fails a request instead
        of a boot.
        """
        self._issuer = issuer
        self._client = client
        self._cooldown_seconds = cooldown_seconds
        self._keys: dict[str, PyJWK] = {}
        self._metadata: AuthorizationServerMetadata | None = None
        self._last_attempt: float | None = None
        self._lock = anyio.Lock()

    @property
    def issuer(self) -> str:
        """The one issuer this key set belongs to."""
        return self._issuer

    async def signing_key(self, key_id: str) -> PyJWK:
        """The key a token names, fetching once if the identifier is unknown.

        Raises:
            UnknownKeyIdentifier: The identifier is absent from the key set and
                either the cooldown is active or the fetch failed. Both are
                refusals; neither falls through to another key.
        """
        key = self._keys.get(key_id)
        if key is not None:
            return key

        async with self._lock:
            # Re-read under the lock: a request that queued behind a fetch must
            # see its result rather than start a second one.
            key = self._keys.get(key_id)
            if key is not None:
                return key

            if not self._cooldown_elapsed():
                raise UnknownKeyIdentifier(key_id)

            await self._refetch()

        key = self._keys.get(key_id)
        if key is None:
            raise UnknownKeyIdentifier(key_id)
        return key

    async def metadata(self) -> AuthorizationServerMetadata:
        """The authorization server's discovery document, fetched once and held.

        Raises:
            RuntimeError: The document is unreachable or names a different
                issuer than the one this server is configured with.
        """
        if self._metadata is None:
            self._metadata = await self._discover()
        return self._metadata

    def _cooldown_elapsed(self) -> bool:
        """Whether another outbound fetch is allowed yet."""
        if self._last_attempt is None:
            return True
        return (anyio.current_time() - self._last_attempt) >= self._cooldown_seconds

    async def _refetch(self) -> None:
        """Fetch the key set once, recording the attempt whether or not it worked.

        The attempt is recorded **before** the request rather than after it
        succeeds, so a failing authorization server is rate-limited by the same
        cooldown as a caller sending nonsense. Failures are swallowed here and
        become :class:`UnknownKeyIdentifier` at the call site: the caller's
        answer is the same, and a transport error carries facts about our own
        infrastructure that a refusal must not disclose.

        **Every failure, rather than a list of them, and the list is why.** Until
        #82 this suppressed four names, and each was there for a step written
        above it: the transport's own errors, the issuer disagreement
        :meth:`_discover` raises, the missing key in the document it reads, and a
        body that is not JSON. ``PyJWKSet.from_dict`` came last and brought none
        of its own, so an empty or malformed key set left the token gate as an
        unhandled error and the caller got a ``500`` where they were owed
        ``401 unknown_key`` — the one outcome the suppression exists to prevent,
        reached through the suppression itself.

        A hand-written tuple is the wrong shape for the claim. What this method
        promises is not *these four things may go wrong* but **after it, either
        there are keys or there are not** — and the ways there are not include
        every library-internal exception in a dependency whose hierarchy nobody
        here enumerates. Enumerating it again would be the same defect with a
        longer list. ``anyio``'s cancellation is not caught, because
        ``CancelledError`` descends from ``BaseException``: a request being torn
        down still tears down.

        **It costs a bug in this block going unseen, and #109 stopped paying
        that.** Until then this was ``contextlib.suppress``, which made a defect
        of ours indistinguishable from an authorization server that is down *and*
        invisible: both leave ``self._keys`` as it was, both answer every caller
        ``401 unknown_key``, and both retry once per cooldown for as long as the
        process runs — an outage that reads as a fleet-wide client problem. The
        caught set is unchanged and the caller's answer is unchanged; what the
        ``except`` buys over the ``suppress`` is one line on ``stderr`` naming the
        failure, on the server's side of the line ADR-0006 draws. :data:`_LOGGER`
        records where that line goes and how it was established.

        The success path still has a falsifier of its own beside the failure
        ones, in ``tests/wire/test_the_cause_a_refusal_names.py``, because a catch
        this wide is only safe while something proves the keys still arrive.
        """
        self._last_attempt = anyio.current_time()
        try:
            metadata = await self.metadata()
            response = await self._client.get(metadata.jwks_uri)
            response.raise_for_status()
            document: dict[str, Any] = response.json()
            self._keys = {
                key.key_id: key for key in PyJWKSet.from_dict(document).keys if key.key_id
            }
        except Exception:
            # No argument interpolated, and that is the non-disclosure rule read
            # in the one direction it does not bind: this record never reaches a
            # caller, so it may hold anything — and the traceback the default
            # formatter appends already names the address, the status and the
            # line, which is more than any hand-written message would.
            _LOGGER.exception("the key set could not be fetched")

    async def _discover(self) -> AuthorizationServerMetadata:
        """Read the authorization server's metadata, path-inserted.

        The issuer the document names is compared against the one we are
        configured with. A document naming a different issuer means the
        deployment has come apart, and continuing would validate tokens against
        a key set belonging to somebody else.

        Raises:
            RuntimeError: The document names an issuer other than ours.
        """
        address = f"{origin_of(self._issuer)}{DISCOVERY_SEGMENT}{path_of(self._issuer)}"
        response = await self._client.get(address)
        response.raise_for_status()
        document: dict[str, Any] = response.json()

        if document.get("issuer") != self._issuer:
            raise RuntimeError(
                f"discovered issuer {document.get('issuer')!r}, expected {self._issuer!r}"
            )

        return AuthorizationServerMetadata(
            issuer=str(document["issuer"]), jwks_uri=str(document["jwks_uri"])
        )

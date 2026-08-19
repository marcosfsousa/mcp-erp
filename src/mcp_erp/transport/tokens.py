"""Local token validation, and the closed vocabulary a refusal names.

Every check is in our own code, against the key set the authorization server
publishes. ADR-0006 rejected introspection for three reasons and one of them is
this module: introspection moves signature and expiry checking inside Keycloak,
deleting the very code this exhibit exists to display, and reduces the audience
check to a field comparison on somebody else's answer.

**Everything closes.** There is no path through this module that returns claims
without a verified signature, a matching issuer, an unexpired lifetime and an
audience naming this server.

**Clock skew is asymmetric, and that is a position rather than sloppiness.**
Zero leeway on expiry; thirty seconds on the not-yet-valid claims. Rejecting a
token that appears to start slightly in the future is a liveness bug and costs
nothing to forgive; accepting one that has expired is a security window — the
same window revocation already concedes, since local validation bounds
revocation by token lifetime alone. Exact expiry also keeps ADR-0007's
ten-second probe client honest: with the conventional sixty-second leeway a
ten-second token stays valid for seventy.

**The description vocabulary is closed** so that the attack suite asserts on a
fixed identifier rather than on prose someone will later reword. Nothing here
discloses anything ADR-0002's rule protects: every fact in play is a property of
the caller's own token, which they already hold.
"""

import time
from dataclasses import dataclass
from typing import Any, Final

import jwt

from mcp_erp.authorization import Claims
from mcp_erp.transport.keys import KeySet, UnknownKeyIdentifier

ALGORITHMS: Final = ("RS256",)
"""The signature algorithms this server will verify, as an allow-list.

An allow-list rather than *whatever the token's header names* is what makes
``alg: none`` and the HMAC-against-a-public-key confusion inexpressible rather
than defended against — the same preference for impossible over guarded that
produced ADR-0006's gate ordering. One entry, because the realm signs with one
algorithm; a second belongs here only when the realm grows one.
"""

NOT_YET_VALID_LEEWAY_SECONDS: Final = 30
"""Forgiveness on ``nbf`` and ``iat``, and on those alone."""

REQUIRED_CLAIMS: Final = ("exp", "iss", "aud", "sub")
"""What a token must carry to be about anybody.

``sub`` is required because it is half the principal directory's key: a token
with no subject cannot be resolved to a principal, and letting it through to be
refused later would put an unattributable caller inside the gate chain.
"""

TOKEN_EXPIRED: Final = "token_expired"
AUDIENCE_MISMATCH: Final = "audience_mismatch"
AUDIENCE_MISSING: Final = "audience_missing"
ISSUER_MISMATCH: Final = "issuer_mismatch"
SIGNATURE_INVALID: Final = "signature_invalid"
UNKNOWN_KEY: Final = "unknown_key"
MALFORMED: Final = "malformed"

DESCRIPTIONS: Final = frozenset(
    {
        TOKEN_EXPIRED,
        AUDIENCE_MISMATCH,
        AUDIENCE_MISSING,
        ISSUER_MISMATCH,
        SIGNATURE_INVALID,
        UNKNOWN_KEY,
        MALFORMED,
    }
)
"""The whole vocabulary, declared once so nothing can name a description off-list.

ADR-0006 listed six of these; ``issuer_mismatch`` is the seventh, added by #37
and recorded there as an amendment. Without it a token from the neighbour realm
could only be refused as ``unknown_key`` — true, because its signing key is not
in our key set, but it makes the ``iss`` comparison unobservable, and
``foreign_issuer_token``'s recorded removal is *"skip the `iss` check against
the configured issuer"*. A removal that changes nothing a test can see is not a
removal.
"""


class TokenRefusal(Exception):
    """A token was presented and rejected, with the one word that says why.

    Distinct from *no token at all*, which is not an error in any sense: RFC
    6750 draws that line and ADR-0006 honours it, so a request carrying no
    credentials gets a challenge with no error code and this exception is never
    raised for it.
    """

    def __init__(self, description: str) -> None:
        """Hold one member of the closed vocabulary."""
        super().__init__(description)
        self.description = description


@dataclass(frozen=True, slots=True)
class ValidatedToken:
    """What a verified token yields: the claims stage, plus when it stops being true.

    ``expires_at`` is layer 1's and stays here rather than joining
    :class:`~mcp_erp.authorization.principal.Claims`. Layer 2 reads issuer,
    subject and granted scopes and nothing else; the expiry is a transport fact,
    needed for one thing only — ``ttlMs = min(5 min, remaining token lifetime)``
    on the tool listing (ADR-0002).
    """

    claims: Claims
    expires_at: int

    def remaining_lifetime_ms(self, *, now: float | None = None) -> int:
        """Milliseconds until this token expires, floored at zero.

        Floored because a negative freshness window is not a shorter one, and a
        token that reached here cannot have expired anyway — this is arithmetic
        that must not be able to produce a nonsense hint if that ever changes.
        """
        moment = time.time() if now is None else now
        return max(0, int((self.expires_at - moment) * 1000))


async def validate(token: str, *, key_set: KeySet, issuer: str, audience: str) -> ValidatedToken:
    """Verify one bearer token, or refuse it with a word from the closed vocabulary.

    The order is deliberate. Structure, then **issuer**, then the key, then the
    signature and the remaining claims. The issuer comparison runs against the
    unverified payload, which is safe for the same reason reading the unverified
    key identifier is: it selects *which* key must have signed this token, and
    lying about it only brings a caller to a signature check they cannot pass.
    Running it first is what makes it observable — a token from the neighbour
    realm is refused for the reason it is actually wrong, rather than incidentally
    because its key is unknown to us.

    Args:
        token: The credential from the ``Authorization`` header.
        key_set: The issuer's signing keys, refetched on a miss behind a cooldown.
        issuer: The one issuer this server trusts.
        audience: This server's resource identifier, which the token must name.

    Returns:
        The claims the token asserts, with its expiry.

    Raises:
        TokenRefusal: Named with one member of :data:`DESCRIPTIONS`.
    """
    try:
        header = jwt.get_unverified_header(token)
        unverified: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as error:
        raise TokenRefusal(MALFORMED) from error

    if unverified.get("iss") != issuer:
        raise TokenRefusal(ISSUER_MISMATCH)

    key_id = header.get("kid")
    if not isinstance(key_id, str) or not key_id:
        # A token naming no key names no key we have. It is structurally valid,
        # so `malformed` would be a different claim than the true one.
        raise TokenRefusal(UNKNOWN_KEY)

    try:
        key = await key_set.signing_key(key_id)
    except UnknownKeyIdentifier as error:
        raise TokenRefusal(UNKNOWN_KEY) from error

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            key=key.key,
            algorithms=list(ALGORITHMS),
            audience=audience,
            issuer=issuer,
            leeway=0,
            options={
                "require": list(REQUIRED_CLAIMS),
                # Both are re-checked below with their own leeway. Left to this
                # call they would inherit the zero the expiry needs, and a clock
                # a second ahead would refuse a token nothing is wrong with.
                "verify_nbf": False,
                "verify_iat": False,
            },
        )
    except jwt.ExpiredSignatureError as error:
        raise TokenRefusal(TOKEN_EXPIRED) from error
    except jwt.MissingRequiredClaimError as error:
        raise TokenRefusal(AUDIENCE_MISSING if error.claim == "aud" else MALFORMED) from error
    except jwt.InvalidAudienceError as error:
        raise TokenRefusal(AUDIENCE_MISMATCH) from error
    except jwt.InvalidIssuerError as error:
        raise TokenRefusal(ISSUER_MISMATCH) from error
    except (jwt.InvalidSignatureError, jwt.InvalidAlgorithmError) as error:
        raise TokenRefusal(SIGNATURE_INVALID) from error
    except jwt.PyJWTError as error:
        raise TokenRefusal(MALFORMED) from error

    _refuse_if_not_yet_valid(payload)

    return ValidatedToken(
        claims=Claims(
            issuer=str(payload["iss"]),
            subject=str(payload["sub"]),
            granted_scopes=scope_set(payload.get("scope")),
        ),
        expires_at=int(payload["exp"]),
    )


def scope_set(value: object) -> frozenset[str]:
    """A ``scope`` string as the set it denotes.

    RFC 6749 §3.3 makes these space-delimited, **case-sensitive** strings, so
    nothing here lowercases anything: ``scope_exact_match`` asserts that
    ``ERP.READ`` does not satisfy ``erp.read``, and a normalising split would
    make that row untestable from this side. A token with no ``scope`` claim
    yields the empty set rather than an error — it is a token that may do
    nothing, which the chain refuses at the scope gate like any other.
    """
    if not isinstance(value, str):
        return frozenset()
    return frozenset(value.split())


def _refuse_if_not_yet_valid(payload: dict[str, Any]) -> None:
    """The asymmetric half of the skew rule: thirty seconds of forgiveness.

    **The one approximate mapping in this module, named rather than hidden.**
    ADR-0006's vocabulary has no member for *not yet valid*, because the leeway
    is what that clause is about and no client of this realm can produce a token
    beyond it — Keycloak stamps ``nbf`` and ``iat`` from its own clock, and the
    clock is the container's. So the residual is refused as ``malformed``: the
    honest reading is that a credential claiming to begin in the future is one
    this server cannot make sense of. An eighth vocabulary member for a state
    the realm cannot reach was declined — a closed vocabulary earns its name by
    every member being observable.

    Raises:
        TokenRefusal: The token claims to start, or to have been issued, more
            than the leeway into the future, or carries a non-numeric moment.
    """
    now = time.time() + NOT_YET_VALID_LEEWAY_SECONDS
    for claim in ("nbf", "iat"):
        moment = payload.get(claim)
        if moment is None:
            continue
        if not isinstance(moment, int | float):
            raise TokenRefusal(MALFORMED)
        if moment > now:
            raise TokenRefusal(MALFORMED)

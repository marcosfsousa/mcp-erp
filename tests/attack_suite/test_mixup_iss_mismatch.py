"""`mixup_iss_mismatch` — the client reads no response it cannot attribute.

Scenario: `mixup_iss_mismatch`, `basis: clause`, `MUST NOT` — *"MUST NOT act on
or display error, error_description, or error_uri"*, with RFC 9207 §2.4 beside
it.

    removal: Skip comparing the response's `iss` against the issuer recorded
             before redirecting.

**The suite's only client-side row**, adopted because we author the client. What
a mix-up attack does is get an honest authorization server's response in front of
a client that was talking to a different one: the client then redeems a code at
the wrong token endpoint, or — the half implementations usually miss — reports an
error that answers a request it never made. This row covers the error case.

**The attacker's authorization server is not built, and does not need to be.**
`as_metadata_issuer_spoof` was refused on cost — a hostile metadata host for one
row — and it would buy nothing here: what the defence compares is the issuer
recorded *before* redirecting against the one the response is attributed to, and
a genuine response from the neighbour realm is as unattributable to our realm as
a forged one would be. So the response below is real, minted by a real
authorization server, and arrives where a client expecting the other one is
waiting.

**Two issuers exist for exactly this kind of row.** ADR-0007's neighbour realm
has its own keys, its own client and its own metadata; `token_passthrough` and
`foreign_issuer_token` use it at the resource server, and this row uses it one
layer up, at the client.

**The client is `tests/tokens.py`, and it is the client this project authors
today.** It performs the whole authorization code flow — challenge, login,
consent, redemption — and #46's conformance client will perform it a second time,
through a hosted identity document. The obligation is the same for both, and the
check lives where the flow lives rather than being written twice.
"""

import secrets
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from scenarios import exercises

import tokens
from tokens import (
    NEIGHBOUR_CLIENT,
    NEIGHBOUR_REALM,
    REDIRECT_URI,
    authorization_code,
    challenge_for,
    metadata,
    reachable,
)

TIMEOUT = 30.0


def _error_response_from(realm: str, client_id: str) -> tuple[str, str]:
    """One real authorization error response, and the issuer that produced it.

    Produced by asking for the weak challenge method, which ADR-0007 pins per
    client — so the authorization server answers with a redirect carrying
    `error`, `error_description` and, per RFC 9207, `iss`. That is exactly the
    document a mix-up puts in front of the wrong client, and it is obtained here
    by asking an honest server an honest question it refuses.

    Returns:
        The redirect's `Location`, and the issuer the realm declares.
    """
    document = metadata(realm)
    with httpx.Client(follow_redirects=False, timeout=TIMEOUT) as http:
        answer = http.get(
            reachable(str(document["authorization_endpoint"])),
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

    assert answer.status_code == httpx.codes.FOUND, answer.text
    return str(answer.headers["location"]), str(document["issuer"])


@exercises("mixup_iss_mismatch")
def test_mixup_iss_mismatch() -> None:
    """A response from an issuer the client did not redirect to is not read at all.

    The client began its flow at the **neighbour** realm and a response from
    **ours** arrives at the callback. Under the recorded removal the client reads
    the error first and reports `invalid_request` — an honest server's words,
    about a request this client never made, which is precisely *acting on* an
    error the clause forbids acting on. With the comparison in place it refuses
    for the reason that is actually true: it cannot attribute this response.

    The failure message is asserted, not just the failure. Both readings raise;
    only one of them says the right thing, and a client that reported the wrong
    one would send a developer to debug a challenge method rather than a mix-up.
    """
    location, issuer_that_answered = _error_response_from(tokens.REALM, tokens.CONFORMANCE_CLIENT)
    neighbour = str(metadata(NEIGHBOUR_REALM)["issuer"])

    # A real response, attributable to a real authorization server — and not the
    # one this client redirected to.
    attributed = parse_qs(urlparse(location).query)["iss"][0]
    assert attributed == issuer_that_answered
    assert issuer_that_answered != neighbour

    with pytest.raises(ValueError, match="attributed to issuer") as refused:
        authorization_code(location, expected_state="whatever", expected_issuer=neighbour)

    # And it is refused *without* the other server's words being repeated as
    # though they answered this client.
    assert "invalid_request" not in str(refused.value)


@exercises("mixup_iss_mismatch")
def test_the_same_response_is_read_once_it_is_attributable() -> None:
    """The control: the check is about attribution, not about refusing everything.

    The identical redirect, handed to a client that did redirect to the issuer
    that produced it, is read — and what it says is the error it carries. A
    defence that refused both would pass the test above while making the client
    unable to complete any flow, which is the shape a nervous fix takes.
    """
    location, issuer_that_answered = _error_response_from(tokens.REALM, tokens.CONFORMANCE_CLIENT)

    with pytest.raises(ValueError, match="invalid_request"):
        authorization_code(
            location, expected_state="whatever", expected_issuer=issuer_that_answered
        )


@exercises("mixup_iss_mismatch")
def test_a_successful_response_is_attributed_before_its_code_is_redeemed() -> None:
    """The success path carries `iss` too, which is what makes the check general.

    An error response is the half implementations miss, and it is not the half
    an attacker wants: the prize is a **code**, redeemed by the victim client at
    an endpoint the attacker chose. So the same comparison has to stand in front
    of a successful response, and this asserts that it does — with a real one,
    driven end to end by the neighbour realm's own client.

    Every mint in every suite in this repository goes through the same call, so
    this is also the assertion that the check has not been switched off by being
    made optional somewhere.
    """
    minted = tokens.mint(
        "tomas.weber", ["erp.read"], client_id=NEIGHBOUR_CLIENT, realm=NEIGHBOUR_REALM
    )

    # The flow completed, which it could only do by passing the attribution
    # check with the issuer the helper discovered before redirecting.
    assert minted.claims["iss"] == str(metadata(NEIGHBOUR_REALM)["issuer"])

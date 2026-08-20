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

**The client under test is `tests/tokens.py`.** It performs the whole
authorization code flow — challenge, login, consent, redemption — and the `iss`
comparison this row falsifies lives in its `authorization_code`, ahead of
everything else the redirect carries.

**There is a second client we author, and it keeps the same clause elsewhere.**
#46's conformance client earns its identity through a hosted document and hands
the redirect's parameters to the protocol package, which validates RFC 9207 `iss`
against the issuer it discovered — but a refusal carries no code, so it can never
be handed over, and the ordering in its `_callback` is its own to get right. #78
put the attribution ahead of `redirect_error` there and falsified it in
`tests/conformance/test_a_refusal_is_attributed_before_it_is_repeated.py`, which
is where it has to live: the client under test is that directory's, and the
declarations this directory collects are read out of this directory's source.
Both clients, one clause, two falsifiers.
"""

from urllib.parse import parse_qs, urlparse

import pytest
from scenarios import exercises

import tokens
from tokens import (
    NEIGHBOUR_CLIENT,
    NEIGHBOUR_REALM,
    authorization_code,
    metadata,
    refused_authorization_response,
)


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
    location, issuer_that_answered = refused_authorization_response(
        tokens.REALM, tokens.CONFORMANCE_CLIENT
    )
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
    location, issuer_that_answered = refused_authorization_response(
        tokens.REALM, tokens.CONFORMANCE_CLIENT
    )

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

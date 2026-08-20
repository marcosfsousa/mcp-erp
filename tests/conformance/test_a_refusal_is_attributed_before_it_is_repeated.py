"""The other half of `mixup_iss_mismatch`, on the other client this project authors.

The attack suite's `mixup_iss_mismatch` row falsifies the `iss` comparison in
`tests/tokens.py`'s `authorization_code`, and until #78 it said out loud that it
asserted nothing about the conformance client. This module is what let that
paragraph be deleted.

**Why the check lives in the client at all**, when the protocol package already
performs it: `AuthorizationCodeResult` requires a `code`, a refused response
carries an `error` and none, so a refusal cannot be handed over — the party that
validates RFC 9207 `iss` on the success path never receives the error path. That
leaves `Flow._callback` as the only line where the clause can be kept, which is
why it keeps it.

**Here rather than in `tests/attack_suite/`**, because the client under test is
this directory's, and the declarations that directory collects are read out of
its own source. The row's note carries the cross-reference instead.

**The success path is asserted next door, by the whole suite.** A flow that
completes is a flow whose callback returned a code, so nothing here re-asserts
that an attributable success is read — `test_the_flow_completes_and_the_call_lands`
is that assertion, and a change that refused everything would take it down.
"""

from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlencode, urlparse

import pytest
from mcp.shared.auth import OAuthMetadata

import tokens
from conformance_client import UNATTRIBUTED, Flow
from tokens import (
    CONFORMANCE_CLIENT,
    NEIGHBOUR_REALM,
    metadata,
    refused_authorization_response,
)

SOMEBODY = "priya.raman"
"""A Person from the Cast, named because :class:`Flow` takes one and never used.

No form is posted in this module. The redirect handed to the callback below was
minted by a request of these tests' own, so the username never reaches a login
page — and a real name rather than a placeholder means a reader who follows it
finds a Person instead of wondering what `unused` would have done.
"""


def _expecting(realm: str, *, answered_with: str) -> Flow:
    """A flow that discovered one realm's issuer, holding a redirect from wherever.

    Two pieces of the flow's own state, set rather than reached: the metadata
    document the package writes onto its context when it discovers, and the
    `Location` :meth:`Flow._open` records on the way past. **Both are real** —
    the metadata is fetched from the realm named, and the redirect was minted by
    a live authorization server refusing a live request.

    Reaching that state by driving the client instead would need the mix-up
    staged, and `docs/attack-suite/scenarios.yaml` refused that on cost:
    `as_metadata_issuer_spoof` would be a hostile metadata host built for one
    row, and it would buy nothing — what the defence compares is the issuer
    discovered before redirecting against the one the response is attributed to,
    and a genuine response from the neighbour realm is as unattributable to ours
    as a forged one would be.
    """
    flow = Flow(SOMEBODY)
    flow._provider.context.oauth_metadata = OAuthMetadata.model_validate(dict(metadata(realm)))
    flow._callback_location = answered_with

    return flow


def _without_the_iss(location: str) -> str:
    """The same redirect with its RFC 9207 parameter removed, and nothing else changed."""
    parsed = urlparse(location)
    query = parse_qs(parsed.query)
    del query["iss"]

    return parsed._replace(query=urlencode(query, doseq=True)).geturl()


def test_a_refusal_the_client_cannot_attribute_is_not_repeated() -> None:
    """The clause: an error from an issuer this client did not redirect to is not displayed.

    The flow discovered the **neighbour** realm and a refusal from **ours**
    arrives at the callback. Under the ordering this replaced — `redirect_error`
    read first — the client raises with `invalid_request` and an honest server's
    description of a request it never made, which is precisely the *acting on or
    displaying* the row's quoted `MUST NOT` forbids. With the attribution first
    it refuses for the reason that is true, and repeats nothing the other server
    said.

    Both halves are asserted. Either ordering raises; only one of them says the
    right thing, and a client that reported the wrong one would send a reader to
    debug a challenge method rather than a mix-up.
    """
    location, issuer_that_answered = refused_authorization_response(
        tokens.REALM, CONFORMANCE_CLIENT
    )
    flow = _expecting(NEIGHBOUR_REALM, answered_with=location)

    # A real response, attributable to a real authorization server — and not the
    # one this flow discovered.
    assert parse_qs(urlparse(location).query)["iss"][0] == issuer_that_answered
    assert flow.discovered_issuer != issuer_that_answered

    with pytest.raises(RuntimeError) as refused:
        asyncio.run(flow._callback())

    assert UNATTRIBUTED in str(refused.value)
    assert "invalid_request" not in str(refused.value)


def test_the_same_refusal_is_repeated_once_it_is_attributable() -> None:
    """The control, and what keeps this from being a blanket silencing.

    The identical redirect, handed to a flow that discovered the issuer which
    produced it, is reported in that server's own words — so a refused flow stays
    diagnosable. A defence that withheld both would pass the test above while
    making every failure read the same, which is the shape a nervous fix takes.
    """
    location, _ = refused_authorization_response(tokens.REALM, CONFORMANCE_CLIENT)
    flow = _expecting(tokens.REALM, answered_with=location)

    with pytest.raises(RuntimeError, match="invalid_request"):
        asyncio.run(flow._callback())


def test_a_refusal_that_names_no_issuer_is_not_attributed_by_default() -> None:
    """Absence is not agreement, on the one path with nothing else to go on.

    The protocol package tolerates a missing `iss` unless the authorization
    server advertised support for it, which is right for a response it can still
    validate other ways — it holds the `state` it generated and a code it is
    about to redeem at an endpoint it discovered. A refusal offers none of that.
    So a redirect carrying an error and no issuer is one this client cannot
    attribute, and it is refused on the same terms as one attributed elsewhere.
    """
    location, _ = refused_authorization_response(tokens.REALM, CONFORMANCE_CLIENT)
    flow = _expecting(tokens.REALM, answered_with=_without_the_iss(location))

    with pytest.raises(RuntimeError) as refused:
        asyncio.run(flow._callback())

    assert UNATTRIBUTED in str(refused.value)
    assert "invalid_request" not in str(refused.value)

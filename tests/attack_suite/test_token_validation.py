"""Two rows of the suite, landed early because this slice is what makes them reachable.

`audience_missing` and `foreign_issuer_token` — the two the ticket asks for by
name, and the two that need no tool to exist beyond the one that now does. The
remaining rows arrive with #44, which also brings the bijection between
`scenarios.yaml` and the tests that declare a scenario by name.

Both are minted through a **real flow against a real client**, not invented here.
ADR-0007 provisions `mcp-conformance-bare` with no audience mapper and a whole
second realm with its own signing keys, precisely so that these two assertions
run against tokens an authorization server actually issued. Minting them in the
test instead would exercise the same branch while asserting against a token we
wrote.
"""

import httpx2

import rpc
from tokens import NEIGHBOUR_CLIENT, NEIGHBOUR_REALM, mint


def test_audience_missing() -> None:
    """A token the authorization server minted with **no audience at all** is refused.

    Scenario: `audience_missing`, `basis: adr`, sourced to ADR-0006 §Refusals
    disclose the caller's own token, and nothing else.

        removal: Treat an absent `aud` as "not addressed to anyone else" and
                 allow it.

    Deliberately not a clause. Research 0003 established that nothing in the
    specification says what a server does with an audience-less token, so
    fail-closed is this project's decision rather than a conformance tick — which
    is why the row carries a project-ADR basis and a null normative strength.

    It is also the row the audience check as a whole rests on. Keycloak does not
    honour RFC 8707's `resource` parameter (normative register row 1), so the
    resource server's own audience check is the load-bearing control; a server
    that waved through a token with no audience would have no control left.
    """
    minted = mint("priya.raman", ["erp.read"], client_id="mcp-conformance-bare")
    assert "aud" not in minted.claims, minted.claims

    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "audience_missing"
    assert parameters["resource_metadata"] == rpc.METADATA_URL


def test_foreign_issuer_token() -> None:
    """A structurally valid token from an issuer our metadata does not name is refused.

    Scenario: `foreign_issuer_token`, `basis: clause`, `MUST NOT` —
    *"MCP servers MUST NOT accept or transit any other tokens."*

        removal: Skip the `iss` check against the configured issuer.

    The neighbour realm makes this a real token rather than an invented one: its
    own signing keys, its own flow, and — through a hardcoded claim mapper —
    **the same subject and the same audience** as the genuine article. So it is
    perfect in every respect except who issued it, which is the only thing left
    for the refusal to be about.

    **Why the description is asserted and not only the status.** Our own key set
    does not contain the neighbour's key either, so a server with no `iss` check
    would still refuse this token — as `unknown_key`. Asserting the description
    is what makes the recorded removal observable: delete the `iss` comparison
    and this assertion fails, where a status-only assertion would not.
    """
    minted = mint("tomas.weber", ["erp.read"], client_id=NEIGHBOUR_CLIENT, realm=NEIGHBOUR_REALM)
    # Perfect except for the issuer: the subject is a directory row, and the
    # audience is ours.
    assert minted.subject == "tomas-weber"
    assert rpc.RESOURCE in _audiences(minted.claims.get("aud"))
    assert minted.claims["iss"].endswith(NEIGHBOUR_REALM)

    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert parameters["error"] == "invalid_token"
    assert parameters["error_description"] == "issuer_mismatch"


def _audiences(claim: object) -> set[str]:
    """The `aud` claim as a set, since it is one value or a list of them."""
    if isinstance(claim, str):
        return {claim}
    if isinstance(claim, list):
        return {str(value) for value in claim}
    return set()

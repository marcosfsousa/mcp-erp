"""What answers a stranger, and what does not.

ADR-0006 published discovery both ways and made the address **path-inserted, and
only path-inserted** — RFC 9728 §3.1 puts the well-known segment between host and
path, which research 0003 calls the single most commonly mis-implemented line in
the whole discovery chain. The deliberate `404` at the bare root is the half a
reader would otherwise read as an oversight.
"""

import httpx2

import rpc
from tokens import ISSUER, mint


def test_the_metadata_document_answers_without_a_token() -> None:
    """The one route outside the token gate, and it is outside it structurally."""
    response = rpc.get(rpc.METADATA_PATH)

    assert response.status_code == httpx2.codes.OK
    document = response.json()

    assert document["resource"] == rpc.RESOURCE
    # The seed's own issuer, read from the seed rather than written out again:
    # the document has to name the authorization server that actually minted the
    # token in the test below, and a second copy of that string here would be a
    # second place for it to be wrong.
    assert document["authorization_servers"] == [ISSUER]
    # Published, and therefore a contract this server then keeps: a token in the
    # query string is refused because the document says only the header is read.
    assert document["bearer_methods_supported"] == ["header"]
    # Derived from the capability the one registered tool declares. `erp.write`
    # and `erp.decide` join it when the tools that declare them do.
    assert document["scopes_supported"] == ["erp.read"]
    # A protected resource SHOULD NOT advertise this: refresh tokens are not a
    # resource requirement.
    assert "offline_access" not in document["scopes_supported"]


def test_the_bare_well_known_root_is_refused() -> None:
    """A decision rather than an oversight.

    That address describes a resource identifier with **no path component**,
    which is a different resource from ours. Answering there would be a
    conformance error dressed as helpfulness.
    """
    assert rpc.get("/.well-known/oauth-protected-resource").status_code == httpx2.codes.NOT_FOUND


def test_the_appended_form_is_refused() -> None:
    """The mis-implementation the clause exists to prevent, asserted directly."""
    assert (
        rpc.get("/mcp/.well-known/oauth-protected-resource").status_code == httpx2.codes.NOT_FOUND
    )


def test_nothing_else_is_served() -> None:
    """Every path but the two is a `404`, including the ones a framework adds.

    FastAPI serves its own schema and two documentation pages by default, and
    unauthenticated. They are switched off in the composition root, which is what
    this asserts: the metadata document is the only path on this server that
    answers a stranger with content.
    """
    for path in ("/", "/openapi.json", "/docs", "/redoc", "/health"):
        assert rpc.get(path).status_code == httpx2.codes.NOT_FOUND, path


def test_the_tool_endpoint_challenges_a_request_with_no_credentials() -> None:
    """A challenge **with no error code**, which is the line RFC 6750 draws.

    Nothing is wrong with the token; there simply is not one. An error code
    belongs only where a token was presented and rejected, and inventing one
    here would tell a client to fix something it has not done.
    """
    response = rpc.post("tools/list")

    assert response.status_code == httpx2.codes.UNAUTHORIZED
    parameters = rpc.challenge(response)
    assert "error" not in parameters
    # Both discovery mechanisms lead to one document: this is the address the
    # test above fetched, so a client following the header and a client guessing
    # the well-known address cannot be split.
    assert parameters["resource_metadata"] == rpc.METADATA_URL
    assert parameters["scope"] == "erp.read"


def test_server_discover_answers_without_a_token() -> None:
    """Era detection precedes authorization, and says nothing about purchasing.

    Putting this probe behind a `401` would rest the exhibit's only third-party
    evidence on recovery behaviour nobody has tested. Because it is the one
    endpoint that answers strangers, constraint `#10`'s deletion test applies
    hardest here: a portable layer-2 pattern whose public face narrates
    requisitions is not portable.
    """
    result = rpc.result(rpc.post("server/discover"))

    assert "2026-07-28" in result["supportedVersions"]
    instructions = result["instructions"].lower()
    for word in ("requisition", "invoice", "purchase", "cost centre", "vendor", "approver"):
        assert word not in instructions, word


def test_a_valid_token_reaches_the_tool_endpoint() -> None:
    """The positive path, so the assertions above are refusals rather than a broken server."""
    minted = mint("priya.raman", ["erp.read"])
    response = rpc.post("tools/list", token=minted.access_token)

    assert response.status_code == httpx2.codes.OK
    assert "error" not in response.json()

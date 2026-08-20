"""Gate 5: what the token carries, compared exactly against what the tool requires.

Two scenarios, and they split on the deletion rather than on the answer.
`insufficient_scope` is the comparison being **skipped** — the tool result comes
back without the intersection ever running. `scope_exact_match` is the comparison
being **run wrongly** — a string that resembles the required scope is allowed to
satisfy it. Both end in the same `403`, which is exactly why ADR-0010 splits rows
on their removals: one answer, two ways to lose it.

**The scope strings are derived from the declarations, never written here.**
ADR-0012 makes the scope a function of the capability a tool declares —
`namespace.capability` — so a suite that spelled `erp.read` beside each
assertion would be a second author for a string the server generates, and the
two would drift the first time a namespace moved.
"""

from typing import Any

import httpx2
from scenarios import exercises

import rpc
from mcp_erp.purchase_to_pay import approve_requisition, list_requisitions, submit_requisition
from tokens import mint

CAPABILITIES: tuple[tuple[str, str, dict[str, Any]], ...] = (
    (list_requisitions.NAME, list_requisitions.ACTION.scope, {}),
    (
        submit_requisition.NAME,
        submit_requisition.ACTION.scope,
        {
            "vendor": "Meridian Cloud Services",
            "amount": "100.00",
            "currency": "EUR",
            "description": "Quarterly window cleaning",
        },
    ),
    (
        approve_requisition.NAME,
        approve_requisition.ACTION.scope,
        {"ids": ["req_0001"], "decision": "approve"},
    ),
)
"""One tool per capability, with arguments a permitted call would have been given.

The arguments are never read — gate 5 answers before dispatch — and they are real
anyway, so that a refusal cannot be the schema's doing rather than the scope's.
"""

LOOKALIKE_CLIENT = "mcp-scope-lookalike"
"""ADR-0007's fifth client, and it exists for one row.

Its whole configuration is *our audience, and two scopes that are not ours*: it
can mint `ERP.READ` and `hr.read` while naming this resource server, so its token
reaches the scope gate instead of being refused at the audience one.
"""

CASE_VARIANT = "ERP.READ"
NAMESPACE_VARIANT = "hr.read"


@exercises("insufficient_scope")
def test_insufficient_scope() -> None:
    """A valid token lacking the operation's scope never reaches the operation.

    Scenario: `insufficient_scope`, `basis: clause`, `SHOULD` — *"When a client
    makes a request with an access token with insufficient scope during runtime
    operations, the server SHOULD respond with: HTTP 403 Forbidden status code
    (per RFC 6750 Section 3.1) … WWW-Authenticate header with the Bearer scheme
    and additional parameters: error="insufficient_scope" … scope="required_scope1
    required_scope2" … resource_metadata."*

        removal: Return the tool result without intersecting granted scope first.

    `floor: true`, as gate 5. **The challenge's shape is the assertion, not the
    `403`** — all three parameters the clause names, because a status code alone
    tells a client nothing it can act on and ADR-0006 commits us to this shape
    regardless of the clause being a `SHOULD` rather than a `MUST`.

    One tool per capability, each called by a Person holding the **other two**
    scopes. That is what makes the refusal about this tool's requirement rather
    than about a token that is short of everything: the caller is authorized, and
    authorized for the wrong thing.
    """
    for tool, required, arguments in CAPABILITIES:
        others = [scope for _, scope, _ in CAPABILITIES if scope != required]
        minted = mint("tomas.weber", others)
        assert required not in minted.granted_scopes, minted.granted_scopes

        response = rpc.call_tool(tool, arguments, token=minted.access_token)

        assert response.status_code == httpx2.codes.FORBIDDEN, (tool, response.text)
        parameters = rpc.challenge(response)
        assert parameters["error"] == "insufficient_scope", tool
        assert parameters["scope"] == required, tool
        assert parameters["resource_metadata"] == rpc.METADATA_URL, tool
        # The refusal names a scope genuinely published and a tool the caller
        # themselves supplied. Neither is a fact only the database holds, which
        # is ADR-0002's disclosure rule as ADR-0006 repaired it.
        assert required in rpc.get(rpc.METADATA_PATH).json()["scopes_supported"], tool


@exercises("scope_exact_match")
def test_scope_exact_match() -> None:
    """A scope that merely resembles the required one satisfies nothing.

    Scenario: `scope_exact_match`, `basis: adr`, sourced to ADR-0012
    §Unrecognised scopes are inert. RFC 6749 §3.3 rides in the row's `context`
    field rather than as its basis — *"space-delimited, case-sensitive strings"*
    is definitional, carries no normative keyword, and governs how the
    authorization server represents the parameter rather than how a resource
    server compares it.

        removal: Replace exact case-sensitive set membership with any laxer
                 comparison.

    **One row and one test, because the deletion is a single site.** Both
    variants are asserted against the same comparison expression: `ERP.READ` must
    not satisfy `erp.read`, which is the case half, and `hr.read` must not
    satisfy it either, which is the namespace half. A case-insensitive comparison
    passes the first; a comparison that matched on the capability suffix passes
    the second; exact membership passes neither.

    It splits from `insufficient_scope` on the deletion: that row's removal skips
    the intersection entirely, and this row's runs it wrongly.

    **A real flow through a real client, and the client is why this row needed a
    finding recorded.** `scenarios.yaml` said the row was testable without new
    realm state because `mcp-conformance-decoy` already holds another resource's
    scope. Run by hand on 2026-08-20 it is not: the decoy's token carries
    somebody else's audience by construction — that is what makes it
    `audience_confusion`'s instrument — so it is refused at gate 4 and never
    reaches the comparison this row is about. ADR-0007 grew a fifth client for it,
    on the same terms as the other three: one client, one refusal it makes
    reachable.
    """
    minted = mint("tomas.weber", [CASE_VARIANT, NAMESPACE_VARIANT], client_id=LOOKALIKE_CLIENT)

    # The token is good in every way but the strings it carries: our issuer, our
    # audience, a directory subject, and two scopes that are not capability
    # scopes of ours.
    assert rpc.RESOURCE in str(minted.claims.get("aud"))
    assert minted.granted_scopes >= {CASE_VARIANT, NAMESPACE_VARIANT}
    assert not minted.granted_scopes & {scope for _, scope, _ in CAPABILITIES}, (
        minted.granted_scopes
    )

    response = rpc.call_tool(list_requisitions.NAME, token=minted.access_token)

    assert response.status_code == httpx2.codes.FORBIDDEN, response.text
    parameters = rpc.challenge(response)
    assert parameters["error"] == "insufficient_scope"
    assert parameters["scope"] == list_requisitions.ACTION.scope


@exercises("scope_exact_match")
def test_the_case_variant_is_inert_on_its_own() -> None:
    """The case half alone, so a passing pair cannot hide behind the other string.

    Scenario: `scope_exact_match`.

    Together the two variants would still pass on a server that compared case
    insensitively **and** refused for the namespace — the token would carry
    `hr.read` and be refused for it, and nobody would learn that `ERP.READ` had
    been accepted. One string at a time is what separates them.
    """
    minted = mint("tomas.weber", [CASE_VARIANT], client_id=LOOKALIKE_CLIENT)
    assert minted.granted_scopes >= {CASE_VARIANT}

    response = rpc.call_tool(list_requisitions.NAME, token=minted.access_token)

    assert response.status_code == httpx2.codes.FORBIDDEN, response.text
    assert rpc.challenge(response)["scope"] == list_requisitions.ACTION.scope

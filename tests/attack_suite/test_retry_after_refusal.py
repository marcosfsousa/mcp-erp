"""Three refusals, and what a client that believes them does next.

Scenarios: `retry_after_role_denial`, `retry_after_sod_denial_same_person` and
`retry_after_sod_denial_other_person` — all `basis: adr`, sourced to ADR-0002
§Refusal shape follows the remedy and §Surviving contact with a retrying client.

**The attacker here is a client doing what it was told.** Nothing malicious is
sent: a refusal names a remedy, and the caller acts on it. What the three rows
forbid is a server whose stated remedy is *false* — one that sends a client to
acquire a scope it already holds, or promises that a different person could act
when nobody could, or promises nothing when somebody could. A false remedy is
worse than no remedy: it turns a refusal into a loop, and a loop into a model
spending a person's tokens on a request that can never succeed.

**They are three rows because they are three deletions.** The role refusal's is
the wire shape — answer `403` with a challenge, and the client re-authorizes for
a scope it already carries. The same-person row's is the *predicate* — check
segregation of duties against roles held rather than positions occupied, and
retrying identically starts to work. The other-person row's is the *field* — set
`retry_as_other_person_helps` from a constant, and the answer stops being about
this decision at all.

**Every row this module acts on is one it raised.** No fixture reload, because
nothing here reads a seeded row: the separation edge needs a requisition whose
submitter is the person about to be refused, and that is a row a test has to
create rather than find.

*The file is named for a refusal and the rows are named for a denial, and the
difference is deliberate.* `CONTEXT.md`'s **Refusal** entry bars *denial* as
another word for it, and that rule binds every identifier this ticket chooses.
It does not reach the three row names: `scenarios.yaml` calls `name` a stable
identifier that is *"never reworded"*, they were assigned before the vocabulary
entry existed, and rewording one would break the join every test in this
directory declares through.
"""

from typing import Any

import httpx2
from scenarios import exercises

import rpc
from mcp_erp.transport.refusals import ROLE_DENIED_CODE
from requisitions import raised_by
from tokens import mint

APPROVE = "approve_requisition"

BELOW_THRESHOLD = "480.00"
"""So that `approver` suffices and nothing but the rule under test can refuse."""

NO_ERP_ROLE = "priya.raman"
"""Holds `approver` in the realm and **no role in the ERP** — the one divergence.

ADR-0007 gives her that on purpose: it is what makes the scope-without-role state
reachable through a real authorization code flow, and so what makes the middle
denial class something the exhibit demonstrates rather than asserts.
"""

SUBMITTER = "tomas.weber"
"""CC-4100, `approver`. Raises a row and is then refused on the row he raised."""

COUNTERPARTY = "ingrid.holm"
"""CC-4100, `unlimited_approver`. The different person a remedy sends the caller to."""

BYSTANDER = "priya.raman"
"""CC-4100, and the person who raises a row nobody is refused for having raised."""


def _decide(username: str, identifiers: list[str]) -> httpx2.Response:
    """One `approve_requisition` call, as the raw response.

    Raw rather than parsed, because two of the three rows below assert on what
    the *HTTP* answer is — a `403` and a challenge is precisely the shape
    `retry_after_role_denial` forbids, and a parsed result would have thrown that
    away before the assertion.
    """
    return rpc.call_tool(
        APPROVE,
        {"ids": identifiers, "decision": "approve"},
        token=mint(username, ["erp.decide"]).access_token,
    )


def _outcome(response: httpx2.Response) -> dict[str, Any]:
    """The refusal or the decision a one-item call answered with.

    A one-item batch is rendered directly rather than folded, so this is the
    answer itself.
    """
    structured: dict[str, Any] = rpc.result(response)["structuredContent"]
    return structured


@exercises("retry_after_role_denial")
def test_retry_after_role_denial() -> None:
    """Scope present, ERP role absent — and the refusal does not send her for a scope.

    Scenario: `retry_after_role_denial`, `basis: adr`, sourced to ADR-0002
    §Refusal shape follows the remedy.

        removal: Return 403 with a `WWW-Authenticate` challenge for the
                 missing-ERP-role case.

    **A `403` here would be a lie**, and the loop it produces is the whole
    argument for three refusal shapes rather than one: the challenge instructs
    the client to acquire a scope, the client re-authorizes, the authorization
    server issues the same token — because the scope is genuinely hers — and the
    call is refused identically. Forever.

    So the answer is a JSON-RPC error, `-31010`, carrying a remedy no client can
    act on alone: an administrator grants the role. Both retry booleans are
    false, and the identical retry below is what says so in behaviour rather than
    in a field.

    Reachable only because ADR-0007 gives Priya Raman `approver` in Keycloak and
    no ERP role. Without that divergence the state would be unreachable through a
    real flow, and the middle denial class would be a paragraph.
    """
    minted = mint(NO_ERP_ROLE, ["erp.decide"])
    # She really does hold the scope, which is what makes a scope challenge a lie
    # rather than a mistake.
    assert "erp.decide" in minted.granted_scopes

    identifier = raised_by(BYSTANDER, BELOW_THRESHOLD)
    refused = _decide(NO_ERP_ROLE, [identifier])

    assert refused.status_code == httpx2.codes.OK
    assert "www-authenticate" not in refused.headers
    error = rpc.error(refused)
    assert error["code"] == ROLE_DENIED_CODE
    assert error["data"] == {
        "reason": "role_missing",
        "remedy": "administrator_grant",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": False,
    }

    # The refusal's own claim, acted on: an identical call answers identically,
    # so a client that ignored the fields and retried gains nothing and loses
    # nothing.
    again = _decide(NO_ERP_ROLE, [identifier])
    assert rpc.error(again) == error


@exercises("retry_after_sod_denial_same_person")
def test_retry_after_sod_denial_same_person() -> None:
    """Nobody decides the requisition they raised, and retrying does not change who they are.

    Scenario: `retry_after_sod_denial_same_person`, `basis: adr`, sourced to
    ADR-0002 §Surviving contact with a retrying client.

        removal: Check segregation of duties against roles held rather than
                 positions occupied on the chain.

    **The pair is the assertion.** One Person, one token, two rows: refused on
    the one he raised, permitted on the one he did not. That is what *a position
    occupied once on one chain* means, and it is what a role-based check cannot
    express — a rule reading his roles would answer the same for both, whichever
    answer it gave.

    The identical retry is the row's own name: `retry_identical_helps` is false,
    and the second call proves it rather than reporting it. Nothing about a
    retry changes which position on this chain he occupies.
    """
    his_own = raised_by(SUBMITTER, BELOW_THRESHOLD)
    somebody_elses = raised_by(BYSTANDER, BELOW_THRESHOLD)

    refused = _outcome(_decide(SUBMITTER, [his_own]))

    assert refused["reason"] == "segregation_of_duties"
    assert refused["retry_identical_helps"] is False
    assert refused["retry_as_other_person_helps"] is True

    # Identical call, identical answer.
    assert _outcome(_decide(SUBMITTER, [his_own])) == refused

    # Same person, same token, same roles — and the row he did not raise goes
    # through, which is what makes the refusal about the position and not about
    # him.
    permitted = _outcome(_decide(SUBMITTER, [somebody_elses]))
    assert permitted["requisition"]["status"] == "approved"


@exercises("retry_after_sod_denial_other_person")
def test_retry_after_sod_denial_other_person() -> None:
    """The stated remedy is true, and it is proved by acting on it.

    Scenario: `retry_after_sod_denial_other_person`, `basis: adr`, sourced to
    ADR-0002 §Surviving contact with a retrying client.

        removal: Set `retry_as_other_person_helps` from a constant instead of
                 from the decision.

    `floor: true`, as gate 6 — the domain rule — and it is the row that keeps
    segregation of duties distinct from every other refusal in the vocabulary.
    Two reasons are byte-identical in shape to this one and mean different
    things; what a client can *do* about them is the only thing that separates
    them, and this asserts the field by doing it.

    The refusal says a different person would help. A different person then
    decides the same requisition, and it goes through.
    """
    his_own = raised_by(SUBMITTER, BELOW_THRESHOLD)

    refused = _outcome(_decide(SUBMITTER, [his_own]))
    assert refused["reason"] == "segregation_of_duties"
    assert refused["retry_as_other_person_helps"] is True

    decided = _outcome(_decide(COUNTERPARTY, [his_own]))

    assert decided["requisition"]["status"] == "approved"
    assert decided["purchase_order"]["approved_by"]["id"] == "ingrid-holm"


@exercises("retry_after_sod_denial_other_person")
def test_the_field_says_no_when_a_different_person_would_not_help() -> None:
    """The other half of *from the decision*: a refusal where the answer is false.

    Scenario: `retry_after_sod_denial_other_person`.

    Under the recorded removal the field is a constant, and a constant that
    happened to be `true` would satisfy the test above on its own. So this is the
    same field on a refusal where the honest answer is the other one: a decided
    requisition is decided for everybody, and the different person who tries next
    is told so and is right to stop.

    One field, two refusals, two values — which is what *from the decision*
    means, asserted rather than described.
    """
    raised = raised_by(BYSTANDER, BELOW_THRESHOLD)
    assert _outcome(_decide(SUBMITTER, [raised]))["requisition"]["status"] == "approved"

    refused = _outcome(_decide(COUNTERPARTY, [raised]))

    assert refused["reason"] == "already_decided"
    assert refused["remedy"] == "none"
    assert refused["retry_as_other_person_helps"] is False
    assert refused["retry_identical_helps"] is False

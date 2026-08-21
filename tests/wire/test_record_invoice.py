"""`record_invoice` — the second separation edge, and the scope-versus-role intersection.

The smallest of the five tools and the last of them. What it adds that nothing
before it could reach:

- **A resource that is not a `Requisition`.** The `PurchaseOrder` is the thing
  acted against, and `Invoice` is the thing created — so the hydration step
  selects an entity for the first time, and the invoice does not exist when the
  decision is taken.
- **The second segregation-of-duties edge**, tested against
  `PurchaseOrder.approved_by`. The first edge is a position on the requisition;
  this one is a position one link further down the same chain.
- **The intersection of scope and role, visible on one tool.** `erp.write` is
  ungated by any role mapping — a mapping there would lock every submitter out
  of a scope ADR-0003 gives them — so the same token that submits a requisition
  reaches this tool and achieves nothing without `invoice_clerk`. The role check
  is what stops the write, not the scope.
- **`already_invoiced`**, the fourth of layer 3's reasons and the last value in
  the closed vocabulary to become producible.

**One item, by declaration rather than by deferral.** ADR-0002's *Five tools*
gives the list to `approve_requisition` alone, and #41 restored it there. Nothing
is postponed here: the fold exists, layer 1 folds on outcome cardinality and
never learns which tool produced one, so a single outcome renders directly — the
same body `get_requisition` answers with, reached the same way.

**The refusal bodies below are written out, on the same grounds
`test_approve_requisition.py` states at length.** This suite exists to show what
the wire looks like, and a refusal that reads as a lookup shows nothing; the
suites whose job is a defence or a whole table read theirs from the `Reason`
record instead. A change to ADR-0002's mapping edits the literals below, and
`tests/matrix/test_the_reason_mapping.py` is what makes that a red check (#87).

**Every order this suite records against is one it raised and approved.**
Recording is terminal, so an order shared between two tests would hand the second
one `already_invoiced` — and an order at all has to be minted through
`approve_requisition`, because nothing else emits one.

**Where this lives, since #43 wrote `matrix.yaml`.** The decision itself is a
matrix row now — `(principal x tool x resource -> expected)` is exactly what that
table is canonical for, and `tests/matrix/` drives one row per branch of this
tool over the wire. What stays here is everything a row does not express: what
the call *did* to the rows behind it, what the declaration says, and the
argument errors that are not refusals at all. A row states which answer came
back; these state what else was true afterwards.

The overlap between the two is real and was not resolved by this ticket. #66's
handoff moved five assertions — one per scope set the tool listing filters on —
and named no others, so the rest stayed where they are and `tests/wire/README.md`
records what a later ticket has to decide.
"""

from collections.abc import Iterator
from typing import Any

import httpx2
import pytest

import fixtures
import rpc
from tokens import mint

TOOL = "record_invoice"
SUBMIT = "submit_requisition"
APPROVE = "approve_requisition"

VENDOR = "Meridian Cloud Services"
"""One of the four names `submit_requisition` enumerates. Nothing here turns on which."""

AMOUNT = "480.00"
"""Below the threshold, so raising and approving a chain costs one role and no argument."""

RECORDER = "rafael.costa"
"""CC-4100, `invoice_clerk` and nothing else — the positive side of the second edge."""

RECORDER_CENTRE = "CC-4100"
"""His partition, named because one assertion needs a requisition he can read.

The convergence below presents a *requisition's* identifier to a tool that
hydrates orders, and the answer has to be `not_found` for the entity rather than
for the partition — so the row it names is one he could otherwise see.
"""

APPROVER = "ingrid.holm"
"""CC-4100, `unlimited_approver` **and** `invoice_clerk`.

Two roles composing on one Person, which is what makes the negative side of the
second edge a statement about a position rather than about a role: she holds the
recording role and is still refused on the one order she approved.
"""

SUBMITTER = "priya.raman"
"""CC-4100, and no ERP role at all. Raises the rows the chain runs on."""

ABSENT_ORDER = "po_9999"
"""An identifier in the right shape that no order carries, and none will.

The *never existed* half of the convergence below. Written out rather than
derived, because it has to stay absent for the whole run and `approve_requisition`
mints the next identifier after the highest that exists. Nothing reaches four
figures in a test run.
"""


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Start from the committed rendering, so this module knows where it began.

    It writes three times over — a row raised, approved, then invoiced — and
    `fixtures.load()` deletes `invoice` before `purchase_order` before
    `requisition` and then re-inserts all three, so the starting state is the
    rendering rather than whatever a previous module left. The rendering's own
    six orders and one invoice are there throughout; what this module mints is
    reached by identifier, never by counting a table.
    """
    fixtures.load()
    yield


def _approved(submitter: str = SUBMITTER, approver: str = APPROVER) -> str:
    """Raise a requisition and approve it, and name the order that came out.

    The only way to get an order at all: `approve_requisition` is what emits one,
    and `approved_by` is stamped from the approver's own token rather than from
    any argument — which is what makes the edge below a check against a position
    occupied on this chain.
    """
    raised = rpc.result(
        rpc.call_tool(
            SUBMIT,
            {
                "vendor": VENDOR,
                "amount": AMOUNT,
                "currency": "EUR",
                "description": "Managed Kubernetes, annual",
            },
            token=mint(submitter, ["erp.write"]).access_token,
        )
    )
    assert raised["isError"] is False, raised

    decided = rpc.result(
        rpc.call_tool(
            APPROVE,
            # A one-item list, because `approve_requisition` is the batch and
            # this tool is not. Layer 1 folds on outcome cardinality, so one item
            # renders as the decision itself rather than under `outcomes` — which
            # is what lets this helper read the order straight out of it.
            {"ids": [raised["structuredContent"]["requisition"]["id"]], "decision": "approve"},
            token=mint(approver, ["erp.decide"]).access_token,
        )
    )
    assert decided["isError"] is False, decided

    identifier: str = decided["structuredContent"]["purchase_order"]["id"]
    return identifier


def _record(username: str, identifier: str) -> httpx2.Response:
    """One `record_invoice` call, raw.

    The response rather than a parsed result, because half the assertions here
    are about what shape the answer took — a tool result, a JSON-RPC error, or a
    `403` that never reaches the handler at all.
    """
    return rpc.call_tool(TOOL, {"id": identifier}, token=mint(username, ["erp.write"]).access_token)


def _permitted(username: str, identifier: str) -> dict[str, Any]:
    """One recording that went through.

    Raises:
        AssertionError: It was refused. Every caller here wants the records the
            recording produced, so a refusal is a broken precondition rather
            than an answer.
    """
    result = rpc.result(_record(username, identifier))

    assert result["isError"] is False, result
    payload: dict[str, Any] = result["structuredContent"]
    return payload


def _refused(username: str, identifier: str) -> dict[str, Any]:
    """One recording the chain or the order's own state stopped.

    Raises:
        AssertionError: It was permitted.
    """
    result = rpc.result(_record(username, identifier))

    assert result["isError"] is True, result
    payload: dict[str, Any] = result["structuredContent"]
    return payload


def test_the_declaration_names_one_purchase_order_and_nothing_else() -> None:
    """One argument: the order being billed.

    No amount, no vendor and no supplier reference — the order fixes all three,
    and an order takes exactly one invoice at full value, so an amount could only
    restate one. No recorder identity either: it is the token's subject, which is
    what makes the second edge a check against a position rather than against
    something the caller supplied.
    """
    tools = rpc.result(rpc.post("tools/list", token=mint(RECORDER, ["erp.write"]).access_token))
    (tool,) = [entry for entry in tools["tools"] if entry["name"] == TOOL]

    assert set(tool["inputSchema"]["properties"]) == {"id"}
    assert tool["inputSchema"]["required"] == ["id"]
    assert tool["inputSchema"]["additionalProperties"] is False
    assert tool["outputSchema"]["required"] == ["purchase_order", "invoice"]


def test_an_invoice_recorder_records_against_an_order_somebody_else_approved() -> None:
    """The positive side of the second edge, and the whole write path with it.

    The order comes back because its status is the thing that moved: nothing in
    the tool set reads a purchase order — ADR-0002 cut `list_purchase_orders` —
    so `open` becoming `invoiced` would otherwise be a terminal state with
    nothing able to observe it.
    """
    order = _approved()

    recorded = _permitted(RECORDER, order)

    assert recorded["purchase_order"]["id"] == order
    assert recorded["purchase_order"]["status"] == "invoiced"
    assert recorded["purchase_order"]["approved_by"] == {
        "id": "ingrid-holm",
        "label": "Ingrid Holm",
    }
    invoice = recorded["invoice"]
    assert invoice["id"].startswith("inv_")
    assert invoice["purchase_order"] == {"id": order, "label": "Managed Kubernetes, annual"}
    assert invoice["recorded_by"] == {"id": "rafael-costa", "label": "Rafael Costa"}


def test_the_invoice_carries_a_reference_and_an_identity_and_nothing_else() -> None:
    """Where the governing rule bites hardest, asserted on the wire.

    No amount, no vendor, no supplier reference and no cost centre. The purchase
    order fixes the first three and the requisition the last, and an order takes
    exactly one invoice at full value — so an amount here could only restate one.
    """
    order = _approved()

    invoice = _permitted(RECORDER, order)["invoice"]

    assert set(invoice) == {"id", "purchase_order", "recorded_by"}


def test_the_two_references_in_one_body_share_a_label_and_name_two_records() -> None:
    """The chain reading as a chain, and the one legibility exception paying for it.

    A purchase order has no name of its own, so the reader's half of a reference
    to one is the requisition's description — the same string the order's own
    reference to that requisition carries. The identifiers differ and the labels
    do not, which is what lets a reader see that all three records belong to one
    chain without following either handle.

    Asserted rather than left to fall out, because the alternative reads as a
    defect: the same string against two different identifiers in one body is a
    decision, and ADR-0003 asked for its one exception to stay checkable.
    """
    order = _approved()

    recorded = _permitted(RECORDER, order)

    label = recorded["purchase_order"]["requisition"]["label"]
    assert recorded["invoice"]["purchase_order"] == {"id": order, "label": label}
    assert recorded["purchase_order"]["requisition"]["id"].startswith("req_")
    assert order.startswith("po_")


def test_the_write_scope_reaches_this_tool_and_the_role_is_what_stops_it() -> None:
    """The intersection, on the one tool where it is visible in a single token.

    `erp.write` is ungated by any role mapping, and it had to be: ADR-0003 gates
    submitting by scope alone, so a mapping there would lock every submitter out
    of a scope they are entitled to. The consequence is this — the same scope
    covers both writes, and the ERP role decides which of the two a caller
    actually reaches.

    Priya Raman is the proof, holding `erp.write` and no ERP role at all. The
    token that raised the requisition this order came from cannot bill it, and
    what refuses her is the role gate rather than the scope gate: a `403` here
    would instruct her to acquire a scope she already holds and demonstrably
    used.
    """
    order = _approved()

    error = rpc.error(_record(SUBMITTER, order))

    assert error["code"] == -31010
    assert error["data"] == {
        "reason": "role_missing",
        "remedy": "administrator_grant",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": False,
    }
    # The remedy is an administrator's grant, so a different person is not it —
    # but the order was not billed either, which is what makes the refusal a
    # refusal rather than a write with a message attached.
    assert _permitted(RECORDER, order)["purchase_order"]["status"] == "invoiced"


def test_the_auditing_role_reads_three_centres_and_records_no_invoice() -> None:
    """Breadth is a read widening, never a write grant.

    Anna Lindqvist holds `auditor`, which widens which rows come back from the
    two read tools and confers no write authority of its own — so the realm
    issues her `erp.write` like anyone else and the role gate refuses her here.

    **What this does not assert is `partition_bypass`.** Row scoping runs after
    the role gate, so she never reaches it, and nobody in the cast holds
    `auditor` together with `invoice_clerk`. A declaration that wrongly bypassed
    the partition on this tool would grant cross-partition invoice recording and
    ship green — ADR-0013 names this tool as the one a reader gets wrong for
    symmetry. The guard is review and the reasoning is in the declaration.
    """
    order = _approved()

    error = rpc.error(_record("anna.lindqvist", order))

    assert error["data"]["reason"] == "role_missing"


def test_the_approver_cannot_record_the_invoice_for_what_they_approved() -> None:
    """The second segregation-of-duties edge, tested against `PurchaseOrder.approved_by`.

    **A position, never a role**, and Ingrid Holm is what makes the difference
    observable rather than described: she holds `invoice_clerk` standing, and she
    is refused on exactly one order — the one she approved. Holding every role in
    the organisation would not change it, because what refuses her is a position
    occupied once on this chain.

    That is also why the edge cannot be a role check. `unlimited_approver` and
    `invoice_clerk` compose on one Person by design (ADR-0003), so a rule reading
    *does the caller hold the approving role* would refuse her on every order in
    her centre, including the ones somebody else approved.
    """
    order = _approved()

    assert _refused(APPROVER, order) == {
        "reason": "segregation_of_duties",
        "remedy": "different_person",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": True,
    }

    # The remedy, acted on rather than asserted: a different person records it.
    assert _permitted(RECORDER, order)["purchase_order"]["status"] == "invoiced"


def test_the_edge_refuses_a_position_and_not_a_role() -> None:
    """The same Person, the same role, another order — and she records it.

    The negative test above is only half the claim. If `invoice_clerk` were what
    refused her, this would be refused too; what separates the two calls is which
    order carries her subject in `approved_by`.
    """
    hers = _approved(approver=APPROVER)
    somebody_elses = _approved(approver="tomas.weber")

    assert _refused(APPROVER, hers)["reason"] == "segregation_of_duties"
    assert _permitted(APPROVER, somebody_elses)["invoice"]["recorded_by"] == {
        "id": "ingrid-holm",
        "label": "Ingrid Holm",
    }


def test_a_second_invoice_against_a_billed_order_is_refused() -> None:
    """The other terminal state, and the other half of ADR-0002's retry promise.

    A model that ignores every field and retries cannot write a second invoice.
    The remedy is `none` and both retry booleans are false, because a billed
    order is billed for everybody — there is no person and no token that makes it
    billable again.
    """
    order = _approved()
    first = _permitted(RECORDER, order)

    assert _refused(RECORDER, order) == {
        "reason": "already_invoiced",
        "remedy": "none",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": False,
    }
    assert first["invoice"]["purchase_order"]["id"] == order

    # Two People hold `invoice_clerk` and one of them approved this order, so *a
    # different person* is her — and what she gets is not `already_invoiced` at
    # all. **Authorization runs before the row's own state**, so a caller who may
    # not bill this order learns nothing about whether it has been billed.
    assert _refused(APPROVER, order)["reason"] == "segregation_of_duties"


def test_a_foreign_order_and_an_order_that_never_existed_answer_byte_identically() -> None:
    """Row scoping on the invoice path, and the convergence it reaches.

    Rafael Costa clears the scope gate and the role gate — he is the one Person
    who holds `invoice_clerk` and nothing else — so the only thing between him
    and an order raised in CC-4200 is the partition. The order has no centre of
    its own: what is compared is the requisition's, one link up the chain, which
    is ADR-0003's *join away* deciding an authorization question.

    The refused row and the row that never existed answer identically, reached
    through layer 2's single return site. The handler passes the hydration step's
    answer straight through — `None` included — so it cannot tell them apart
    because it never looks.
    """
    foreign_order = _approved(submitter="anna.lindqvist", approver="yusuf.demir")

    foreign = _record(RECORDER, foreign_order)
    absent = _record(RECORDER, ABSENT_ORDER)

    assert foreign.status_code == absent.status_code
    assert foreign.content == absent.content, (foreign.text, absent.text)
    assert rpc.result(foreign)["structuredContent"]["reason"] == "not_found"


def test_a_requisition_identifier_is_not_a_purchase_order() -> None:
    """The hydration step selects an entity, and this is that from the outside.

    Every earlier tool hydrates a `Requisition`; this one hydrates the
    `PurchaseOrder` and nothing else. A requisition's identifier presented here
    is looked for among the orders, found nowhere, and answered on the same terms
    as any other absent row — the tool never reaches the requisition table, and
    it never touches an invoice, which does not exist when the decision is taken.
    """
    absent = _record(RECORDER, ABSENT_ORDER)
    requisition = _record(RECORDER, fixtures.a_row_in(RECORDER_CENTRE))

    assert requisition.content == absent.content, (requisition.text, absent.text)


def test_a_token_without_the_write_scope_is_refused_before_the_handler_runs() -> None:
    """The first denial class: a `403` naming the scope the caller must acquire.

    Gate 5 refuses it, so nothing is hydrated and nothing is billed. The scope is
    derived from the capability the tool declares — the same `erp.write`
    `submit_requisition` declares — so what the challenge names and what
    `scopes_supported` publishes cannot drift.
    """
    order = _approved()

    response = rpc.call_tool(TOOL, {"id": order}, token=mint(RECORDER, ["erp.decide"]).access_token)

    assert response.status_code == httpx2.codes.FORBIDDEN
    parameters = rpc.challenge(response)
    assert parameters["error"] == "insufficient_scope"
    assert parameters["scope"] == "erp.write"
    assert parameters["resource_metadata"] == rpc.METADATA_URL
    # Nothing was billed, so the order is still there to bill.
    assert _permitted(RECORDER, order)["purchase_order"]["status"] == "invoiced"

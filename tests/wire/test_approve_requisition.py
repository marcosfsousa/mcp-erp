"""`approve_requisition` — the first role-gated tool, and the first batch.

**A batch, since #41.** The tool takes a list of identifiers and one decision,
and answers for every item the list names — permit or refusal, never a silent
drop. The rule layer 1 renders that with is asserted in `test_the_fold.py`
beside this; what is asserted here is what a *decision* does with it: mixed
verdicts in one body, a caller-level refusal replacing the whole response
instead of riding in it, and an item named twice answered twice.

Six things arrive here that no earlier tool could reach.

- **A resource is hydrated by a named step and handed to the chain.** The
  resource is the `Requisition` — *the thing acted against, never the thing
  created* — and the `PurchaseOrder` an approval emits does not exist when the
  decision is taken.
- **`role_missing`'s `-31010` becomes reachable at the wire.** #39 shipped both
  its tools gated by scope alone and said so: the falsifier arrives with the
  first role-gated tool, and this is it. Priya Raman holds `approver` in the
  realm and no ERP role at all, so she can carry `erp.decide` and still be
  refused by the role gate — which is the divergence ADR-0007 calls load-bearing.
- **Two relationship rules run, in the order the `Action` declares.** The
  threshold first, then the submitter edge; `test_the_threshold_is_declared
  _before_the_submitter_edge` is what makes that order an assertion rather than
  an accident, and `test_marketing_has_nobody_who_can_approve_above_the
  _threshold` is what makes it matter.
- **A terminal state.** A second decision on a decided requisition answers
  `already_decided` and mints nothing.
- **Both entry points, and the batch is what makes that structural.**
  `decide_call` runs once ahead of the items and `decide_item` runs per item.
  Not tidiness: a caller-level refusal is a `-31010` protocol error, which
  cannot ride inside a result body, so a batch that reached it per item would
  produce N answers layer 1 could not render. ADR-0002's *caller-level refusals
  are whole-call; item-level refusals are per-item* is the axis, and this is the
  first call with more than one item on it.
- **Per-item idempotency, per item of a real batch.** A blind retry of a whole
  batch answers `already_decided` for each item and mints nothing; the scenario
  that owns that assertion is `double_approval_via_batch_retry`, in the attack
  suite.

**Every row this suite decides on is one it raised.** Approval is terminal, so a
row shared between two tests would hand the second one `already_decided` — and
ADR-0003 chose a wipe per run over a reset between rows. Raising through
`submit_requisition` is also the only way to get a row at a chosen amount into a
chosen centre: the partition is the submitter's and no argument can change it.

**Where this lives.** A principal, a tool and a resource mapped to an expected
answer is `matrix.yaml`'s shape, and #43 has not written that file. `tests/wire/`
is where ADR-0013 parks a wire assertion with no artifact to belong to yet, on
the same terms as `test_submit_requisition.py` beside it.
"""

from collections.abc import Iterator
from typing import Any

import httpx2
import pytest

import rpc
import seeded_requisitions
from tokens import mint

TOOL = "approve_requisition"
GET = "get_requisition"
SUBMIT = "submit_requisition"

VENDOR = "Meridian Cloud Services"
"""One of the four names `submit_requisition` enumerates. Nothing here turns on which."""

THRESHOLD = "5000.00"
"""ADR-0003's €5,000, at the boundary: *at or below*, `approver` suffices."""

ABOVE_THRESHOLD = "5000.01"
"""One cent past it, which is the whole of what separates the two roles."""

WELL_ABOVE = "7500.00"
"""Above the threshold by an amount a reader does not have to squint at."""

APPROVER = "tomas.weber"
"""CC-4100, `approver`. Decides at or below the threshold and is refused above it."""

UNLIMITED = "ingrid.holm"
"""CC-4100, `unlimited_approver` — the role with no upper limit, so it covers both tiers."""

SUBMITTER = "priya.raman"
"""CC-4100, and no ERP role at all. Raises the rows the two approvers decide.

She is also the `role_missing` case: ADR-0007 gives her `approver` in the realm
and nothing at the server, so she is the one Person who can carry `erp.decide`
to a role gate that refuses her.
"""

OUTSIDER = "yusuf.demir"
"""Everything the approver is, in CC-4200 — the row-scoping foil the seed says he is."""

MARKETING = "mei.tanaka"
"""CC-4300's only inhabitant, holding `approver` and no more.

Which makes CC-4300 a centre that can raise a requisition above the threshold and
contains nobody who can decide it. ADR-0003 §The capability holes are deliberate
put that hole there on purpose.
"""


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Start from the seeded four, with the purchase orders cleared.

    This module writes twice over — a row raised, then decided — so it must know
    where it began. The loader clears `purchase_order` before `requisition`,
    which is what makes the orders this module mints the only ones in the table.
    """
    seeded_requisitions.load()
    yield


def _raise(username: str, amount: str) -> str:
    """Raise one requisition as this Person, against their own centre, and name it.

    Their own centre because there is no other kind: `submit_requisition` takes
    no cost centre, so who raises the row is what decides which centre it lands
    in — which is how a CC-4300 row above the threshold gets written at all.
    """
    result = rpc.result(
        rpc.call_tool(
            SUBMIT,
            {
                "vendor": VENDOR,
                "amount": amount,
                "currency": "EUR",
                "description": "Managed Kubernetes, annual",
            },
            token=mint(username, ["erp.write"]).access_token,
        )
    )

    assert result["isError"] is False, result
    identifier: str = result["structuredContent"]["requisition"]["id"]
    return identifier


def _decide(username: str, identifier: str, decision: str = "approve") -> httpx2.Response:
    """One `approve_requisition` call naming one item, raw.

    The response rather than a parsed result, because half the assertions below
    are about what shape the answer took — a tool result, a JSON-RPC error, or a
    `403` that never reaches the handler at all.

    A one-item batch, which layer 1 renders directly rather than folding, so
    every single-item assertion below reads exactly as it did before the list
    arrived. That the two cardinalities differ at all is `test_the_fold.py`'s
    subject.
    """
    return _decide_all(username, [identifier], decision)


def _decide_all(
    username: str, identifiers: list[str], decision: str = "approve"
) -> httpx2.Response:
    """One `approve_requisition` call over however many items are named, raw.

    One `decision` for the whole list, which is ADR-0002's shape: the decision is
    what the caller intends, and the list is the set of rows they intend it for.
    A list of `{id, decision}` pairs would be a second way to spell the same call
    and would add no authorization behaviour.
    """
    return rpc.call_tool(
        TOOL,
        {"ids": identifiers, "decision": decision},
        token=mint(username, ["erp.decide"]).access_token,
    )


def _answers(
    username: str, identifiers: list[str], decision: str = "approve"
) -> tuple[list[dict[str, Any]], bool]:
    """The N answers a folded body carries, and whether the result is marked in error."""
    result = rpc.result(_decide_all(username, identifiers, decision))

    answers: list[dict[str, Any]] = result["structuredContent"]["outcomes"]
    marked: bool = result["isError"]
    return answers, marked


def _permitted(username: str, identifier: str, decision: str = "approve") -> dict[str, Any]:
    """One decision that went through.

    Raises:
        AssertionError: It was refused. Every caller here wants the record the
            decision produced, so a refusal is a broken precondition rather than
            an answer.
    """
    result = rpc.result(_decide(username, identifier, decision))

    assert result["isError"] is False, result
    payload: dict[str, Any] = result["structuredContent"]
    return payload


def _refused(username: str, identifier: str, decision: str = "approve") -> dict[str, Any]:
    """One decision the chain or the row's own state stopped.

    Raises:
        AssertionError: It was permitted.
    """
    result = rpc.result(_decide(username, identifier, decision))

    assert result["isError"] is True, result
    payload: dict[str, Any] = result["structuredContent"]
    return payload


def _status(username: str, identifier: str) -> str:
    """What the requisition says about itself, read back through the named read."""
    result = rpc.result(
        rpc.call_tool(GET, {"id": identifier}, token=mint(username, ["erp.read"]).access_token)
    )

    assert result["isError"] is False, result
    status: str = result["structuredContent"]["requisition"]["status"]
    return status


def test_the_declaration_names_a_list_of_rows_and_one_decision() -> None:
    """Two arguments: which rows, and which way.

    `decision` is an enum of two rather than a second tool, because rejecting is
    the same authorization decision as approving — a separate tool would add a
    `tools/list` row and no authorization behaviour. And there is no `amount`
    and no `cost_centre`: both are facts about the rows the server already holds,
    and a caller who could restate either could restate them wrongly.

    **The list carries a ceiling**, which is the one constraint here that is not
    ADR-0002's. A batch is N writes inside one request, and a declared list with
    no upper bound is a request whose cost the caller chooses.
    """
    tools = rpc.result(rpc.post("tools/list", token=mint(APPROVER, ["erp.decide"]).access_token))
    (tool,) = [entry for entry in tools["tools"] if entry["name"] == TOOL]

    declared = tool["inputSchema"]
    assert set(declared["properties"]) == {"ids", "decision"}
    assert declared["required"] == ["ids", "decision"]
    assert declared["properties"]["ids"] == {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "maxItems": 20,
    }
    assert declared["properties"]["decision"]["enum"] == ["approve", "reject"]
    assert declared["additionalProperties"] is False


def test_the_declaration_publishes_both_bodies_the_cardinality_can_produce() -> None:
    """One `outputSchema`, two bodies, and exactly one of them per call.

    Layer 1 folds on cardinality alone, because cardinality is the only thing it
    is allowed to know — so a one-item call answers with the decision itself and
    a two-item call answers with a list of them. The tool that can be called
    either way declares both, and the `oneOf` is what stops the pair being read
    as one body with optional halves.

    It describes the **permitted** body, which is what an `outputSchema` has
    described here since the first refusal shipped: a refused item is a result
    marked in error, and layer 3 declaring the refusal's shape would be layer 3
    describing how layer 1 renders.
    """
    tools = rpc.result(rpc.post("tools/list", token=mint(APPROVER, ["erp.decide"]).access_token))
    (tool,) = [entry for entry in tools["tools"] if entry["name"] == TOOL]

    declared = tool["outputSchema"]
    assert set(declared["properties"]) == {"requisition", "purchase_order", "outcomes"}
    assert declared["oneOf"] == [{"required": ["requisition"]}, {"required": ["outcomes"]}]
    assert declared["additionalProperties"] is False
    # The list's items are the one-item body, so the two cannot describe the
    # same row differently.
    assert declared["properties"]["outcomes"]["items"]["required"] == ["requisition"]


def test_an_approval_emits_a_purchase_order_carrying_the_approver() -> None:
    """The record that carries the approver's identity forward.

    `approved_by` is the whole reason the entity exists: it is what the second
    segregation-of-duties edge is tested against when `record_invoice` arrives at
    #42. The requisition comes back too, so the caller sees the state their own
    call produced rather than having to read it back.
    """
    identifier = _raise(SUBMITTER, THRESHOLD)

    decided = _permitted(APPROVER, identifier)

    assert decided["requisition"]["id"] == identifier
    assert decided["requisition"]["status"] == "approved"
    order = decided["purchase_order"]
    assert order["id"].startswith("po_")
    assert order["requisition"] == {"id": identifier, "label": "Managed Kubernetes, annual"}
    assert order["approved_by"] == {"id": "tomas-weber", "label": "Tomas Weber"}
    assert order["status"] == "open"


def test_the_purchase_order_carries_no_copy_of_the_cost_centre() -> None:
    """ADR-0003's correction to ADR-0002, asserted on the wire.

    The approver's identity is load-bearing and the cost centre is a join away,
    so denormalising it would buy a shorter query and a second copy of a fact
    that can disagree with the first. The row it points at carries the centre,
    and it carries it once.
    """
    identifier = _raise(SUBMITTER, THRESHOLD)

    decided = _permitted(APPROVER, identifier)

    assert set(decided["purchase_order"]) == {"id", "requisition", "approved_by", "status"}
    assert decided["requisition"]["cost_centre"] == "CC-4100"


def test_the_role_at_the_threshold_decides_at_the_threshold() -> None:
    """*At or below*, `approver` suffices — and the boundary is inclusive.

    Asserted at exactly €5,000 rather than under it, because *at or below* and
    *below* differ on precisely one value and a test that never names it cannot
    tell the two rules apart.
    """
    identifier = _raise(SUBMITTER, THRESHOLD)

    assert _permitted(APPROVER, identifier)["requisition"]["status"] == "approved"


def test_the_role_at_the_threshold_is_refused_one_cent_above_it() -> None:
    """The refusal, and the remedy that is true: a different person acts.

    `retry_identical_helps` is false because nothing about the caller will
    change; `retry_as_other_person_helps` is true because somebody holding the
    unlimited role can decide this row — which the test below acts on rather
    than asserting.
    """
    identifier = _raise(SUBMITTER, ABOVE_THRESHOLD)

    assert _refused(APPROVER, identifier) == {
        "reason": "over_threshold",
        "remedy": "different_person",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": True,
    }
    # A refused decision decides nothing: the row is where it was.
    assert _status(SUBMITTER, identifier) == "submitted"


def test_the_role_with_no_upper_limit_reaches_the_branch_the_other_cannot() -> None:
    """The same row, the other role, and the remedy above acted on.

    One identifier, two callers, two answers — which is what makes the threshold
    a decision about the principal rather than a property of the row.
    """
    identifier = _raise(SUBMITTER, WELL_ABOVE)

    assert _refused(APPROVER, identifier)["reason"] == "over_threshold"
    assert _permitted(UNLIMITED, identifier)["requisition"]["status"] == "approved"


def test_the_role_with_no_upper_limit_has_no_lower_bound_either() -> None:
    """*No upper limit* means it covers the small ones too, so nobody holds both roles.

    That is the whole of why `senior_approver` was renamed: the old name needed
    a gloss every time it appeared, and this is the branch the gloss described.
    """
    identifier = _raise(SUBMITTER, "480.00")

    assert _permitted(UNLIMITED, identifier)["requisition"]["status"] == "approved"


def test_the_submitter_cannot_approve_their_own_requisition() -> None:
    """The first segregation-of-duties edge, tested against `submitted_by`.

    A position occupied on one chain, never a role held standing: the approver
    below holds `approver` and is refused on exactly one row — the one he
    raised.
    """
    identifier = _raise(APPROVER, "1200.00")

    assert _refused(APPROVER, identifier) == {
        "reason": "segregation_of_duties",
        "remedy": "different_person",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": True,
    }
    assert _status(APPROVER, identifier) == "submitted"

    # The remedy, acted on rather than asserted: a different person decides it.
    assert _permitted(UNLIMITED, identifier)["requisition"]["status"] == "approved"


def test_the_threshold_is_declared_before_the_submitter_edge() -> None:
    """A row both rules refuse comes back with the first rule's reason.

    The tuple's order is a declaration about which refusal a caller sees, and
    this is the case that observes it: the approver's own row, above the
    threshold, refuses on both counts. The test below is why the order is this
    way round rather than the other.
    """
    identifier = _raise(APPROVER, WELL_ABOVE)

    assert _refused(APPROVER, identifier)["reason"] == "over_threshold"


def test_marketing_has_nobody_who_can_approve_above_the_threshold() -> None:
    """The capability hole, named: a remedy no available human fills.

    CC-4300 holds one Person. She may raise a requisition at any amount, and the
    refusal she gets truthfully reports `retry_as_other_person_helps: true` while
    the organisation contains nobody who could act on it: the only unlimited
    approver holds CC-4100, so the row is not even visible to her.

    **A remedy names a class of action, never an available person.** Conflating
    the two is how authorization systems come to promise what the organisation
    cannot deliver, and ADR-0003 put this hole here so the distinction would be
    tested rather than described.

    It is also what fixes the rule order. Every CC-4300 requisition is submitted
    by its only inhabitant, so an `Action` declaring the submitter edge first
    would answer `segregation_of_duties` here for ever and this branch would be
    unreachable — a hole made invisible by the order rules happen to be written
    in.
    """
    identifier = _raise(MARKETING, WELL_ABOVE)

    refused = _refused(MARKETING, identifier)
    assert refused["reason"] == "over_threshold"
    assert refused["remedy"] == "different_person"
    assert refused["retry_as_other_person_helps"] is True

    # The one Person who holds the role the remedy points at is in another
    # centre, so what she gets is not a threshold refusal at all — it is the
    # answer for a row that, as far as she can tell, does not exist.
    assert _refused(UNLIMITED, identifier)["reason"] == "not_found"
    assert _status(MARKETING, identifier) == "submitted"


def test_a_second_decision_on_a_decided_requisition_is_refused() -> None:
    """Terminal states, and the idempotency ADR-0002's retrying client rests on.

    A model that ignores every field and retries cannot mint a second purchase
    order. The remedy is `none` and both retry booleans are false, because there
    is no person and no token that makes a decided row decidable again.
    """
    identifier = _raise(SUBMITTER, "480.00")
    first = _permitted(APPROVER, identifier)

    assert _refused(APPROVER, identifier) == {
        "reason": "already_decided",
        "remedy": "none",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": False,
    }
    # And not by a different person either, nor by deciding the other way.
    assert _refused(UNLIMITED, identifier)["reason"] == "already_decided"
    assert _refused(APPROVER, identifier, "reject")["reason"] == "already_decided"
    assert _status(SUBMITTER, identifier) == "approved"
    assert first["purchase_order"]["status"] == "open"


def test_a_rejection_is_equally_terminal_and_emits_no_purchase_order() -> None:
    """Rejection is the same authorization decision and a different domain outcome.

    Nothing is created, so there is no order in the result — which is what
    `purchase_order` being absent rather than `null` says: the record does not
    exist, rather than existing empty.
    """
    identifier = _raise(SUBMITTER, "480.00")

    decided = _permitted(APPROVER, identifier, "reject")

    assert decided["requisition"]["status"] == "rejected"
    assert "purchase_order" not in decided
    assert _refused(APPROVER, identifier)["reason"] == "already_decided"


def test_a_foreign_row_and_a_row_that_never_existed_answer_byte_identically() -> None:
    """The empty join and the foreign row converge, on the write path this time.

    The handler passes the hydration step's answer straight through — `None`
    included — so it cannot tell the two apart because it never looks. The
    convergence itself is layer 2's single return site, asserted structurally in
    `tests/authorization/test_purity.py`; what is asserted here is that the tool
    hydrating a row for a *decision* reaches that same site.

    The request identifier is the same on both, so the two envelopes differ in
    the `id` argument alone.
    """
    identifier = _raise(SUBMITTER, "480.00")

    foreign = _decide(OUTSIDER, identifier)
    absent = _decide(OUTSIDER, seeded_requisitions.ABSENT_IDENTIFIER)

    assert foreign.status_code == absent.status_code
    assert foreign.content == absent.content, (foreign.text, absent.text)
    assert rpc.result(foreign)["structuredContent"]["reason"] == "not_found"
    # A refused decision leaves the row where it was, so a probe writes nothing.
    assert _status(SUBMITTER, identifier) == "submitted"


def test_a_token_without_the_deciding_scope_is_refused_before_the_handler_runs() -> None:
    """The first denial class: a `403` naming the scope the caller must acquire.

    Gate 5 refuses it, so nothing is hydrated and nothing is decided. The scope
    is derived from the capability the tool declares, so what the challenge names
    and what `scopes_supported` publishes cannot drift.
    """
    identifier = _raise(SUBMITTER, "480.00")

    response = rpc.call_tool(
        TOOL,
        {"id": identifier, "decision": "approve"},
        token=mint(APPROVER, ["erp.read"]).access_token,
    )

    assert response.status_code == httpx2.codes.FORBIDDEN
    parameters = rpc.challenge(response)
    assert parameters["error"] == "insufficient_scope"
    assert parameters["scope"] == "erp.decide"
    assert parameters["resource_metadata"] == rpc.METADATA_URL
    assert _status(SUBMITTER, identifier) == "submitted"


def test_the_scope_present_and_the_role_absent_is_a_protocol_error() -> None:
    """The middle denial class, reachable at the wire for the first time.

    #39 shipped two tools gated by scope alone and reported this as an honest
    limit: `role_missing` was declared, shaped and unreachable until a role-gated
    tool existed. This is that tool.

    **A `403` here would be a lie.** It would carry a header instructing the
    client to acquire a scope it already holds, producing an identical token and
    an identical refusal — a loop. So it is a JSON-RPC error, which the
    specification reserves for what a model is *less* likely to be able to fix,
    and the remedy is an administrator granting a role.

    Reachable only because ADR-0007 gives Priya Raman `approver` in the realm and
    no ERP role: the realm will issue her `erp.decide`, and the server will not
    stand behind it.
    """
    identifier = _raise(SUBMITTER, "480.00")

    error = rpc.error(_decide(SUBMITTER, identifier))

    assert error["code"] == -31010
    assert error["data"] == {
        "reason": "role_missing",
        "remedy": "administrator_grant",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": False,
    }
    assert _status(SUBMITTER, identifier) == "submitted"


def test_a_decision_the_enum_forbids_is_a_protocol_error_and_not_a_refusal() -> None:
    """Invalid params, because nothing was authorized or denied.

    A third word for `decision` is a caller's mistake rather than a decision
    about them, so it answers `-32602` and carries no `reason` — giving it one
    would amend a closed vocabulary for a spelling mistake.
    """
    identifier = _raise(SUBMITTER, "480.00")

    assert rpc.error(_decide(APPROVER, identifier, "maybe"))["code"] == -32602
    assert _status(SUBMITTER, identifier) == "submitted"


def test_a_refused_caller_is_answered_before_their_other_arguments_are_read() -> None:
    """The chain runs first, so a refusal cannot be told apart from a refusal with a typo.

    The same forbidden `decision` the test above answers `-32602` for. Sent by
    somebody the chain refuses, it never gets that far: what comes back is their
    refusal, unchanged. `submit_requisition` keeps the same order — the chain,
    then the arguments — and the identifier is the one exception, because
    hydration cannot happen without one.
    """
    identifier = _raise(SUBMITTER, "480.00")

    assert _refused(OUTSIDER, identifier, "maybe")["reason"] == "not_found"
    assert rpc.error(_decide(SUBMITTER, identifier, "maybe"))["code"] == -31010


def test_mixed_verdicts_arrive_in_one_result_body() -> None:
    """Some items permitted, some refused, in one answer — and one wire shape.

    ADR-0002 earned a streamed response mode on exactly this call and then cut
    it; what the mixed batch demonstrates now is the fold. Three items, three
    answers, in the order they were named: one decided, one refused by a rule
    that reads the row, and one refused for a row that — as far as this caller
    can tell — is not there.

    **The result is marked in error because one of the three was refused.** That
    is the reading a single-item refusal already has, applied to a call with more
    than one item on it: a model is told there is something here to act on, and
    per-item idempotency is what makes the retry it invites harmless.
    """
    decided = _raise(SUBMITTER, "480.00")
    refused = _raise(SUBMITTER, WELL_ABOVE)

    answers, marked = _answers(APPROVER, [decided, refused, seeded_requisitions.ABSENT_IDENTIFIER])

    assert marked is True
    assert answers[0]["requisition"]["id"] == decided
    assert answers[0]["requisition"]["status"] == "approved"
    assert answers[1]["reason"] == "over_threshold"
    assert answers[2]["reason"] == "not_found"
    # A refused item decides nothing, and a permitted one beside it is decided
    # anyway: the items are independent, which is what makes them N outcomes.
    assert _status(SUBMITTER, refused) == "submitted"


def test_an_item_named_twice_is_answered_twice() -> None:
    """*Outcomes equal items requested* holds against the caller's own repetition.

    The second answer is `already_decided`, because the first has already
    happened — per-item idempotency inside one call rather than between two. The
    failure this forbids is a batch that de-duplicated its own list, which would
    answer twice as far as the count goes and once as far as the caller's second
    item goes.
    """
    identifier = _raise(SUBMITTER, "480.00")

    answers, marked = _answers(APPROVER, [identifier, identifier])

    assert marked is True
    assert answers[0]["requisition"]["status"] == "approved"
    assert answers[1] == {
        "reason": "already_decided",
        "remedy": "none",
        "retry_identical_helps": False,
        "retry_as_other_person_helps": False,
    }


def test_a_caller_level_refusal_replaces_the_whole_response() -> None:
    """The axis ADR-0002 drew, with more than one item on the call for the first time.

    A refusal that depends on the caller cannot ride in a result body: it is a
    `-31010`, and a JSON-RPC error is the response rather than something inside
    one. So the batch answers once, not once per item — and the reason it must is
    mechanical rather than stylistic, since a protocol-error denial class has no
    rendering inside a folded body at all.

    Priya Raman is the one Person who can reach it: the realm gives her
    `approver` and the server gives her no ERP role, so she carries `erp.decide`
    to a role gate that refuses her.
    """
    first = _raise(SUBMITTER, "480.00")
    second = _raise(SUBMITTER, "480.00")

    error = rpc.error(_decide_all(SUBMITTER, [first, second]))

    assert error["code"] == -31010
    assert error["data"]["reason"] == "role_missing"
    # Whole-call, so neither item was looked at, let alone decided.
    assert _status(SUBMITTER, first) == "submitted"
    assert _status(SUBMITTER, second) == "submitted"


def test_a_list_the_schema_forbids_is_a_protocol_error_and_not_a_refusal() -> None:
    """An empty batch and an oversized one, both invalid params.

    Neither is a decision about the caller, so neither carries a `reason`. The
    empty list is refused rather than answered with nothing, because a call that
    named no item and got no answer is indistinguishable from a batch that
    dropped every item it was given — and *outcomes equal items requested* is the
    invariant that distinction is the whole of.

    The ceiling is enforced here rather than only declared, for the reason every
    other argument on this stack is: nothing validates arguments against a
    published `inputSchema`, so a rule a model reads and a rule the server keeps
    are two rules unless one of them is written twice.
    """
    identifier = _raise(SUBMITTER, "480.00")

    assert rpc.error(_decide_all(APPROVER, []))["code"] == -32602
    assert rpc.error(_decide_all(APPROVER, [identifier] * 21))["code"] == -32602
    assert _status(SUBMITTER, identifier) == "submitted"


def test_a_single_item_decision_answers_application_json() -> None:
    """One wire shape, on the tool that used to be the reason there were two.

    ADR-0002 earned the streamed response mode on this tool alone — *"a batch is
    N independent decisions with N independent outcomes"* — and then took its own
    option 5 and cut it, because no proof tier opened a stream, asserted on one,
    or depended on one. So the mode is not chosen per call: **every POST is
    answered `application/json`**, and the register's *No streamed response mode*
    interpretation carries the reading — the `MUST` naming both modes binds a
    client's ability to read them, never a server's obligation to produce one.

    The request asks for both, as a faithful client does, which is what makes the
    answer a decision rather than the only thing that would parse.
    """
    identifier = _raise(SUBMITTER, "480.00")

    response = _decide(APPROVER, identifier)

    assert "text/event-stream" in rpc.TRANSPORT_HEADERS["accept"]
    assert response.headers["content-type"].split(";")[0] == "application/json"

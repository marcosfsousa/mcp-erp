"""`submit_requisition` is scope-only, and the cost centre is not an argument.

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

The scenario this is *not* is `state_handle_hijack`: that row is a refused write
against a named resource, and this tool has no resource at all. Its falsifier
arrived with the first write that takes one — `approve_requisition`, at #40, in
`tests/attack_suite/test_state_handle_hijack.py`.

**The thing being asserted is an absence.** ADR-0002 designed the cost-centre
input out and ADR-0003 closed the question that would have brought it back, so
an out-of-partition write is *inexpressible* rather than refused. That is a
claim about the schema and about where the value comes from — so it is checked
in both places: the declaration has no such property, and the row that comes
back carries the submitter's own centre whoever submits.
"""

from collections.abc import Iterator
from typing import Any

import httpx2
import pytest

import fixtures
import requisitions as visible
import rpc
from tokens import Minted, mint

TOOL = "submit_requisition"

VENDOR = "Bauer Facility Services"
"""One of the four the input schema enumerates, by name rather than identifier.

`list_vendors` was cut for demonstrating no authorization behaviour, so the tool
definition is the lookup — which only works if what it enumerates is what a
reader recognises.
"""

ARGUMENTS: dict[str, Any] = {
    "vendor": VENDOR,
    "amount": "480.00",
    "currency": "EUR",
    "description": "Quarterly window cleaning",
}
"""Everything the caller supplies, which is everything the server cannot."""


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Start from the generated fixtures, so a submission is observably new.

    This module writes, unlike the two read suites, and the reload is what keeps
    it from depending on whatever a previous module left behind. It still does
    not isolate rows between tests — ADR-0003 chose a wipe per run rather than
    per row, and the alternative it rejected is a test-only reset route on a
    server whose entire subject is authorization.
    """
    fixtures.load()
    yield


def _submit(minted: Minted, arguments: dict[str, Any] | None = None) -> httpx2.Response:
    """One `submit_requisition` call over the wire."""
    return rpc.call_tool(
        TOOL, ARGUMENTS if arguments is None else arguments, token=minted.access_token
    )


def _written(username: str) -> dict[str, Any]:
    """The row one Person's submission produced."""
    result = rpc.result(_submit(mint(username, ["erp.write"])))

    assert result["isError"] is False, result
    row: dict[str, Any] = result["structuredContent"]["requisition"]
    return row


def test_the_declaration_takes_no_cost_centre() -> None:
    """The input schema is the assertion, because the absence is the design.

    A free-text centre would leak which centres exist — its refusal is the
    probing surface ADR-0002 designed out — and an enumerated one would publish
    the organisation's shape in a document `tools/list` hands to anyone holding
    the scope. So there is no property to send, and `additionalProperties: false`
    is what makes sending one anyway not a way in.
    """
    tools = rpc.result(
        rpc.post("tools/list", token=mint("priya.raman", ["erp.write"]).access_token)
    )
    (tool,) = [entry for entry in tools["tools"] if entry["name"] == TOOL]

    assert set(tool["inputSchema"]["properties"]) == {
        "vendor",
        "amount",
        "currency",
        "description",
    }
    assert tool["inputSchema"]["additionalProperties"] is False
    # Enumerated by name, generated from the vendor rows, so the tool definition
    # cannot drift from the data it is a lookup for.
    assert VENDOR in tool["inputSchema"]["properties"]["vendor"]["enum"]


def test_a_submission_is_charged_to_the_submitter_s_own_cost_centre() -> None:
    """Priya Raman holds CC-4100 and holds no ERP role at all.

    She is the case ADR-0003 means by *submitting is gated by scope alone*: a
    token carrying `erp.write` is the whole of what she needs, and the centre
    charged is the directory's answer rather than anything she said.
    """
    row = _written("priya.raman")

    assert row["cost_centre"] == "CC-4100"
    assert row["submitted_by"] == {"id": "priya-raman", "label": "Priya Raman"}
    assert row["status"] == "submitted"
    assert row["amount"] == "480.00"
    assert row["currency"] == "EUR"


def test_two_people_sending_identical_arguments_are_charged_differently() -> None:
    """The same call, twice, and the answer differs on the one field nobody sent.

    This is what *inexpressible* means, stated as a pair rather than as a single
    row a reader has to take on trust: there is no argument either of them could
    have varied to be charged to the other's centre, and the field that differs
    is the one the schema does not carry.
    """
    theirs = _written("priya.raman")
    ours = _written("mei.tanaka")

    assert theirs["cost_centre"] == "CC-4100"
    assert ours["cost_centre"] == "CC-4300"
    assert theirs["id"] != ours["id"]


def test_the_auditing_role_writes_to_its_own_centre_like_anyone_else() -> None:
    """Breadth is a read widening, never a write grant.

    `partition_bypass` is empty on this Action, so Anna Lindqvist's `auditor` —
    which reads three centres of three — buys her nothing here. She submits
    against CC-4200 because that is the centre she holds, exactly as a person
    holding no role at all does.

    This is the assertion the read side gets for free and the write side does
    not: ADR-0013 says nothing in the type will object to `{auditor}` on a write,
    and no matrix row reaches that mistake because row scoping runs after a gate
    a bypass does not open. Here it is reached.
    """
    assert _written("anna.lindqvist")["cost_centre"] == "CC-4200"


def test_a_token_without_the_write_scope_is_refused_before_anything_is_written() -> None:
    """The first denial class: `403`, naming the scope the caller must acquire.

    Gate 5 refuses it, so the handler never runs and the store is never reached.
    A `403` is honest here in the way it would be a lie on a missing role — the
    caller genuinely does not hold `erp.write`, and re-authorizing is genuinely
    the remedy.
    """
    before = visible.visible_to("priya.raman")

    response = _submit(mint("priya.raman", ["erp.read"]))

    assert response.status_code == httpx2.codes.FORBIDDEN
    parameters = rpc.challenge(response)
    assert parameters["error"] == "insufficient_scope"
    assert parameters["scope"] == "erp.write"
    assert parameters["resource_metadata"] == rpc.METADATA_URL
    assert visible.visible_to("priya.raman") == before


def test_an_argument_the_schema_forbids_is_a_protocol_error_and_not_a_refusal() -> None:
    """Invalid params, because nothing was authorized or denied.

    A vendor the enum does not carry is a caller mistake rather than a decision
    about them, so it answers `-32602` and carries no `reason` — giving it one
    would amend a closed vocabulary for a spelling mistake, and would tell a
    model to route around a wall that is not there.
    """
    response = _submit(mint("priya.raman", ["erp.write"]), {**ARGUMENTS, "vendor": "Acme"})

    assert rpc.error(response)["code"] == -32602


@pytest.mark.parametrize(
    "amount",
    [
        # `Decimal` accepts every one of these and the declared pattern accepts
        # none of them, which is why the handler matches the pattern rather than
        # parsing and hoping the two agree.
        "1e2",
        "+5",
        " 1.5",
        "1_0",
        # Three decimal places: `numeric(12, 2)` would round it silently, so the
        # caller would be charged an amount they did not name.
        "1.555",
        # Eleven integer digits: one more than the column holds, so this reached
        # the database and came back as an integrity error rather than as a
        # message about the argument.
        "99999999999",
        # The pattern admits `0`; `CHECK (amount > 0)` is the rule it declines to
        # express, and the handler carries that one separately.
        "0",
        "-1",
    ],
)
def test_an_amount_the_pattern_forbids_never_reaches_the_column(amount: str) -> None:
    """The declared pattern is the rule, and the handler enforces *that* rule.

    Every value here is one `Decimal` would have parsed happily. Two of them
    change what the caller gets rather than merely being sloppy — a third decimal
    place is rounded by the column, and an eleventh integer digit overflows it —
    so a handler that parsed instead of matching would answer a database error
    where the declaration promised invalid params.
    """
    before = visible.visible_to("priya.raman")

    response = _submit(mint("priya.raman", ["erp.write"]), {**ARGUMENTS, "amount": amount})

    assert rpc.error(response)["code"] == -32602
    assert visible.visible_to("priya.raman") == before

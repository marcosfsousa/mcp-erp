"""What drives one matrix row over the wire, and what it asserts about the answer.

`tests/matrix/` is driven from the table in its entirety: every file beside this
one is a parametrised loop over the rows `docs/decision-matrix/matrix.yaml`
declares for one tool, and this module is what a row means. Nothing here decides
*what* is expected — the table does — and nothing in the table decides *how* an
expectation is checked.

**The shape of a refusal is derived, never restated.** A row states a `reason`
and nothing else, and :func:`_refusal` reads the `Reason` record the two layers
declare to learn which of ADR-0002's three shapes to look for, which remedy the
payload must carry and what both retry booleans must say. So the mapping is used
here and asserted in exactly one place —
`test_the_reason_mapping.py::test_the_union_of_both_layers_maps_to_the_shapes_adr_0002_fixed`
— which is ADR-0003's *exactly one dedicated test* holding rather than being
described.

**Every row drives real HTTP against Compose with a real token.** ADR-0008 put
the whole table there: a matrix row green in-process while the wire path goes
unexercised is a test passing for the wrong reason, in its least visible form.
The token is minted through the real authorization code flow by `tokens.py`;
nothing here shortcuts it.

**There is no expected-response-mode column.** ADR-0013 specified one and #37
dropped it when ADR-0002 cut the streamed mode: every POST is answered
`application/json`, so the column's every value would be the same, and a field
that changes no assertion is what the governing rule refuses. #43's ticket text
predates that cut and still lists it; `tests/matrix/README.md` carries the
reasoning.
"""

from __future__ import annotations

from typing import Any, Final

import httpx2

import fixtures
import rpc
from mcp_erp.authorization import REASONS as AUTHORIZATION_REASONS
from mcp_erp.authorization import Action, DenialClass, Reason
from mcp_erp.purchase_to_pay import (
    approve_requisition,
    get_requisition,
    list_requisitions,
    record_invoice,
    submit_requisition,
)
from mcp_erp.purchase_to_pay.fixtures import MATRIX, Row, read_matrix
from mcp_erp.purchase_to_pay.reasons import REASONS as DOMAIN_REASONS
from tokens import mint

LISTING: Final = "tools/list"
"""The one call a row may name that is not a tool, spelled here and not in `src/`.

`tools/list` is layer 1's word. Layer 3's parser used to hold it so that it could
refuse a fixture on a call that names no resource, and it now states the three
tools that **do** hydrate one instead — every member a name layer 3 owns. Which
leaves the protocol method to be spelled where protocol methods are already
spelled: in a suite, beside `rpc.post("tools/list", ...)`.
"""

MATRIX_DEFINITION: Final = read_matrix((fixtures.REPO / MATRIX).read_text(encoding="utf-8"))
"""The table, parsed once at import by the layer whose vocabulary it speaks.

Read through `mcp_erp.purchase_to_pay.fixtures` rather than with a parser of its
own, because the fixture generator and this driver must agree about what a row
says — two readers of one file is two readings of it.
"""

REASON_RECORDS: Final = {reason.value: reason for reason in AUTHORIZATION_REASONS | DOMAIN_REASONS}
"""The union of both layers' declared reasons, keyed by the value a row states.

Layer 2 declares three and layer 3 four, with no lookup table anywhere — so this
is a lookup built *for the suite* out of the two declared sets, not a fifth place
the vocabulary is written down. It is also why this directory holds the mapping
test: building it imports the package the ejection command deletes.
"""

ACTIONS: Final[dict[str, Action[Any]]] = {
    list_requisitions.NAME: list_requisitions.ACTION,
    get_requisition.NAME: get_requisition.ACTION,
    submit_requisition.NAME: submit_requisition.ACTION,
    approve_requisition.NAME: approve_requisition.ACTION,
    record_invoice.NAME: record_invoice.ACTION,
}
"""Each tool's declared `Action`, which is where a challenge's `scope` comes from.

Derived from the capability the tool declares rather than written out, on
ADR-0012's rule that the scope string is never a literal: what the `403` names
and what `scopes_supported` publishes cannot drift, and a suite that hard-coded
`erp.read` would be the one hand-written scope string the attack suite forbids.
"""

SUBMISSION: Final = {
    "vendor": "Meridian Cloud Services",
    "amount": "480.00",
    "currency": "EUR",
    "description": "Quarterly window cleaning",
}
"""What a `submit_requisition` row sends, and it is the same for every such row.

Submitting takes no resource and no argument here changes an authorization
decision: the cost centre is the principal's and the schema has no field for it,
and the amount is read by nothing until a decision is taken on the row later. A
row that varied these would be declaring a variable that moves no expectation,
which is the same thing the `given` guardrail forbids one column along.
"""


def rows_for(tool: str) -> tuple[Row, ...]:
    """Every row the table declares for one tool, in declaration order.

    Raises:
        AssertionError: The tool has no rows. Every tool the server declares is
            named by at least one row — a matrix invariant — so an empty result
            is a table that lost them rather than a tool that needs none.
    """
    rows = tuple(row for row in MATRIX_DEFINITION.rows if row.tool == tool)
    assert rows, f"the matrix declares no row for {tool!r}"
    return rows


def name(row: Row) -> str:
    """The row's own identifier, which is what `pytest -v` prints for it.

    So a red check names the expectation that broke rather than a parameter
    index, and the name it prints is the one `matrix.yaml` and the fixture
    rendering both use.
    """
    return row.id


def drive(row: Row) -> None:
    """Perform one row and assert what it expects.

    Two halves, and the split is ADR-0002's own: what a call *does* depends on
    the tool, and what a refusal *looks like* depends only on the reason. So the
    tool decides the request and the reason decides the assertion, and neither
    knows about the other.
    """
    if row.tool == LISTING:
        _listing(row)
        return

    response = _call(row)
    if row.expect.permitted:
        _permitted(row, response)
        return

    _refusal(row, response)


def _listing(row: Row) -> None:
    """A `tools/list` row: exact set equality over the names the filter returns.

    Set equality rather than membership, because every one of these rows makes an
    *and nothing else* claim — a token holding one capability reaches its own
    side and neither more nor less, and a membership assertion would pass on a
    listing that returned everything.
    """
    listing = rpc.result(rpc.post("tools/list", token=_token(row)))
    tools = listing["tools"]
    assert isinstance(tools, list)

    assert row.expect.tools is not None
    assert {tool["name"] for tool in tools} == set(row.expect.tools)


def _call(row: Row) -> httpx2.Response:
    """One `tools/call` for this row, with the arguments its tool takes.

    The raw response rather than a parsed result, because a refusal's shape is
    half of what is asserted: a `403` carries no envelope at all, so a helper
    that unwrapped one would make two of the three shapes unreachable.
    """
    return rpc.call_tool(row.tool, _arguments(row), token=_token(row))


def _arguments(row: Row) -> dict[str, Any]:
    """What this row's tool is called with.

    The resource is not a column: a row that names a `given` acts on the fixture
    that block produces, and a row without one acts on the identifier no row
    carries. That rule is applied here, once, so no test file restates it.
    """
    if row.tool == list_requisitions.NAME:
        return {}
    if row.tool == submit_requisition.NAME:
        return dict(SUBMISSION)
    if row.tool == record_invoice.NAME:
        return {"id": _order_identifier(row)}
    if row.tool == approve_requisition.NAME:
        # A one-item batch, which layer 1 renders directly rather than folding —
        # so the answer this row reads back is the outcome itself. The fold is
        # `tests/wire/test_the_fold.py`'s subject and is a property of a call's
        # cardinality rather than of a caller, which is why no row carries one.
        return {"ids": [_identifier(row)], "decision": "approve"}
    return {"id": _identifier(row)}


def _identifier(row: Row) -> str:
    """The requisition this row acts on, or the identifier no row carries."""
    if row.given is None:
        return fixtures.ABSENT_IDENTIFIER
    return fixtures.owned_by(row.id).id


def _order_identifier(row: Row) -> str:
    """The purchase order this row acts on, or the identifier no order carries."""
    if row.given is None:
        return fixtures.ABSENT_ORDER
    return fixtures.order_owned_by(row.id).id


def _token(row: Row) -> str:
    """A real access token for this row's principal, minted through the real flow.

    Person x scope set, which is what the table varies. `openid` rides on every
    token and reaches nothing on its own, so the scope set a row declares is the
    whole of what it adds.
    """
    return mint(row.principal.person, list(row.principal.scopes)).access_token


def _permitted(row: Row, response: httpx2.Response) -> None:
    """A row the chain let through, plus whatever else its tool's row claims.

    Every permitted row asserts the same first thing — a result not marked in
    error — and three tools add one claim each on top of it. Those extra claims
    are the ones a permit alone would not catch: a listing that returned the
    wrong partition, and a submission stamped with the wrong one.
    """
    result = rpc.result(response)
    assert result["isError"] is False, result
    payload = result["structuredContent"]

    if row.tool == list_requisitions.NAME:
        assert row.expect.visible_partitions is not None
        # Set equality over returned identifiers, which is what ADR-0003 fixed
        # read rows on: row scoping is a question of which rows come back, and no
        # entity carries a timestamp, so there is no order to assert.
        assert {entry["id"] for entry in payload["requisitions"]} == fixtures.identifiers_in(
            *row.expect.visible_partitions
        )
        return

    if row.tool == submit_requisition.NAME:
        assert row.expect.charged_to is not None
        # The partition is supplied from the principal rather than decided, and
        # there is no argument to prefer over it — which is what makes an
        # out-of-partition write inexpressible rather than refused.
        assert payload["requisition"]["cost_centre"] == row.expect.charged_to
        return

    if row.tool == get_requisition.NAME:
        assert payload["requisition"]["id"] == _identifier(row)


def _refusal(row: Row, response: httpx2.Response) -> None:
    """A refused row, checked against the shape its reason record declares.

    The row states a reason; everything below is read off the record that reason
    is, so a change to ADR-0002's mapping is a change in one declaration and not
    in thirty-three expectations.

    Raises:
        AssertionError: The wire took a shape the reason does not declare.
    """
    assert row.expect.reason is not None
    reason = REASON_RECORDS[row.expect.reason]

    if reason.denial_class is DenialClass.CHALLENGE:
        _challenge(row, response, reason)
        return

    if reason.denial_class is DenialClass.PROTOCOL_ERROR:
        error = rpc.error(response)
        assert error["code"] == -31010
        assert error["data"] == _payload(reason)
        return

    result = rpc.result(response)
    assert result["isError"] is True, result
    assert result["structuredContent"] == _payload(reason)


def _challenge(row: Row, response: httpx2.Response, reason: Reason) -> None:
    """The `403` shape: a header, and no envelope at all.

    The scope it names is derived from the capability the tool declares, so this
    asserts the agreement between the challenge and the declaration rather than
    against a string written here — and the metadata address is the one every
    challenge points at.
    """
    assert response.status_code == httpx2.codes.FORBIDDEN, response.text

    parameters = rpc.challenge(response)
    assert parameters["error"] == reason.value
    assert parameters["scope"] == ACTIONS[row.tool].scope
    assert parameters["resource_metadata"] == rpc.METADATA_URL


def _payload(reason: Reason) -> dict[str, Any]:
    """The four fields a structured refusal carries, read off the record.

    Not imported from `mcp_erp.transport.refusals`, deliberately. That function
    is the code under test: a suite calling it would assert that layer 1 agrees
    with itself, where this asserts that what layer 1 rendered says what the
    reason the two domains declared says.
    """
    return {
        "reason": reason.value,
        "remedy": reason.remedy.value,
        "retry_identical_helps": reason.retry_identical_helps,
        "retry_as_other_person_helps": reason.retry_as_other_person_helps,
    }

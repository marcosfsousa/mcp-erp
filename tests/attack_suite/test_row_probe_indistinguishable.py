"""`row_probe_indistinguishable` — a named row answers the same whether it exists or not.

Scenario: `row_probe_indistinguishable`, `basis: adr`, sourced to ADR-0002
§Disclose the shape of the API; never the contents of the database.

    removal: Return a distinguishable refusal for "exists but not yours" versus
             "never existed".

The **named** half of the refusal contract `list_partition_scoped` covers the
discovered half of:

    A resource **named** in the request is refused, never omitted.
    A resource **discovered** by listing is omitted, never refused.

**Byte-identity on the wire, and constant time is not measured.** ADR-0013 puts
the claim at two altitudes and this is the outer one: the two responses are
compared as bytes. The inner one is a single-return-site property asserted
structurally in `tests/authorization/test_purity.py`, over layer 2's source
rather than over its behaviour. Neither measures timing and neither claims it —
a measured-timing assertion against Compose competes with container scheduling
and jitter, flakes, and a flaky required job is the one that would earn an
exemption the ruleset does not offer.

**Reached by guessing, not by being handed the identifier.** ADR-0003 takes a
deliberate deviation from a specification `SHOULD` — identifiers are sequential
and legible — precisely so this scenario can guess a foreign one. Following the
`SHOULD` would have turned a demonstrated defence into an asserted one.
"""

from collections.abc import Iterator

import httpx2
import pytest
from scenarios import exercises

import fixtures
import rpc
from mcp_erp.authorization import NOT_FOUND
from refusal_records import refusal_body
from tokens import mint

TOOL = "get_requisition"

PROBER = "tomas.weber"
"""Tomas Weber holds CC-4100, so every CC-4300 row is foreign to him."""

OWNER = "mei.tanaka"
"""Mei Tanaka holds CC-4300, and is why the foreign row is provably a row.

Without an owner this suite would pass unchanged against an empty table, at
which point it compares *never existed* with *never existed* and asserts
nothing.

**The third centre rather than the second**, so that the auditing assertion
below is breadth rather than membership: Anna Lindqvist holds CC-4200, which is
neither the prober's centre nor this row's, so the only thing that can carry her
across is the bypass role.
"""

FOREIGN_CENTRE = "CC-4300"


@pytest.fixture(scope="module", autouse=True)
def requisitions() -> Iterator[None]:
    """Wipe and reload the rows once before this module, on ADR-0003's shape.

    Module-scoped rather than session-scoped for the reason
    `test_list_partition_scoped` states: `tests/conftest.py` already exists and
    the types job runs over `tests/`, so a second file of that name would be a
    duplicate module to mypy.
    """
    fixtures.load()
    yield


def _foreign_identifier() -> str:
    """One generated identifier in a cost centre the prober does not hold.

    Asked for by partition rather than by identifier, since #43 the fixtures are
    generated from `matrix.yaml` and their identifiers are ordinals the generator
    renumbers when a row is inserted. What this scenario needs is *a row he
    cannot see*, which is a property of the partition and of nothing else.
    """
    return fixtures.a_row_in(FOREIGN_CENTRE)


def _answer(username: str, identifier: str) -> httpx2.Response:
    """What `get_requisition` answers one Person naming one identifier.

    The raw response rather than a parsed result, because the scenario
    compares bytes. Named for the answer rather than for the refusal: half
    the calls below are permitted, and those are the ones that make the
    refusals mean something.
    """
    minted = mint(username, ["erp.read"])
    return rpc.call_tool(TOOL, {"id": identifier}, token=minted.access_token)


@exercises("row_probe_indistinguishable")
def test_the_foreign_row_is_a_row_somebody_can_see() -> None:
    """The precondition, held by a test rather than by trust.

    A suite asserting that two refusals agree passes just as well when the row
    it calls foreign does not exist at all — at which point it is comparing
    *never existed* with *never existed* and asserting nothing.
    """
    result = rpc.result(_answer(OWNER, _foreign_identifier()))

    assert result["isError"] is False, result
    assert result["structuredContent"]["requisition"]["cost_centre"] == FOREIGN_CENTRE


@exercises("row_probe_indistinguishable")
def test_a_foreign_row_and_a_row_that_never_existed_answer_byte_identically() -> None:
    """The scenario. Same bytes, so the answer carries no bit about existence.

    The request identifier is the same on both, which is what makes the
    comparison meaningful: a JSON-RPC response echoes it, so two calls that
    differed there would differ in their bodies for a reason that has nothing to
    do with what this row is about. `rpc.post` uses the same default for every
    call, so the two envelopes differ in the `id` argument alone.

    Headers are deliberately not compared. The gateway stamps which replica
    answered, and round robin means the two calls land on different ones — a
    property another suite exists to assert, and nothing to do with this one.
    """
    foreign = _answer(PROBER, _foreign_identifier())
    absent = _answer(PROBER, fixtures.ABSENT_IDENTIFIER)

    assert foreign.status_code == absent.status_code
    assert foreign.content == absent.content, (foreign.text, absent.text)


@exercises("row_probe_indistinguishable")
def test_the_refusal_is_a_refusal_rather_than_an_omission() -> None:
    """A **named** resource is refused, never omitted — the half this row owns.

    So the answer is a tool result marked in error carrying `not_found`, and not
    an empty success. The `not_found` reason and the `null` remedy are the whole
    of what a caller learns, and neither is a fact only the database holds.

    **`retry_as_other_person_helps` is the load-bearing field**, and it is read
    from the record rather than written out here. True would confirm that the row
    exists and that somebody else can see it — the existence oracle ADR-0002
    declined to ship, stated in the refusal itself rather than only in the bytes
    the test above compares. What holds it false is
    `tests/matrix/test_the_reason_mapping.py`, which checks `not_found`'s record
    against ADR-0002's table; what this asserts is that the wire carries what
    that record says — the half a copy written out here could not tell the
    difference about, because a copy agrees with a changed record by not moving.
    """
    result = rpc.result(_answer(PROBER, _foreign_identifier()))

    assert result["isError"] is True, result
    assert result["structuredContent"] == refusal_body(NOT_FOUND)


@exercises("row_probe_indistinguishable")
def test_the_auditing_role_reads_the_row_the_prober_cannot() -> None:
    """Breadth by role, at single-row granularity.

    `partition_bypass` is `{auditor}` on both read tools, so the same identifier
    that answers `not_found` to Tomas answers with the row to Anna. The pair is
    what makes the refusal a *decision* rather than a property of the row: one
    identifier, two callers, two answers.
    """
    result = rpc.result(_answer("anna.lindqvist", _foreign_identifier()))

    assert result["isError"] is False, result
    assert result["structuredContent"]["requisition"]["id"] == _foreign_identifier()

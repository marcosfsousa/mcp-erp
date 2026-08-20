"""The matrix's own invariants: the standing index, the guardrails, and the ladder.

`matrix.yaml` declares a `meta` block, and a count kept where it can be read and
not checked is what ADR-0011 caught drifting four times in one month. So every
number in it is asserted against the rows here — the index is standing because
something stands on it.

**Nothing in this file needs Compose**, and that is deliberate: it asks whether
the table is well formed, which is a question about two committed files rather
than about a running server. `Seed renders clean` runs it for that reason, beside
the re-render it already refuses a diff on — the same overlap ADR-0013 priced for
`tests/authorization/test_identity.py`, where a re-render plus diff catches a
hand-edited rendering and a test catches a broken generator. `Decision matrix
(wire)` collects it too, because it is in this directory and a suite that skipped
its own invariants when run whole would be a suite with a hole in it.

**The seed correspondence is checked here rather than closed by construction.**
The fixture generator reads `matrix.yaml` and never the seed, so a `given` block
states the cost centre its row is charged to. That duplicates a fact the
organisation rendering already holds — and duplication *by authorship* is what a
drift check is the right control for, where a generator reading both halves would
make the equality true by construction and untestable.
"""

import json
from collections import Counter
from decimal import Decimal
from typing import Any

import driver

import fixtures
from mcp_erp.authorization import REASONS as AUTHORIZATION_REASONS
from mcp_erp.purchase_to_pay.fixtures import (
    FIXTURE_RENDERING,
    LISTING,
    render_fixtures,
)
from mcp_erp.purchase_to_pay.organisation import ORGANISATION_RENDERING, read_organisation
from mcp_erp.purchase_to_pay.reasons import REASONS as DOMAIN_REASONS

MATRIX = driver.MATRIX_DEFINITION
META: dict[str, Any] = dict(MATRIX.meta)

LADDER: tuple[frozenset[str], ...] = (
    frozenset(),
    frozenset({"erp.read"}),
    frozenset({"erp.read", "erp.write"}),
    frozenset({"erp.read", "erp.write", "erp.decide"}),
)
"""The cumulative ladder of four, which is what a row reaches for by default.

Two people differing only in role, tested under the same rung, is the comparison
this table is built to make. A row that invented its own scope set would make its
result a fact about two variables at once.
"""

CITED = {
    frozenset({"erp.decide"}),
    frozenset({"erp.write"}),
}
"""The non-cumulative sets, each admitted by citing the row that needs it.

`{erp.decide}` is the deciding tool's, and the listing row that reaches it: the
claim is that the filter reads granted scope alone, and a token also carrying
read and write would show four tools beside the one the claim is about.
`{erp.write}` is the listing row that claims *and no read tool*, which
`{read,write}` cannot make.

#43's ticket named the first as the only one so far. It was written before #66
handed the tool listing's five assertions here, and the second arrives with them
— the rule operating as written rather than a breach of it.
"""


def _organisation() -> dict[str, str]:
    """Each seeded person's cost centre, from the rendering rather than the seed.

    The rendering, because that is what the database is loaded from at boot — so
    this compares the fixtures against the rows that will actually be there, not
    against a file one generator away from them.
    """
    document = json.loads((fixtures.REPO / ORGANISATION_RENDERING).read_text(encoding="utf-8"))
    return {person["subject"]: person["cost_centre"] for person in document["people"]}


def test_the_declared_total_and_the_ceiling_hold() -> None:
    """The index's headline number, and the bound that makes growth a decision.

    Crossing the ceiling reviews whether two rows are restating one branch rather
    than adding a row — it is not a cap on coverage, it is a prompt to look at the
    split rule the way `scenarios.yaml`'s soft ceiling of 35 is.
    """
    assert META["total"] == len(MATRIX.rows)
    assert len(MATRIX.rows) <= META["ceiling"]


def test_the_declared_index_agrees_with_the_rows_it_indexes() -> None:
    """Every count in `meta`, against the rows.

    Four separate splits — by tool, by reason, permitted, and how many rows own a
    fixture — because each is a different question a reader arrives with, and a
    single total answers none of them.
    """
    assert META["by_tool"] == dict(Counter(row.tool for row in MATRIX.rows))
    assert META["by_reason"] == dict(
        Counter(row.expect.reason for row in MATRIX.rows if row.expect.reason is not None)
    )
    assert META["allowed"] == sum(1 for row in MATRIX.rows if row.expect.allowed)
    assert META["fixtures"] == sum(1 for row in MATRIX.rows if row.given is not None)


def test_every_declared_reason_is_expected_by_at_least_one_row() -> None:
    """The table's floor, and what makes the closed vocabulary reachable.

    A reason no row expects is a value the exhibit declares and cannot
    demonstrate — which is precisely what ADR-0003 refused to let
    `already_invoiced` be until #42 shipped the tool that produces it. The
    mapping test one file along asserts what each reason *means*; this asserts
    that each is *reached*.
    """
    expected = {row.expect.reason for row in MATRIX.rows if row.expect.reason is not None}

    assert expected == {reason.value for reason in AUTHORIZATION_REASONS | DOMAIN_REASONS}


def test_every_tool_the_server_declares_is_named_by_a_row() -> None:
    """Five tools and the listing, each with at least one row.

    A tool with no row is a tool whose authorization behaviour this artifact says
    nothing about, and the count of five is ADR-0002's rather than this file's —
    it comes off the `Action` declarations, so a sixth tool fails here rather than
    shipping unexamined.
    """
    named = {row.tool for row in MATRIX.rows}

    assert named == set(driver.ACTIONS) | {LISTING}


def test_every_row_identifier_is_unique() -> None:
    """Row names key the fixture rendering and every `pytest -v` line.

    `read_matrix` refuses a duplicate as it parses, so this asserts the parser's
    refusal rather than restating it — a second identifier of the same name would
    have two fixtures and one lookup.
    """
    assert len({row.id for row in MATRIX.rows}) == len(MATRIX.rows)


def test_every_scope_set_is_on_the_ladder_or_is_one_of_the_two_cited() -> None:
    """Token shapes are bounded, and both directions of the bound are checked.

    A set that is neither on the ladder nor cited fails; and a cited set that no
    row uses fails too, because a standing exemption nothing needs is an
    exemption the next reader will treat as a licence.
    """
    used = {frozenset(row.principal.scopes) for row in MATRIX.rows}

    assert used <= set(LADDER) | CITED
    assert CITED <= used


def test_every_fixture_is_charged_to_its_submitters_own_centre() -> None:
    """A row that broke this would be data no tool could have produced.

    `submit_requisition` takes no cost centre and stamps the submitter's, so a
    fixture in someone else's centre is a row the exhibit asserts against and
    could never have written. It is the one fact `matrix.yaml` and the seed both
    hold, and this is the check that keeps them equal.
    """
    centres = _organisation()

    for row in MATRIX.rows:
        if row.given is None:
            continue
        assert row.given.submitted_by in centres, row.id
        assert row.given.cost_centre == centres[row.given.submitted_by], row.id


def test_every_identity_a_fixture_names_is_someone_the_seed_declares() -> None:
    """Submitters, approvers and recorders alike, against the same rendering.

    The database would refuse an unknown subject at load time with a foreign-key
    violation, which is a true refusal wearing the wrong diagnosis: a matrix row
    naming somebody who does not exist is a table defect, and it should read as
    one before Compose is anywhere near it.
    """
    centres = _organisation()

    for row in MATRIX.rows:
        given = row.given
        if given is None:
            continue
        for subject in (given.submitted_by, given.approved_by, given.recorded_by):
            assert subject is None or subject in centres, (row.id, subject)


def test_every_amount_is_a_positive_decimal_the_column_can_hold() -> None:
    """Two decimal places at most, because the column is `numeric(12, 2)`.

    A third place is silently rounded on the way in, which would leave a
    threshold row asserting against an amount the database never held. `Decimal`
    is far more permissive than the tool's own declared pattern, so the shape is
    checked rather than merely parsed — the same argument the handler makes.
    """
    for row in MATRIX.rows:
        if row.given is None:
            continue
        amount = Decimal(row.given.amount)
        assert amount > 0, row.id
        # `as_tuple().exponent` is an integer for every finite decimal and one of
        # three strings for the special values, which a positive amount is not —
        # so the narrowing is a fact about the assertion above it.
        exponent = amount.as_tuple().exponent
        assert isinstance(exponent, int)
        assert -exponent <= 2, row.id


def test_the_committed_rendering_is_what_the_matrix_renders() -> None:
    """The generator half of the drift check, in process.

    `Seed renders clean` re-renders on a Linux runner and refuses a diff, which
    is the comparison that spans two machines. This asserts the same equality
    where a developer meets it, so a hand-edited fixture fails `pytest
    tests/matrix` before it ever reaches a runner.
    """
    committed = (fixtures.REPO / FIXTURE_RENDERING).read_text(encoding="utf-8")

    assert render_fixtures(MATRIX) == committed


def test_the_renderer_is_byte_stable() -> None:
    """Rendered twice from one parse, identical both times.

    Sorted keys, rows in a fixed order, nothing generated and nothing dated — the
    same property layer 2's renderer is held to, because one drift check polices
    all four renderings and a check that flakes on any of them is a required
    check somebody will want turned off.
    """
    assert render_fixtures(MATRIX) == render_fixtures(MATRIX)


def test_the_organisation_seed_still_parses_the_people_this_table_names() -> None:
    """The rendering read above is the one the seed produces, not a stale copy.

    Cheap, and it closes the one gap in the check above it: comparing fixtures to
    a rendering says nothing if the rendering itself has drifted from the seed.
    That drift is `Seed renders clean`'s subject, and asserting the two agree here
    is what lets this file trust the map it reads.
    """
    seed = (fixtures.REPO / "docs/organisation/seed.yaml").read_text(encoding="utf-8")
    organisation = read_organisation(seed)

    assert {person.subject: person.cost_centre for person in organisation.people} == _organisation()

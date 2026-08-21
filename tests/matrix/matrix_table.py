"""The decision matrix, rendered for the write-up — the other half of map constraint `4`.

Map constraint `4` has said since the charting session that the matrix is *"one
source rendering into both tests and the write-up"*. The tests half is this
directory; `mcp_erp.purchase_to_pay.fixtures` is the fixtures half. This is the
write-up half, and ADR-0014 §*What a machine can keep true, a machine keeps true*
is the decision that commissioned it. **The rendering is committed and
`Seed renders clean` refuses a diff**, like every other rendering here.

**It restates nothing.** Every cell is read from `docs/decision-matrix/matrix.yaml`
through the parser `tests/matrix/driver.py` and the fixture generator already
share, and the two columns that are not literally in the table are derived the
way the driver derives them:

*What the fixture is* comes from :func:`~mcp_erp.purchase_to_pay.fixtures.fixtures_for`,
so a row's *Acts on* cell names the identifier the seeded database actually
carries rather than a number typed here.

*What shape a refusal takes* comes from the `Reason` record the two layers
declare — ADR-0002's mapping, used here for the same reason `driver.py` uses it:
a row states a reason and nothing else, and everything that follows from the
reason follows in one place.

**The counts are derived from the rows, never read from `meta`.** `meta` is the
standing index a reader walks and
`tests/matrix/test_the_matrix_holds_together.py` is what holds it to the rows; a
rendering that copied it would publish a number nothing had checked, which is the
artifact ADR-0011 caught drifting four times in one month.

**No prose.** ADR-0014 keeps the connective narrative hand-written and free, and
#92 is explicit that none of it is this ticket's. What this file writes is a
title, a provenance line, an index and the rows.

It imports nothing from `tests/`, which is what lets it run as a script from the
repository root::

    uv run python tests/matrix/matrix_table.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from mcp_erp.authorization import REASONS as AUTHORIZATION_REASONS
from mcp_erp.authorization import DenialClass, Reason
from mcp_erp.purchase_to_pay import approve_requisition, get_requisition, record_invoice
from mcp_erp.purchase_to_pay.fixtures import MATRIX, Given, Matrix, Row, fixtures_for, read_matrix
from mcp_erp.purchase_to_pay.reasons import REASONS as DOMAIN_REASONS

REPO: Final = Path(__file__).resolve().parents[2]
"""The checkout, from this file's own location."""

RENDERING: Final = "docs/decision-matrix/matrix.md"
"""Where the rendered table is committed, beside the source it renders."""

REASON_RECORDS: Final = {reason.value: reason for reason in AUTHORIZATION_REASONS | DOMAIN_REASONS}
"""The union of both layers' declared reasons, keyed by the value a row states.

Built for this rendering out of the two declared sets, exactly as
`tests/matrix/driver.py` builds it for the suite — not a lookup table either
layer holds, because ADR-0013 is that there is none.
"""

SHAPES: Final = {
    DenialClass.CHALLENGE: "`403` with a `WWW-Authenticate` challenge",
    DenialClass.PROTOCOL_ERROR: "a JSON-RPC error, `-31010`",
    DenialClass.TOOL_RESULT: "a tool result marked in error",
}
"""How each denial class reads in a table. Layer 1's renderings, named where ADR-0002 named them."""

HYDRATES: Final = frozenset({get_requisition.NAME, approve_requisition.NAME, record_invoice.NAME})
"""The tools that act against a named row, stated as the generator states them.

`get_requisition`, `approve_requisition` and `record_invoice` — three of the five,
and not the three another sentence in this repository means by the phrase.

The calls that **do** hydrate rather than the calls that do not, so that every
member is a name layer 3 owns — the complement would have to spell `tools/list`,
which is layer 1's word.
"""

ABSENT_REQUISITION: Final = "req_9999"
ABSENT_ORDER: Final = "po_9999"
"""The identifiers no row carries, for the rows whose whole subject is that nothing is there.

Spelled here rather than imported from `tests/fixtures.py`: this module runs as a
script from the repository root, so `tests/` is not on its path, and the two
values are the matrix's own convention rather than that module's — *"a row with
no `given`, on a tool that names a resource, acts on the identifier no row
carries."*
"""


def render(matrix: Matrix) -> str:
    """The whole document: a title, its provenance, the derived index, and the rows.

    Byte-stable on the same terms as the seed's four renderings — rows in
    declaration order, counts derived by counting, nothing generated and nothing
    dated — because one drift check polices them all and a check that flakes on
    any of them is a required check somebody will want turned off.
    """
    lines = [
        "# The decision matrix",
        "",
        f"<!-- Rendered from {MATRIX} by tests/matrix/matrix_table.py. Do not edit. -->",
        "<!-- `Seed renders clean` re-renders this file and refuses a diff. -->",
        "",
        f"{len(matrix.rows)} rows: what one principal may do to one resource through one tool.",
        "",
    ]

    lines.extend(_index(matrix))

    identifiers = _identifiers(matrix)
    for tool in _tools(matrix):
        lines.append(f"## `{tool}`")
        lines.append("")
        lines.append("| Row | Person | Token scopes | Acts on | Expected |")
        lines.append("| --- | --- | --- | --- | --- |")
        lines.extend(_row(row, identifiers) for row in matrix.rows if row.tool == tool)
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def _index(matrix: Matrix) -> list[str]:
    """The standing index, counted from the rows rather than copied from `meta`."""
    reasons: dict[str, int] = {}
    for row in matrix.rows:
        if row.expect.reason is not None:
            reasons[row.expect.reason] = reasons.get(row.expect.reason, 0) + 1

    permitted = sum(1 for row in matrix.rows if row.expect.permitted)

    lines = ["## What the rows reach", "", "| Reason | Rows | Refused as |", "| --- | --- | --- |"]
    lines.extend(
        f"| `{value}` | {count} | {SHAPES[REASON_RECORDS[value].denial_class]} |"
        for value, count in sorted(reasons.items())
    )
    lines.append(f"| *permitted* | {permitted} | — |")
    lines.append("")

    return lines


def _tools(matrix: Matrix) -> list[str]:
    """Every call the rows name, in the order the table first names them."""
    seen: list[str] = []
    for row in matrix.rows:
        if row.tool not in seen:
            seen.append(row.tool)

    return seen


def _identifiers(matrix: Matrix) -> dict[str, tuple[str, str | None]]:
    """Each fixture-bearing row's requisition and purchase order, by row name.

    Read from the generator rather than recomputed, so the *Acts on* column names
    what the seeded database holds. A row whose chain stops at the requisition
    has no order, and `record_invoice` is the only tool that acts on one.
    """
    return {
        fixture.row: (
            str(fixture.requisition["id"]),
            None if fixture.purchase_order is None else str(fixture.purchase_order["id"]),
        )
        for fixture in fixtures_for(matrix)
    }


def _row(row: Row, identifiers: dict[str, tuple[str, str | None]]) -> str:
    """One row of one tool's table."""
    scopes = " ".join(f"`{scope}`" for scope in row.principal.scopes) or "*none*"

    return (
        f"| `{row.id}` | {row.principal.person} | {scopes} "
        f"| {_acts_on(row, identifiers)} | {_expected(row)} |"
    )


def _acts_on(row: Row, identifiers: dict[str, tuple[str, str | None]]) -> str:
    """The resource this row acts against, which the matrix decides by one rule.

    A row that names a `given` acts on the fixture that block produces — the
    purchase order its chain reaches when the tool is `record_invoice`. A row
    without one, on a tool that names a resource, acts on the identifier no row
    carries. The listing and the two tools that name no resource act on nothing.
    """
    if row.tool not in HYDRATES:
        return "—"
    if row.given is None:
        return _absent(row.tool)

    requisition, order = identifiers[row.id]
    named = order if row.tool == record_invoice.NAME else requisition

    return f"`{named}` — {_chain(row.given)}"


def _absent(tool: str) -> str:
    """What a row with no fixture acts on: an identifier nothing carries, or nothing."""
    if tool == record_invoice.NAME:
        return f"`{ABSENT_ORDER}` — no order carries it"

    return f"`{ABSENT_REQUISITION}` — no row carries it"


def _chain(given: Given | None) -> str:
    """A fixture in one cell: the centre it is charged to, its amount, and how far it got."""
    if given is None:
        return "—"

    described = f"{given.cost_centre}, {given.amount}, raised by `{given.submitted_by}`"

    if given.approved_by is not None:
        described += f", approved by `{given.approved_by}`"
    if given.order_status is not None:
        described += f", order {given.order_status}"
    if given.recorded_by is not None:
        described += f", invoiced by `{given.recorded_by}`"

    return described


def _expected(row: Row) -> str:
    """The Decision the row expects, plus the one further fact its tool asserts on."""
    if not row.expect.permitted:
        assert row.expect.reason is not None
        return f"refused — `{row.expect.reason}`, {_shape(REASON_RECORDS[row.expect.reason])}"

    if row.expect.tools is not None:
        listed = ", ".join(f"`{tool}`" for tool in row.expect.tools) or "*nothing*"
        return f"permitted — lists {listed}"
    if row.expect.visible_partitions is not None:
        return f"permitted — returns {', '.join(row.expect.visible_partitions)}"
    if row.expect.charged_to is not None:
        return f"permitted — charged to {row.expect.charged_to}"

    return "permitted"


def _shape(reason: Reason) -> str:
    """The wire shape a reason takes, derived from the record and never restated."""
    return SHAPES[reason.denial_class]


def main() -> int:
    """Re-render the table from the committed matrix definition."""
    source = (REPO / MATRIX).read_text(encoding="utf-8")
    rendering = REPO / RENDERING

    rendering.parent.mkdir(parents=True, exist_ok=True)
    rendering.write_bytes(render(read_matrix(source)).encode("utf-8"))
    print(f"rendered {RENDERING}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The fixture generator: the seed's disposable half, read out of the matrix.

The third generator, and the one that renders none of the seed's three
renderings. :mod:`mcp_erp.authorization.identity` renders the directory rows and
the user import; :mod:`mcp_erp.purchase_to_pay.organisation` renders the ERP's
authored rows. This one reads ``docs/decision-matrix/matrix.yaml`` and emits the
rows the organisation does not hold: one requisition per matrix row that names a
``given``, plus the purchase order and the invoice that row's chain reaches.

It lives in ``purchase_to_pay/`` because it speaks layer 3's words — cost
centres, vendors, amounts, the people who raise and decide — so ejecting the
domain takes it and its rendering with it, while identity provisioning carries
on. That is ADR-0004's criterion 4 read literally, and it is also why
``matrix.yaml`` cannot live under ``tests/``: the thing that reads it ships in
``src/``.

**It never reads the seed, and the organisation generator never reads the
matrix.** ADR-0003 splits the two halves — *the organisation is authored; the
test data is generated* — and each generator touches one of them. The one value
that appears on both sides is the cost centre, and it is duplicated by
*authorship* here rather than by generation: a ``given`` block states the centre
its row is charged to, and ``tests/matrix/test_the_matrix_holds_together.py``
asserts it against the submitter's own centre in the organisation rendering. A
generator reading both halves would make that equality true by construction and
untestable, which is the opposite of what the drift check is for.

**Identifiers are ordinal, not name-shaped, and that is ADR-0003 choosing
between two of its own rules.** The guardrail says *an id derived from the row's
own name*; the normative register's *Legible identifiers* deviation says the
identifiers must be **guessable**, taken so that ``row_probe_indistinguishable``
can guess a foreign one rather than be handed it. ``req_over_threshold`` is not
guessable and would additionally read as zero to
:func:`~mcp_erp.purchase_to_pay.repository._next_identifier`, which mints from
the highest trailing integer that exists. So the identifiers stay ``req_0001``
upward, in the order the rows are declared, and what ties one to its row is the
``row`` field on the rendering — which the loader ignores and a reader does not.
Nothing keys on the number: every suite looks a fixture up by its row's name, so
inserting a row renumbers the rendering and changes no assertion.

Run it from a checkout to re-render::

    python -m mcp_erp.purchase_to_pay.fixtures
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final

import yaml

MATRIX = "docs/decision-matrix/matrix.yaml"
"""The canonical matrix definition, relative to the repository root.

Under ``docs/`` rather than ``tests/`` because this module ships in ``src/`` and
a package that reached into the test tree for its input would not survive being
installed (ADR-0013).
"""

FIXTURE_RENDERING = "src/mcp_erp/purchase_to_pay/data/fixtures.json"
"""Where the generated rows are committed, relative to the repository root.

Beside the organisation rendering, inside layer 3's package, so ``rm -rf
src/mcp_erp/purchase_to_pay`` takes the seed's disposable half with the domain.
"""

SUBMITTED: Final = "submitted"
APPROVED: Final = "approved"
REJECTED: Final = "rejected"
STATUSES: Final = (SUBMITTED, APPROVED, REJECTED)
"""The three values ``requisition_status`` holds, spelled as the schema spells them."""

OPEN: Final = "open"
INVOICED: Final = "invoiced"
ORDER_STATUSES: Final = (OPEN, INVOICED)
"""The two values ``purchase_order_status`` holds."""

LISTING: Final = "tools/list"
"""The one method a row may name that is not a tool.

The listing filters on granted scope and nothing else, so its rows vary the
principal and expect a set of tool names — a ``(principal x tool x resource)``
row whose resource is the tool set itself. Named here because the generator has
to know that such a row carries no ``given``, and layer 3 already owns every
other name in the table.
"""


@dataclass(frozen=True, slots=True)
class Given:
    """One row's fixture: a requisition, and as much of its chain as the row needs.

    Flat and literal, with every field stated — ADR-0003's guardrail. There are
    no defaults to inherit and no reference to another row, so a fixture is
    readable without holding the rest of the table in mind.

    The three nullable fields are what make one record cover a chain of up to
    three entities without a conditional in the data: an approver means an order,
    and a recorder means an invoice. :func:`read_matrix` refuses every other
    combination, so the implication runs one way and cannot be half-stated.

    Attributes:
        cost_centre: The centre the row is charged to, which is its submitter's.
        vendor: A vendor identifier from the seed.
        amount: The decimal string, which is what the threshold reads.
        description: The label, ADR-0003's single named legibility exception.
        submitted_by: The subject that raised it.
        status: One of :data:`STATUSES`.
        approved_by: The approver's subject, or ``None``.
        order_status: One of :data:`ORDER_STATUSES`, or ``None``.
        recorded_by: The recorder's subject, or ``None``.
    """

    cost_centre: str
    vendor: str
    amount: str
    description: str
    submitted_by: str
    status: str
    approved_by: str | None
    order_status: str | None
    recorded_by: str | None


@dataclass(frozen=True, slots=True)
class Principal:
    """Person x scope set, which is what the matrix varies rather than person alone.

    Effective permission is granted scope intersected with role permission, and the two inputs
    are only genuinely independent if the table can move them independently —
    including the case the exhibit most wants to show, a senior approver whose
    application asked only for read scope (ADR-0003).
    """

    person: str
    scopes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Expect:
    """What the row expects, stated as an outcome and at most one further fact.

    ``reason`` is the whole of a refusal's expectation. Wire shape, remedy and
    both retry booleans are **derived** from the ``Reason`` record the two layers
    declare, never restated here — which is what keeps ADR-0002's mapping a thing
    asserted in exactly one place.

    Attributes:
        allowed: Whether the call is expected to go through.
        reason: The refusal's value, or ``None`` when it is allowed.
        tools: For a ``tools/list`` row, the names the listing must return.
        visible_partitions: For a ``list_requisitions`` row, the centres whose
            fixtures must come back — the set the row asserts equality over.
        charged_to: For a ``submit_requisition`` row, the centre the written row
            must be stamped with.
    """

    allowed: bool
    reason: str | None
    tools: tuple[str, ...] | None
    visible_partitions: tuple[str, ...] | None
    charged_to: str | None


@dataclass(frozen=True, slots=True)
class Row:
    """One ``(principal x tool x resource → expected)`` row.

    The resource is not a field. A row that names a ``given`` acts on the fixture
    that block produces; a row without one, on a tool that names a resource, acts
    on the identifier no row carries. One rule rather than a third column that
    could disagree with the second.
    """

    id: str
    principal: Principal
    tool: str
    given: Given | None
    expect: Expect


@dataclass(frozen=True, slots=True)
class Matrix:
    """The whole table, plus the standing index it declares about itself.

    ``meta`` is carried through unparsed. It is an index for a reader and a
    subject for ``tests/matrix/test_the_matrix_holds_together.py``, which asserts
    every count in it against the rows — so nothing here may derive a count from
    it, or the check would be comparing the file to itself.
    """

    meta: Mapping[str, Any]
    rows: tuple[Row, ...]


@dataclass(frozen=True, slots=True)
class Fixture:
    """One matrix row's fixture, rendered: the rows it puts in the three tables.

    ``purchase_order`` and ``invoice`` are ``None`` unless the row's chain
    reaches them. The row's own name travels with each, which is what ties a
    generated identifier back to the row that owns it.
    """

    row: str
    requisition: Mapping[str, Any]
    purchase_order: Mapping[str, Any] | None
    invoice: Mapping[str, Any] | None


def read_matrix(text: str) -> Matrix:
    """Parse the matrix definition, refusing what no run of the tools could produce.

    The refusals are the guardrail made executable. Three of them are about the
    chain a ``given`` describes — an approver without an approval, an order
    without an approver, a recorder without an invoiced order — and each names a
    state the five tools cannot reach, so a fixture in one of them would be data
    the exhibit is asserting against and could never have written.

    The other three are about the table itself: a duplicated row identifier, a
    reason on a permitted row, and a ``given`` on a tool that names no resource.

    Raises:
        ValueError: Two rows share an identifier; a ``given`` describes a state
            no tool could produce; a permitted row states a reason or a refused
            row states none; or a row carries a ``given`` on a tool that acts
            against no resource.
    """
    document = yaml.safe_load(text)

    rows: list[Row] = []
    seen: set[str] = set()
    for entry in document["rows"]:
        identifier = str(entry["id"])
        if identifier in seen:
            raise ValueError(f"duplicate row {identifier!r}")
        seen.add(identifier)

        given = _given(entry["given"], row=identifier)
        if given is not None and entry["tool"] in _RESOURCELESS:
            raise ValueError(
                f"row {identifier!r} carries a fixture on {entry['tool']!r}, "
                f"which acts against no resource"
            )

        rows.append(
            Row(
                id=identifier,
                principal=Principal(
                    person=str(entry["principal"]["person"]),
                    scopes=tuple(str(scope) for scope in entry["principal"]["scopes"]),
                ),
                tool=str(entry["tool"]),
                given=given,
                expect=_expect(entry["expect"], row=identifier),
            )
        )

    return Matrix(meta=document["meta"], rows=tuple(rows))


def render_fixtures(matrix: Matrix) -> str:
    """Render the three tables the matrix's rows own, in declaration order.

    Byte-stable on the same terms as the other two generators — sorted keys, rows
    in a fixed order, nothing generated and nothing dated — because one drift
    check polices all four renderings and a check that flakes on any of them is a
    required check somebody will want turned off.

    Amounts render as the decimal string the matrix states rather than as a
    number: JSON has one numeric type and it is binary floating point, which
    cannot represent what an accounting amount means. The column is
    ``numeric(12, 2)`` and the loader casts the string into it.
    """
    fixtures = fixtures_for(matrix)
    return _as_json(
        {
            "requisitions": [fixture.requisition for fixture in fixtures],
            "purchase_orders": [
                fixture.purchase_order for fixture in fixtures if fixture.purchase_order is not None
            ],
            "invoices": [fixture.invoice for fixture in fixtures if fixture.invoice is not None],
        }
    )


def fixtures_for(matrix: Matrix) -> tuple[Fixture, ...]:
    """One fixture per row that names a ``given``, in the order the rows declare them.

    The loop ADR-0003 asked for, and deliberately nothing more: no row consults
    another, no identifier is computed from a field, and the three counters are
    the only state it carries. A conditional here would be the DSL map constraint
    `#4` refused arriving through the generator instead of through the data.
    """
    fixtures: list[Fixture] = []
    requisitions = orders = invoices = 0

    for row in matrix.rows:
        given = row.given
        if given is None:
            continue

        requisitions += 1
        requisition_id = _identifier("req", requisitions)
        purchase_order: dict[str, Any] | None = None
        invoice: dict[str, Any] | None = None

        if given.approved_by is not None:
            orders += 1
            order_id = _identifier("po", orders)
            purchase_order = {
                "row": row.id,
                "id": order_id,
                "requisition_id": requisition_id,
                "approved_by": given.approved_by,
                "status": given.order_status,
            }

            if given.recorded_by is not None:
                invoices += 1
                invoice = {
                    "row": row.id,
                    "id": _identifier("inv", invoices),
                    "purchase_order_id": order_id,
                    "recorded_by": given.recorded_by,
                }

        fixtures.append(
            Fixture(
                row=row.id,
                requisition={
                    "row": row.id,
                    "id": requisition_id,
                    "cost_centre": given.cost_centre,
                    "vendor": given.vendor,
                    "amount": given.amount,
                    "description": given.description,
                    "submitted_by": given.submitted_by,
                    "status": given.status,
                },
                purchase_order=purchase_order,
                invoice=invoice,
            )
        )

    return tuple(fixtures)


_RESOURCELESS: Final = frozenset({LISTING, "list_requisitions", "submit_requisition"})
"""The three calls that act against no named resource, and so never carry a fixture.

The listing and the unnamed read take no identifier at all; ``submit_requisition``
takes arguments and creates a row rather than acting on one — *the thing acted
against, never the thing created* (ADR-0013).
"""


def _identifier(prefix: str, ordinal: int) -> str:
    """One fixture identifier: the prefix, and the ordinal padded to four digits.

    The same shape :func:`~mcp_erp.purchase_to_pay.repository._next_identifier`
    mints, because the two share a table and a run does both — the fixtures are
    loaded, and then a suite submits. Four digits rather than a bare integer so
    that the padding, which is the mint's, is what the fixtures already carry.
    """
    return f"{prefix}_{ordinal:04d}"


def _given(entry: Mapping[str, Any] | None, *, row: str) -> Given | None:
    """One fixture block, with the three chain implications checked.

    Raises:
        ValueError: The block describes a state no run of the five tools could
            have produced.
    """
    if entry is None:
        return None

    status = str(entry["status"])
    if status not in STATUSES:
        raise ValueError(f"row {row!r} has status {status!r}, which is not one of {STATUSES}")

    approved_by = _optional(entry["approved_by"])
    order_status = _optional(entry["order_status"])
    recorded_by = _optional(entry["recorded_by"])

    # An approval is what emits an order, so the two arrive together or not at
    # all. A rejection is equally terminal and emits nothing, which is why the
    # test is against `approved` rather than against the status being terminal.
    if (approved_by is not None) != (status == APPROVED):
        raise ValueError(
            f"row {row!r} states an approver on a {status!r} requisition, "
            f"or a {APPROVED!r} one with no approver"
        )
    if (order_status is not None) != (approved_by is not None):
        raise ValueError(f"row {row!r} states an order status with no approver, or the reverse")
    if order_status is not None and order_status not in ORDER_STATUSES:
        raise ValueError(
            f"row {row!r} has order status {order_status!r}, which is not one of {ORDER_STATUSES}"
        )
    # An invoice is what a recording writes, and one order takes exactly one — so
    # a recorder and an invoiced order are the same fact stated twice, and either
    # without the other is a chain with a missing link.
    if (recorded_by is not None) != (order_status == INVOICED):
        raise ValueError(
            f"row {row!r} states a recorder on an order that is not {INVOICED!r}, "
            f"or an {INVOICED!r} order with no recorder"
        )

    amount = str(entry["amount"])
    try:
        if Decimal(amount) <= 0:
            raise ValueError(f"row {row!r} has a non-positive amount {amount!r}")
    except InvalidOperation as unusable:
        raise ValueError(f"row {row!r} has an amount that is not decimal: {amount!r}") from unusable

    return Given(
        cost_centre=str(entry["cost_centre"]),
        vendor=str(entry["vendor"]),
        amount=amount,
        description=str(entry["description"]),
        submitted_by=str(entry["submitted_by"]),
        status=status,
        approved_by=approved_by,
        order_status=order_status,
        recorded_by=recorded_by,
    )


def _expect(entry: Mapping[str, Any], *, row: str) -> Expect:
    """One expectation block, with the outcome and the reason held to each other.

    Raises:
        ValueError: The outcome is neither of the two words, a permitted row
            states a reason, or a refused row states none. A refusal with no
            reason would be a row asserting only that *something* went wrong,
            which is the assertion this table exists instead of.
    """
    outcome = str(entry["outcome"])
    if outcome not in ("allowed", "refused"):
        raise ValueError(f"row {row!r} expects {outcome!r}, which is neither allowed nor refused")

    allowed = outcome == "allowed"
    reason = _optional(entry.get("reason"))
    if allowed != (reason is None):
        raise ValueError(f"row {row!r} expects {outcome!r} and states reason {reason!r}")

    return Expect(
        allowed=allowed,
        reason=reason,
        tools=_names(entry.get("tools")),
        visible_partitions=_names(entry.get("visible_partitions")),
        charged_to=_optional(entry.get("charged_to")),
    )


def _names(value: Sequence[Any] | None) -> tuple[str, ...] | None:
    """A list of names as a tuple, or ``None`` where the key is absent.

    The empty list is **not** ``None`` and the distinction is load-bearing: a
    token carrying no capability scope expects the listing to return nothing,
    which is a row asserting the empty set rather than a row asserting nothing.
    """
    return None if value is None else tuple(str(name) for name in value)


def _optional(value: object) -> str | None:
    """One nullable string field, stated as ``null`` rather than omitted.

    ``object`` rather than ``Any``, so that nothing downstream inherits a hole in
    the type: what YAML hands back is unknown, and the one legal thing to do with
    it here is to narrow it or refuse it.
    """
    return None if value is None else str(value)


def _as_json(document: object) -> str:
    """The serialisation all four renderings share, stated again rather than shared.

    The argument :mod:`mcp_erp.purchase_to_pay.organisation` makes about not
    sharing this with layer 2 does not apply between two layer-3 modules — they
    are deleted together — but the two read different sources for different
    reasons and ADR-0013 keeps them separate for that. Six identical arguments is
    the cheaper duplication, and it is the same six.
    """
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write(path: Path, text: str) -> None:
    """Write a rendering, in bytes, with the newline the renderer chose."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def main() -> None:
    """Re-render the fixtures from the committed matrix definition.

    Resolves paths from this file's location, so it runs from a checkout and
    nowhere else — the rendering is committed, and the ``Seed renders clean`` job
    re-runs this and fails on any diff.
    """
    repo = Path(__file__).resolve().parents[3]
    matrix = (repo / MATRIX).read_text(encoding="utf-8")

    _write(repo / FIXTURE_RENDERING, render_fixtures(read_matrix(matrix)))
    print(f"rendered {FIXTURE_RENDERING}")


if __name__ == "__main__":
    main()

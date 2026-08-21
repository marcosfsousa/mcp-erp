"""The canonical list, as this directory reads it, and the way a test declares a row.

`docs/attack-suite/scenarios.yaml` is the single source of truth. This module is
the only thing that parses it, and it does three jobs that have to agree:

**It reads the rows**, so the invariants beside it assert against the file rather
than against a restatement of it — the `meta` block's counts included, which is
what map constraint `#12` asks of a derived number kept where it can be read.
Since #92 it is also what `scenario_table.py` renders the write-up's table from, which is
why :class:`Scenario` carries the whole row rather than the fields an assertion
reads.

**It carries the declaration**, :func:`exercises`, which every test in this
directory applies to say which row it falsifies. ADR-0010 fixed that shape — *"tests
are hand-written and declare which scenario they exercise by name, with a drift
check asserting a bijection and the threshold row as its single declared
exemption"* — and the marker is what makes the declaration mechanical rather than
a sentence in a docstring that nothing reads.

**It reads the assertions**, :func:`restated_refusal_payloads`, which is the one
check here about how a row asserts rather than about which row it is. It shares
the source walk with the declaration collector because both ask the same question
of the same files, and a second `glob` would be a second answer to it.

**The declarations are collected from the source, never by importing.** Importing
this directory's modules from inside a test would run them a second time under a
second name, which is a pytest problem before it is anything else. Reading the
decorators out of the syntax tree costs nothing, cannot execute a fixture by
accident, and reports the module and function a stray declaration sits in.
`tests/authorization/test_purity.py` reads layer 2's source for a comparable
reason: some properties are about what is written, not about what happens.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import pytest
import yaml

TestFunction = ast.FunctionDef | ast.AsyncFunctionDef
"""What pytest collects as a test, in the syntax tree's terms — both spellings."""

HERE: Final = Path(__file__).resolve().parent
"""This directory, which is where the declarations live."""

REPO: Final = HERE.parents[1]
"""The checkout, from this file's own location — `tests/fixtures.py`'s resolution."""

SCENARIOS: Final = "docs/attack-suite/scenarios.yaml"
"""The canonical list, relative to the repository root."""

DECLARATION: Final = "exercises"
"""The name a test applies to declare its row, as it is written in the source.

The collector matches on this spelling, so renaming the function means renaming
it here — and a declaration written through an alias is not collected, which is
a limitation stated out loud rather than defended against: every test in this
directory writes `@exercises("row_name")` and the invariants refuse a test that
does not.
"""

MAPPED_FIELDS: Final = frozenset({"remedy", "retry_identical_helps", "retry_as_other_person_helps"})
"""The refusal-body fields ADR-0002 derives from the reason, as the wire keys them.

Not `reason` itself, which names which rule fired rather than what the mapping
says about it. Spelled here rather than read off `Reason`'s dataclass fields
because these are *wire* keys — the record also carries `denial_class`, which
decides the shape a refusal takes and never appears in a body.
"""

INVARIANTS: Final = "test_the_suite_holds_together.py"
"""The one module in this directory that declares no row, and the only one.

It is about the table rather than about an attack, so a declaration would name a
row it does not falsify. Named here so the exemption is one string in one place
instead of a rule about which files are exempt.
"""

DOCUMENTED: Final = "documented"
ASSERTED: Final = "asserted"

RETITLE_BELOW: Final = 20
"""Below this many asserting rows the write-up stops calling this an attack suite.

`scenarios.yaml`'s own invariant — *"Below 20 asserted rows the write-up retitles
this from 'attack suite' to 'clause inventory, N proven'"* — asserted here so the
title and the table cannot come apart quietly.
"""


@dataclass(frozen=True, slots=True)
class Scenario:
    """One row of the canonical list, whole.

    **It used to be deliberately partial**, on the ground that nothing asserted
    against the citation or the prose and that parsing them would invite a test
    checking a sentence's shape. That ground moved with #92: `scenario_table.py` renders
    this file into the write-up, ADR-0014 makes that rendering committed and
    diff-checked, and a renderer needs the row. Nothing here asserts against the
    prose still — the invariants beside this module read the same fields they
    always did.

    Attributes:
        name: The stable identifier a test declares. Never reworded.
        basis: `clause`, `adr` or `seam`.
        prevents: One line: the attack this stops.
        citation: The citation block verbatim, key by key. Carried as a mapping
            rather than parsed into fields because its shape varies by basis and
            by what was harvestable — nineteen rows quote a clause, fifteen name
            a decision, and seven of the quotes are elided. A renderer that
            walked named fields would drop a key nobody had told it about; one
            that walks the mapping cannot.
        normative_strength: The keyword the quoted sentence carries, or ``None``
            for the two bases that quote no normative sentence at all.
        status: `asserted` or `documented`.
        floor: Whether the row may ever be downgraded to `documented`.
        removal: The deletion that makes the attack succeed, or ``None`` on the
            one row that prevents nothing.
        note: What the row asserts and how it splits from its neighbours, or
            ``None``.
        history: How the row was narrowed or corrected, or ``None``. **Separate
            from `note` deliberately**, and the reason is a rendering: a note
            recording a *withdrawn* claim still contains the claim's words, and
            a rendered cell carrying them can be skimmed as an assertion.
            `row_probe_indistinguishable` is the row that found it.
    """

    name: str
    basis: str
    prevents: str
    citation: Mapping[str, str]
    normative_strength: str | None
    status: str
    floor: bool
    removal: str | None
    note: str | None
    history: str | None


@dataclass(frozen=True, slots=True)
class Suite:
    """The canonical list as a whole: the standing index, and the rows it indexes.

    Attributes:
        meta: The `meta` block verbatim, so the invariants can assert every
            number in it against the rows rather than trusting it.
        rows: The scenarios, in the order the file declares them.
    """

    meta: Mapping[str, Any]
    rows: tuple[Scenario, ...]

    @property
    def names(self) -> set[str]:
        """Every row's name, which is the set a declaration has to land in."""
        return {row.name for row in self.rows}

    @property
    def asserted(self) -> tuple[Scenario, ...]:
        """The rows carrying `status: asserted` — the ones a test has to exist for."""
        return tuple(row for row in self.rows if row.status == ASSERTED)

    @property
    def documented(self) -> tuple[Scenario, ...]:
        """The rows carrying `status: documented`, of which there may be exactly one."""
        return tuple(row for row in self.rows if row.status == DOCUMENTED)


@dataclass(frozen=True, slots=True)
class Declaration:
    """One test's statement of the row it falsifies.

    Attributes:
        scenario: The row's name, as written in the decorator.
        module: The file it was written in.
        test: The test function carrying it.
    """

    scenario: str
    module: str
    test: str


def exercises(name: str) -> pytest.MarkDecorator:
    """Declare the scenario this test falsifies, by name.

    Applied to every test in this directory, and the drift check reads it back
    out of the source. A marker rather than a bare attribute so the declaration
    is visible to `pytest --collect-only` and selectable with `-m`, which is what
    makes *run the rows that cover this defence* a thing a reader can do.

    Args:
        name: A row's `name` in `scenarios.yaml`, verbatim.

    Returns:
        The marker, for use as a decorator.
    """
    return pytest.mark.scenario(name)


def read_suite(text: str) -> Suite:
    """Parse the canonical list.

    Args:
        text: The contents of `scenarios.yaml`.

    Returns:
        The `meta` block and the rows.

    Raises:
        ValueError: The document is not a mapping carrying `meta` and
            `scenarios`, or a row is missing a field the invariants read. A
            refusal at the parse rather than a `KeyError` inside an assertion,
            because a malformed table should say so once instead of four times.
    """
    document = yaml.safe_load(text)
    if not isinstance(document, dict) or "meta" not in document or "scenarios" not in document:
        raise ValueError("scenarios.yaml must be a mapping carrying `meta` and `scenarios`")

    rows: list[Scenario] = []
    for entry in document["scenarios"]:
        if not isinstance(entry, dict):
            raise ValueError(f"a scenario must be a mapping, got {entry!r}")
        missing = [
            key
            for key in ("name", "basis", "prevents", "citation", "status", "floor")
            if key not in entry
        ]
        if missing:
            raise ValueError(f"{entry.get('name', entry)!r} is missing {', '.join(missing)}")
        rows.append(
            Scenario(
                name=str(entry["name"]),
                basis=str(entry["basis"]),
                prevents=str(entry["prevents"]),
                citation={str(key): str(value) for key, value in entry["citation"].items()},
                normative_strength=_optional(entry.get("normative_strength")),
                status=str(entry["status"]),
                floor=bool(entry["floor"]),
                removal=_optional(entry.get("removal")),
                note=_optional(entry.get("note")),
                history=_optional(entry.get("history")),
            )
        )

    return Suite(meta=document["meta"], rows=tuple(rows))


def suite() -> Suite:
    """The canonical list as committed, read from the checkout this run is in."""
    return read_suite((REPO / SCENARIOS).read_text(encoding="utf-8"))


def declarations(directory: Path = HERE) -> tuple[Declaration, ...]:
    """Every `@exercises(...)` in this directory, read out of the source.

    Statically, for the reason the module docstring gives: importing a test
    module from inside a test is a second import under a second name, and the
    question here is what is *written* rather than what runs.

    Args:
        directory: Where the test modules live. A parameter so the drift check's
            own demonstration can point it at a directory it wrote itself.

    Returns:
        One entry per declaration, in file and then source order.
    """
    return tuple(
        Declaration(scenario=name, module=path.name, test=function.name)
        for path, function in _tests_in(directory)
        for name in _declared_by(function)
    )


def tests_without_a_declaration(directory: Path = HERE) -> tuple[str, ...]:
    """Tests in this directory that declare no row at all.

    The half of the bijection that reads from the tests rather than from the
    table. A test that declares nothing is not a defect in what it asserts — it
    is a hole in the report: the suite's claim is that every row here has a
    falsifier and every falsifier here is named by a row, and an undeclared test
    is outside both halves of that sentence.

    Args:
        directory: Where the test modules live.

    Returns:
        ``module::test`` for each, in file and then source order.
    """
    return tuple(
        f"{path.name}::{function.name}"
        for path, function in _tests_in(directory)
        if path.name != INVARIANTS and not _declared_by(function)
    )


def rows_without_a_test(rows: Suite, declared: tuple[Declaration, ...]) -> set[str]:
    """Asserting rows that no test declares — the drift a new row arrives as.

    The exemption is **derived from the row rather than written down here**: a
    row carrying `status: documented` asserts nothing and therefore needs no
    test, which is ADR-0010's *"the threshold row as its single declared
    exemption"* expressed as the rule it is an instance of. Naming the row here
    would make the exemption survive the row changing status, which is exactly
    the drift this function exists to catch.

    Args:
        rows: The canonical list.
        declared: Every declaration the tests carry.

    Returns:
        The names, or an empty set when the suite is whole.
    """
    return {row.name for row in rows.asserted} - {entry.scenario for entry in declared}


def declarations_naming_no_row(rows: Suite, declared: tuple[Declaration, ...]) -> set[str]:
    """Declarations that name nothing in the table — the other direction of the drift.

    A test declaring a row that does not exist is a test nobody can find from the
    table, and a renamed row leaves one behind. `name` is the field
    `scenarios.yaml` says is *"never reworded"*, and this is what holds that.

    Args:
        rows: The canonical list.
        declared: Every declaration the tests carry.

    Returns:
        ``module::test → scenario`` for each, so the message names where to look.
    """
    return {
        f"{entry.module}::{entry.test} declares {entry.scenario!r}"
        for entry in declared
        if entry.scenario not in rows.names
    }


def restated_refusal_payloads(directory: Path = HERE) -> tuple[str, ...]:
    """Places in this directory that spell a refusal body out instead of reading it.

    A refusal body is four fields, and every one of them is stated once — in the
    `Reason` the two layers declare. A test that writes any of them out again is
    a second copy of ADR-0002's mapping, and the rows here assert a **defence**:
    a defence whose expectation is a copy goes on passing after the declaration
    beneath it changes, which is the one way a green attack suite can be lying.
    `refusal_records.refusal_body` is the read that avoids it.

    Two shapes, because #87 found the second only after counting the first:

    - a **whole body**, a dictionary carrying both `reason` and `remedy`;
    - a **field**, a subscript of any of the three that carry the mapping,
      compared against anything.

    `reason` alone is not matched. Naming which rule fired is what a row is *for*
    — `answers[1]["reason"] == "not_found"` says the refusal came from the right
    place and says nothing about its declared shape.

    **The limits, out loud.** It reads `test_*.py` in this directory only, so
    `scenarios.py` and any helper module escape it; it sees dictionary displays
    and not `dict(reason=…)`; and it reads subscripts written with a literal key,
    not one held in a variable. Each is a way to restate the mapping that this
    would not catch, stated here rather than defended against — the same
    narrowness `DECLARATION` records for the collector above.

    `tests/wire/` is deliberately outside this: those literals are the
    demonstration a reader opens the file for, and the modules that keep them say
    so in their own docstrings (#87).

    Args:
        directory: Where the test modules live.

    Returns:
        ``module:line`` for each, in file and then source order.
    """
    return tuple(
        f"{path.name}:{node.lineno}"
        for path, tree in _modules_in(directory)
        for node in ast.walk(tree)
        if isinstance(node, ast.expr) and (_is_whole_body(node) or _is_mapping_field(node))
    )


def _is_whole_body(node: ast.expr) -> bool:
    """A dictionary display carrying both `reason` and `remedy`.

    The two keys rather than all four, so that a body written out with a field
    left off is caught as well as a complete one.
    """
    return isinstance(node, ast.Dict) and {"reason", "remedy"} <= {
        key.value for key in node.keys if isinstance(key, ast.Constant)
    }


def _is_mapping_field(node: ast.expr) -> bool:
    """A subscript naming one of the three fields the mapping decides.

    `reason` is not among them: which rule fired is a row's own business, and the
    three below are the ones ADR-0002 derives from it.
    """
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and node.slice.value in MAPPED_FIELDS
    )


def _modules_in(directory: Path) -> Iterator[tuple[Path, ast.Module]]:
    """Every test module of a directory, parsed once, in file order.

    One walk, because every check that reads the sources asks the same question
    of the same files and a second `glob` would be a second answer to *what
    counts as a test here*.

    **`rglob`, not `glob`**, so a subdirectory cannot hold a test the check never
    sees — pytest would collect it and this would not, which is the one asymmetry
    that makes a bijection claim untrue while every assertion in it passes.
    """
    for path in sorted(directory.rglob("test_*.py")):
        yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _tests_in(directory: Path) -> Iterator[tuple[Path, TestFunction]]:
    """Every test function in every test module of a directory, in file and source order.

    Module-level definitions only. A nested helper named `test_…` is not
    collected by pytest either, so walking the whole tree would hold a
    declaration against something that never runs.
    """
    for path, tree in _modules_in(directory):
        for node in tree.body:
            # `async def` too: nothing here is asynchronous today, and a test
            # that were would be invisible to the collector while pytest ran it
            # — a hole in the load-bearing claim, closed for the cost of naming
            # the second node type.
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
                "test_"
            ):
                yield path, node


def _declared_by(function: TestFunction) -> tuple[str, ...]:
    """The scenario names one test's decorators declare.

    Reads `@exercises("…")` and nothing else — not an alias, not a name computed
    at import. The narrowness is the point: what the collector accepts is what a
    reader can see by looking at the line above the test.
    """
    names: list[str] = []
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        called = decorator.func
        if not (isinstance(called, ast.Name) and called.id == DECLARATION):
            continue
        names.extend(
            argument.value
            for argument in decorator.args
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
        )
    return tuple(names)


def _optional(value: object) -> str | None:
    """A YAML scalar as a string, keeping `null` as ``None``.

    Four fields are deliberately nullable and an empty string would erase what
    each absence means: `normative_strength` on every `adr` and `seam` row,
    `removal` on the one row that prevents nothing, and `note` and `history` on
    every row that has nothing of that kind to record.
    """
    return None if value is None else str(value)

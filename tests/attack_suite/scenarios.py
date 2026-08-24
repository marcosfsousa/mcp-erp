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

STAR: Final = "*"
"""How the tree spells the alias of a wildcard import, and how a refusal names one.

`from helper import *` binds whatever the other module exports, so there is no
identifier on the line to report. :func:`runnable_but_unseen_in` refuses it under
this name rather than resolving the other module — reading one file is what makes
that check cheap and what keeps it from becoming an interpreter.
"""

TEST_CASE: Final = "TestCase"
"""The suffix a class pytest collects by *type* is written with, in every spelling.

`unittest` exports three `TestCase` classes — `TestCase`,
`IsolatedAsyncioTestCase` and `FunctionTestCase` — and `_pytest/unittest.py`
collects a subclass of any of them before a name pattern is consulted. A suffix
reads all three off the line; the equality against this literal that stood here
until #127 read one, and the other two ran unrefused.
"""

TEST_FLAG: Final = "__test__"
"""The attribute pytest collects a class by when no name and no base would reach it.

`python_classes = []` turns off collection by name and does not turn this off:
pytest reads the flag from the object, so a class carrying ``__test__ = True``
runs whatever it derives from and whatever it is called. It is the one shape here
that is a property of the class rather than of a binding, which is why
:func:`_is_flagged_as_a_test` is a second mechanism rather than a wider base rule.
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


def runnable_but_unseen_in(directory: Path = HERE) -> tuple[str, ...]:
    """Module-scope bindings pytest would run here that :func:`_tests_in` cannot see.

    `pyproject.toml` narrows collection to `test_*.py`, no classes and `test_*`
    functions, so that what pytest runs and what the collector reads are the same
    set. That narrowing reaches everything **named** — but the collector reads
    the syntax tree for a module-level ``def test_…``, and pytest reads the
    module's *namespace*, so a `test_*` name that arrives any other way runs
    unseen. Each such test declares no row while satisfying
    :func:`tests_without_a_declaration`, which is the bijection's third direction
    broken silently — the failure `test_the_suite_holds_together.py` exists to
    make impossible.

    **One rule, not a list of shapes.** Every `test_*` name bound at module scope
    is refused unless it is a ``def test_…`` :func:`_tests_in` itself read, and
    every class :func:`_is_a_test_case` decides is one is refused outright —
    `_pytest/unittest.py` collects a `TestCase` subclass by *type* before any name
    pattern is consulted, so `python_classes` has no bearing on it and `unittest`'s
    own loader then finds its methods by their `test` prefix rather than by
    `python_functions`. Three ways in were measured against a real
    `--collect-only` run (#112): that `TestCase`, a name bound by import, and one
    bound by assignment. The rule covers those, and also unpacking, `for`,
    `with … as`, the walrus, an import guarded by an `if` or a `try`, and a `def`
    nested under either — none of which an enumeration written from the three
    would have caught, and every one of which pytest runs.

    **The class half is a judgment, and a name it cannot judge is reported.**
    Three more shapes were measured the same way (#127) and all three were being
    cleared: `unittest.IsolatedAsyncioTestCase`, a `TestCase` base imported under
    another name, and a class carrying :data:`TEST_FLAG`. What decides a class now
    is :func:`_is_a_test_case` — a base whose written name ends in
    :data:`TEST_CASE`, or the flag in the class body — and an import that renames
    a `TestCase` is refused on its own line by :func:`_imports_a_test_case`. What
    is left is a base this cannot read at all, and that goes to
    :func:`classes_that_cannot_be_judged_in` rather than passing as a `no`.

    Scope is what the tree marks: `def` and `class` bodies bind in a scope of
    their own and are not descended, while `if`, `try`, `for`, `while`, `with`
    and `match` are, because a binding under one of those is still a module-level
    binding. A comprehension and a `lambda` have a scope of their own too and are
    descended anyway — refusing `[test_x for test_x in …]`, which binds nothing
    outside the brackets. That is the same bias as the paragraph below, taken
    rather than spending a scope table on a name nobody writes.

    **A wildcard import is refused under the name ``*``.** The names it binds are
    in the other module and this reads one file, so there is nothing to report but
    the line itself.

    **The identifier is the boundary.** A name written into `globals()`, or bound
    by `exec` or `setattr`, appears on no line as a name and is out of reach here.
    Refusing what is *written* closes the hole worth closing; resolving what is
    computed would make this an interpreter — the same reason :func:`_tests_in`
    is not taught to follow an import, and the same reason it is not taught to
    collect a declaration out of a class body, which would make `@exercises` mean
    two things. :func:`_is_flagged_as_a_test` reads a class body and is not that:
    it collects no declaration and no binding, and reports on the class it was
    already handed.

    **Read as written, never resolved**, and erring toward refusal. A base whose
    name ends in `TestCase` matches and a subclass of a subclass does not;
    `test_payloads = (…)` is refused though pytest collects no tuple. That is
    :data:`DECLARATION`'s rule about aliases applied again — what the check
    accepts is what a reader can see on the line — and it is sound here because
    the invariant is that none of these shapes is present at all, so a rename is
    the whole remedy for a false positive. The rule was **held** through #127 and
    supplemented twice rather than bent: once by reading the import line where a
    base was renamed, and once by reading :data:`TEST_FLAG` out of a class body,
    which asks what a class *is* rather than what the module binds.

    Args:
        directory: Where the test modules live.

    Returns:
        ``module::name`` for each, in file and then source order.
    """
    return tuple(
        f"{path.name}::{name}"
        for path, tree in _modules_in(directory)
        # `dict.fromkeys` rather than a set: a name rebound at module scope is one
        # unseen test, reported once, and source order is what makes it findable.
        for name in dict.fromkeys(_unseen_in(tree))
    )


def _unseen_in(tree: ast.Module) -> Iterator[str]:
    """The module-scope bindings of one module that :func:`_tests_in` did not read."""
    read = {
        id(node)
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.startswith("test_")
    }
    for node in _at_the_scope_of(tree):
        if id(node) not in read:
            yield from _runnable_but_unseen(node)


def _at_the_scope_of(node: ast.AST) -> Iterator[ast.AST]:
    """Every node under one that runs in the scope that node opens, in source order.

    Written for a module and used for a class body too, because the question is
    the same one twice: *what runs here*. Stops at `def` and `class`, whose bodies
    open a scope of their own — which is why :func:`_tests_in` reads `tree.body`
    and nothing deeper. Anything else is descended, control flow included, because
    `if`, `try`, `for`, `while` and `with` write into the enclosing namespace
    exactly as a bare statement does — which is what a first cut at reading
    :data:`TEST_FLAG` off a class body's top level alone missed (#127). Two things
    descended here do *not*: a comprehension and a `lambda`. They are left in on
    the bias :func:`runnable_but_unseen_in` states — a refusal costs a rename and a
    miss costs a silent bijection break — rather than because they belong.

    **What this does not reach is a name bound from inside a scope it stopped
    at**: `global test_x` in a function the module calls binds one, and the
    `global` is written where this does not look. Following it means deciding
    which functions run at import, which is the interpreter this is not.
    """
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            yield from _at_the_scope_of(child)


def _runnable_but_unseen(node: ast.AST) -> tuple[str, ...]:
    """The name one module-scope node binds, where pytest would run it unseen.

    Four spellings of a binding and nothing else: the `class` statement, the
    `import` alias, an identifier the tree marks `Store` — which is one node type
    for assignment, unpacking, `for`, `with … as`, the walrus and the augmented
    forms, so none of those needs naming here — and a `match` pattern's capture,
    which is the one binding Python spells as a bare `str` on the node rather
    than as a `Name`, and so the one that has to be named separately.

    **Three of them are refused on what they bind rather than on the `test_`
    prefix**, because none of the three has to be called `test_…` to run: a
    `class` pytest would collect by type or by :data:`TEST_FLAG`, an `import` that
    binds a `TestCase`, and — the one thing here that is not a binding at all — an
    attribute assignment setting :data:`TEST_FLAG` on a name the module already
    bound.
    """
    if isinstance(node, ast.ClassDef):
        return (node.name,) if _is_a_test_case(node) else ()

    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        # Reached only for a `def` :func:`_tests_in` did not read — one nested
        # under an `if` or a `try`, which pytest runs and the collector never sees.
        name = node.name
    elif isinstance(node, ast.alias):
        # `import a.b` binds `a`; `from x import *` binds names this cannot read.
        name = node.asname or node.name.split(".", 1)[0]
        if _imports_a_test_case(node):
            return (name,)
    elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
        # `Leak.__test__ = True` binds nothing — it sets pytest's flag on
        # something already bound, and the flag is what runs it. Refused under
        # the name it mutates, which is where a reader would look. It is also the
        # shape with no class in it: `audit.__test__ = True` runs a module-level
        # `def` under a name no `test_` prefix would have caught.
        return (ast.unparse(node.value),) if node.attr == TEST_FLAG else ()
    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        name = node.id
    elif isinstance(node, ast.MatchAs | ast.MatchStar):
        # `case test_x:` and `case [*test_x]:`. `None` is the wildcard `case _:`,
        # which binds nothing.
        name = node.name or ""
    elif isinstance(node, ast.MatchMapping):
        # `case {**test_rest}:`, the third and last of the `str`-valued captures.
        name = node.rest or ""
    else:
        return ()

    return (name,) if name == STAR or name.startswith("test_") else ()


def classes_that_cannot_be_judged_in(directory: Path = HERE) -> tuple[str, ...]:
    """Module-scope classes here whose shape :func:`_is_a_test_case` cannot decide.

    The refusal beside this one answers *does pytest collect this class* off the
    `class` statement, and for a base it is not allowed to resolve there is no
    honest answer. Until #127 it answered **no** — a base spelled anything but
    `TestCase` was cleared, so `unittest.IsolatedAsyncioTestCase`, a base imported
    under another name and a class carrying :data:`TEST_FLAG` all ran here with
    nothing reported. Two of those are now decided on the line; the third cannot
    be, and this is where it is said out loud instead.

    **The clearance is narrow on purpose.** A class is cleared here only when it
    derives from nothing at all: `python_classes = []` leaves pytest two ways to
    reach a class — by type and by :data:`TEST_FLAG` — and a base-less class can
    be reached by neither, the flag having already been read by
    :func:`_is_flagged_as_a_test`. Any other base is a name whose class is decided
    somewhere this does not read, so a class carrying one is either matched by
    :func:`_is_a_test_case_base` and refused there or reported here. That is a
    wide net and it costs nothing: no `test_*.py` in this directory writes a
    module-scope class, and the invariant beside this is that none starts.

    **A keyword base is not read.** `class A(metaclass=M)` carries no base and is
    cleared, though a metaclass could return anything — the same boundary
    :func:`runnable_but_unseen_in` draws at `exec` and `globals()`, for the same
    reason.

    Args:
        directory: Where the test modules live.

    Returns:
        ``module::Name`` for each, in file and then source order.
    """
    return tuple(
        f"{path.name}::{node.name}"
        for path, tree in _modules_in(directory)
        for node in _at_the_scope_of(tree)
        if isinstance(node, ast.ClassDef) and node.bases and not _is_a_test_case(node)
    )


def _is_a_test_case(node: ast.ClassDef) -> bool:
    """Whether a class statement is one pytest collects and runs, read as written.

    Two mechanisms, because pytest has two: a base whose written name ends in
    :data:`TEST_CASE`, which `_pytest/unittest.py` collects by type; and
    :data:`TEST_FLAG` in the class body, which pytest reads off the object and no
    base rule could ever reach.
    """
    return any(_is_a_test_case_base(base) for base in node.bases) or _is_flagged_as_a_test(node)


def _is_a_test_case_base(base: ast.expr) -> bool:
    """Whether a base is written as a `TestCase`, in any spelling that reaches here.

    A **suffix** rather than the equality that stood here until #127: `TestCase`,
    `unittest.TestCase`, `unittest.case.TestCase`, `IsolatedAsyncioTestCase` and
    `FunctionTestCase` all match, and so would a `LedgerTestCase` somebody wrote.
    That last is the read-as-written bias :func:`runnable_but_unseen_in` states,
    taken again: the invariant is that no such class is in this directory at all,
    so a rename is the whole remedy for a false refusal, and a miss is the
    bijection broken silently.
    """
    if isinstance(base, ast.Name):
        return base.id.endswith(TEST_CASE)
    return isinstance(base, ast.Attribute) and base.attr.endswith(TEST_CASE)


def _is_flagged_as_a_test(node: ast.ClassDef) -> bool:
    """Whether a class body sets :data:`TEST_FLAG` to anything but a written `False`.

    **A class-body read, and the only one here.** The module walk stops at a
    `class` because its question is *what does the module bind*, and a class body
    binds nothing into the module. This asks a different question — *what is this
    class* — of a statement that walk already handed over, so it is a second
    mechanism rather than that rule bent: nothing about which names the check
    collects changes, and `@exercises` still means one thing. It is the same walk
    though, run over the class instead of the module, because `if os.name:
    __test__ = True` sets the flag exactly as a bare statement would.

    **The flag is read wherever the body binds it**, not only where the body
    assigns it plainly. A first cut here matched `__test__` as the target of an
    `=` and nothing else, which reproduced #127 one level down: `__test__, _ =
    True, 1`, `for __test__ in (True,)`, `with … as __test__`, `(__test__ :=
    True)` and `case __test__:` all leave the flag on the class and pytest
    collects every one of them. So this asks :func:`_binds_the_flag` the same
    question :func:`_runnable_but_unseen` asks of a module — *what does this
    scope bind* — and the spellings stop needing to be enumerated.

    `False` is `__test__`'s opt-out and is read as one, but **only where the
    value is written against the name**: `__test__ = False` opts out, and a
    binding with no value beside it — an unpacking, a loop, a capture — cannot
    be read as one and is refused. Anything else written there — a name, a call,
    a flag decided at import — is refused rather than resolved, which is the same
    bias as the suffix above and costs a rename when it is wrong.

    **The flag set from outside the class is not this function's**, and is not
    missed: `Leak.__test__ = True` on the line below is a module-scope statement,
    and :func:`_runnable_but_unseen` refuses it under the name it mutates.
    `setattr(Leak, "__test__", True)` is out of reach of both, which is the
    boundary :func:`runnable_but_unseen_in` draws at `exec` and `globals()` — the
    flag has to be an identifier on a line to be read.
    """
    opted_out: set[int] = set()
    for statement in _at_the_scope_of(node):
        if isinstance(statement, ast.Assign) and _is_written_false(statement.value):
            # Recorded by node identity rather than returned on, because the walk
            # hands over the target itself further down and it must not then read
            # as a bare binding. `__test__ = _x = False` writes off both.
            opted_out.update(id(target) for target in statement.targets)
        elif isinstance(statement, ast.AnnAssign) and _is_written_false(statement.value):
            opted_out.add(id(statement.target))
        elif _binds_the_flag(statement) and id(statement) not in opted_out:
            return True
    return False


def _binds_the_flag(node: ast.AST) -> bool:
    """Whether one node binds :data:`TEST_FLAG` into the scope it is written in.

    The two spellings :func:`_runnable_but_unseen` reads for a module, asked here
    of a class body: an identifier the tree marks `Store` — one node type for
    assignment, unpacking, `for`, `with … as`, the walrus and the augmented forms
    — and a `match` pattern's capture, which Python spells as a bare `str` on the
    node and so has to be named separately.

    **`except … as __test__` is deliberately not read.** It is the one binding
    Python takes back, deleting the name when the handler ends, so the class
    carries no flag and pytest collects nothing — measured, not reasoned from.
    """
    if isinstance(node, ast.Name):
        return node.id == TEST_FLAG and isinstance(node.ctx, ast.Store)
    if isinstance(node, ast.MatchAs | ast.MatchStar):
        return node.name == TEST_FLAG
    return isinstance(node, ast.MatchMapping) and node.rest == TEST_FLAG


def _is_written_false(value: ast.expr | None) -> bool:
    """Whether a value is the literal `False`, and not merely something falsey.

    Narrower than either half of what pytest does, and on purpose. pytest turns
    collection *on* with `safe_getattr(obj, "__test__", False) is True`
    (`_pytest/python.py`), so `__test__ = 1` reaches nothing; and it turns a
    `TestCase` *off* on any falsey value with `not getattr(cls, "__test__", True)`
    (`_pytest/unittest.py`), so `__test__ = 0` is an opt-out there. Reading either
    rule here would mean deciding which one applies, and that needs the base
    resolved. So only a written `False` clears a class, and `__test__ = 1` is
    refused though pytest would not collect it — a false refusal costing a rename,
    which is the trade this whole check is built on.
    """
    return isinstance(value, ast.Constant) and value.value is False


def _imports_a_test_case(node: ast.alias) -> bool:
    """Whether an import binds a class written as a `TestCase`, renamed or not.

    Two reasons, and the rename is only the first. `from unittest import TestCase
    as Base` puts a class pytest collects by type into this module under a name no
    rule here would look at twice — and it resolves nothing to notice, because
    both names are on the line. So the binding is refused where the rename is
    written, and the `class A(Base)` below it is left to
    :func:`classes_that_cannot_be_judged_in`, which is the honest answer to a base
    it can no longer read.

    The second is that the import can be the runnable shape on its own: `from
    unittest import FunctionTestCase` binds a concrete `TestCase` carrying a
    `runTest`, and pytest collects it in the importing module. So the un-renamed
    import is refused too — `from unittest import TestCase` reports a name pytest
    happens not to collect, which is a rename to fix and the bias this check takes
    everywhere.

    `import a.b.TestCase` is not this — it binds `a`, whose name says nothing —
    which is why the original is only read when it is what the line actually
    binds. The gap that leaves is a `TestCase` subclass imported under a name
    carrying no suffix at all; that one reaches the class rule or nothing.
    """
    binds_the_name_it_reads = node.asname is not None or "." not in node.name
    return binds_the_name_it_reads and node.name.rsplit(".", 1)[-1].endswith(TEST_CASE)


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

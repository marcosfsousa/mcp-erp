"""The suite's own invariants: the bijection, the floor, the standing index, and how a row asserts.

`scenarios.yaml` declares a `meta` block, and a count kept where it can be read
and not checked is what ADR-0011 caught drifting four times in one month. So
every number in it is asserted against the rows here — the same argument
`tests/matrix/test_the_matrix_holds_together.py` makes for the decision matrix,
and the same shape.

**The bijection is why the suite is trustworthy, and it is why the suite is not
split across tickets.** Every asserting row has a test that declares it by name;
every declaration names a row; every test in this directory declares something.
Break any of the three and a defence can be deleted without a red check — which
is the failure the report exists to make impossible, not a tidiness rule.

**The fourth invariant is about how a row asserts rather than which row it is.**
A refusal body written out beside a test is a copy of ADR-0002's mapping, and a
defence whose expectation is a copy goes on passing after the declaration under
it moves — green, and protecting nothing. #87 found them across this suite and
`tests/wire/`; the ones here are gone, and
:func:`~scenarios.restated_refusal_payloads` is what keeps them gone.

**One row is exempt and the exemption is derived, not written down.**
`threshold_split_evasion` asserts nothing, so it needs no test — and
:func:`~scenarios.rows_without_a_test` reads that off `status: documented`
rather than off the row's name. ADR-0010 rejected the alternative in the same
sentence that granted the exemption: *"the accepted-risk row has no test, and
would need a skipped one to hold its metadata. A skipped test in a security suite
is a bad thing to own."*

**Nothing in this file needs Compose.** It asks whether the table and the tests
agree, which is a question about two committed things, so a developer can run it
alone in a second. It is collected by `Attack suite (wire)` because it lives in
this directory and a suite that skipped its own invariants when run whole would
be a suite with a hole in it — the reading `Decision matrix (wire)` already takes
for the file this one is modelled on.
"""

import subprocess
import sys
from collections import Counter
from pathlib import Path

import scenario_table
import scenarios
import yaml
from scenarios import ASSERTED, DOCUMENTED, RETITLE_BELOW, Suite, read_suite, suite

SUITE: Suite = suite()
META = dict(SUITE.meta)
DECLARED = scenarios.declarations()

CEILING = 35
"""The soft ceiling `scenarios.yaml` states, and what crossing it is for.

Not a cap on coverage: crossing it reviews the split rule rather than refusing a
row, because the likely cause is two removals differing cosmetically. Asserted so
that the review happens rather than being remembered.
"""

FLOOR = {
    # One per gate step of ADR-0006's chain, in its order. The chain is the
    # security property, so a step with no falsifier is a step that can be
    # reordered or removed without a red check.
    "dns_rebinding_origin": "gate 1 — the Origin allow-list",
    "header_body_mismatch": "gate 2 — header and body must agree",
    "auth_bypass_via_method_header_mismatch": "gate 3 — the exemption, which is a branch",
    "token_expired": "gate 4 — the token gate",
    "insufficient_scope": "gate 5 — the scope gate",
    "retry_after_sod_denial_other_person": "gate 6 — the domain rule, and its remedy",
    # ADR-0009's three seam assertions. They keep their place for a different
    # reason than they were written for: the legacy leg is always on and nothing
    # else here touches it, so a regression on it would be invisible everywhere
    # else in the suite.
    "legacy_unauthenticated_refused": "seam — the always-on leg refuses strangers",
    "legacy_underscoped_same_denial_class": "seam — one scope rule, both legs",
    "legacy_discover_exemption_unavailable": "seam — the exemption is unavailable by absence",
    # Everything map ship line `#8` names: audience binding. Two rows, because
    # the check has two halves and a server passing one and failing the other
    # would still be accepting somebody else's token.
    "audience_confusion": "ship line #8 — a token addressed to another resource",
    "audience_missing": "ship line #8 — a token addressed to nobody at all",
}
"""The eleven rows that may never be downgraded, each beside what it holds up.

Written out rather than derived, because *which* rows the floor is made of is the
claim — `scenarios.yaml` states it in prose and this is the same sentence in a
form that fails. A row moving out of the floor changes this file, which is where
that decision should be visible.
"""


def test_the_declared_total_and_the_ceiling_hold() -> None:
    """The index's headline number, against the rows it indexes."""
    assert META["total"] == len(SUITE.rows)
    assert len(SUITE.rows) <= CEILING


def test_every_row_name_is_unique() -> None:
    """Names key the tests, so two rows of one name would be one row twice.

    `name` is the field the table calls *never reworded*: it is what a test
    declares and what the drift check joins on, and a duplicate would let one
    test stand for two rows.
    """
    assert len(SUITE.names) == len(SUITE.rows)


def test_the_declared_basis_split_agrees_with_the_rows() -> None:
    """Three bases, counted off the rows rather than trusted.

    The split is the number that moved when `list_partition_scoped` was declared
    and again when `unsupported_protocol_version` was minted, and a `total` that
    agrees while a split does not is the drift this catches.
    """
    assert META["basis_split"] == dict(Counter(row.basis for row in SUITE.rows))


def test_the_declared_strength_split_agrees_with_the_clause_rows() -> None:
    """Only clause rows carry a strength, so only they are counted."""
    counted = Counter(
        row.normative_strength for row in SUITE.rows if row.normative_strength is not None
    )

    assert META["strength_split"] == dict(counted)


def test_only_clause_rows_carry_a_normative_strength() -> None:
    """The table's own rule, in both directions.

    A `clause` row with no strength is a citation nobody read the keyword off;
    an `adr` or `seam` row with one is a project decision wearing a specification's
    authority, which is the misreading ADR-0010 built the field to prevent.
    """
    for row in SUITE.rows:
        if row.basis == "clause":
            assert row.normative_strength is not None, row.name
        else:
            assert row.normative_strength is None, row.name


def test_exactly_one_row_is_documented_and_it_prevents_nothing() -> None:
    """The invariant that keeps `documented` from becoming a third state.

    A row claiming `asserted` with nothing behind it is the defect this ticket
    inherited on two rows at once, and it is undetectable from the table alone —
    the bijection below is what makes it detectable. This asserts the other half:
    the one row that is allowed to assert nothing is allowed *because* it prevents
    nothing, and it carries no removal to perform.
    """
    documented = SUITE.documented

    assert [row.name for row in documented] == ["threshold_split_evasion"]
    assert documented[0].removal is None


def test_every_asserting_row_records_a_removal() -> None:
    """A row with no removal is a row nobody can falsify.

    The removal is the unit of proof and the unit of splitting alike (ADR-0010),
    so an asserting row without one has no statement of what deleting the defence
    would cost — and two rows can no longer be told apart by their deletions.
    """
    for row in SUITE.asserted:
        assert row.removal is not None, row.name


def test_the_floor_is_exactly_the_eleven_rows_that_hold_the_chain_up() -> None:
    """The floor, marked: which rows, and what each one holds.

    Set equality rather than a count, because a floor of eleven made of a
    different eleven would satisfy a count and lose a gate step. The declared
    number is checked here too, against the same set, rather than beside the
    total — it is a fact about which rows the floor is made of.
    """
    assert {row.name for row in SUITE.rows if row.floor} == set(FLOOR)
    assert META["floor"] == len(FLOOR)


def test_no_floor_row_is_merely_documented() -> None:
    """*May never be downgraded* is the whole content of the field."""
    for row in SUITE.rows:
        if row.floor:
            assert row.status == ASSERTED, row.name


def test_the_table_still_earns_the_name_attack_suite() -> None:
    """Above the line where the write-up has to retitle, and the line is asserted.

    `scenarios.yaml` states it as an invariant of the artifact — below twenty
    asserting rows the table is a *clause inventory, N proven* rather than an
    attack suite — and a threshold nothing checks is a promise about a future
    edit. Cutting tests down to the floor is permitted; doing it and keeping the
    title is not.
    """
    assert len(SUITE.asserted) >= RETITLE_BELOW, (
        f"{len(SUITE.asserted)} asserting rows: the write-up retitles this table "
        f"to 'clause inventory, {len(SUITE.asserted)} proven'"
    )


def test_every_row_carries_a_status_the_table_defines() -> None:
    """Two values, and no third one arriving by typo."""
    assert {row.status for row in SUITE.rows} <= {ASSERTED, DOCUMENTED}


def test_nothing_is_held_out_and_minted_at_the_same_time() -> None:
    """A candidate outside the table cannot also be a row inside it.

    `unsupported_protocol_version` sat in `held_out` from #9 until #44 minted it,
    and the failure mode while it did was a reader taking the note for a proven
    row. The entry is gone now; this is what would catch it coming back beside
    the row it became.
    """
    held_out = {entry["name"] for entry in META.get("held_out") or ()}

    assert not held_out & SUITE.names


# ─── The bijection ────────────────────────────────────────────────────────────


def test_every_asserting_row_has_a_test_that_declares_it() -> None:
    """The first half. A row with no falsifier is a defence nothing protects."""
    assert scenarios.rows_without_a_test(SUITE, DECLARED) == set()


def test_every_declaration_names_a_row_that_exists() -> None:
    """The second half. A declaration naming nothing is a test the table cannot find."""
    assert scenarios.declarations_naming_no_row(SUITE, DECLARED) == set()


def test_every_test_in_this_directory_declares_a_row() -> None:
    """The third. An undeclared test is a hole in the report rather than in a defence.

    The one exemption is this module, which is about the table rather than about
    an attack — named once in `scenarios.INVARIANTS` rather than inferred from
    what a file happens to assert.
    """
    assert scenarios.tests_without_a_declaration() == ()


def test_nothing_here_runs_in_a_shape_the_collector_cannot_see() -> None:
    """The third invariant's blind spot, closed by refusing the shapes that open it.

    `pyproject.toml` narrows what pytest collects so that it and
    :func:`~scenarios._tests_in` agree — but that narrowing reaches what is
    *named*, and the collector reads a syntax tree while pytest reads a module
    namespace. A `test_*` name that arrives without being written as a
    module-level `def` runs unseen: it declares no row and the check above
    reports nothing, which is the bijection broken silently.

    Three arrivals, none of them closable from `pyproject.toml` and all three
    measured (#112): a `unittest.TestCase` subclass, which pytest collects by
    *type* whatever it is named; a `test_*` name bound by import; and one bound
    by assignment. :func:`test_the_shapes_that_refusal_is_for` runs each and
    shows what it costs.

    **Refused rather than collected**, because the alternatives are worse:
    resolving imports and assignments makes the collector an interpreter, and
    collecting a declaration out of a class body makes `@exercises` mean two
    things. Nothing here is written in any of the three.

    A class body *is* read since #127, for :data:`~scenarios.TEST_FLAG` and
    nothing else. That is neither alternative: it collects no declaration and
    binds no name, and it answers about the class the module-scope walk already
    stopped at rather than descending past it to look for tests.
    """
    assert scenarios.runnable_but_unseen_in() == ()


def test_no_class_here_is_one_the_check_cannot_judge() -> None:
    """The same blind spot from the other side: a class it can neither clear nor refuse.

    The refusal above answers *is this a test case* off the `class` statement,
    and for a base it cannot read — one imported under another name, one from a
    helper — there is no honest answer. Answering "no" by default is what let
    three collected shapes through (#127), so the check reports the question
    instead, and this asserts the directory never asks it.

    A class with no bases at all is cleared rather than reported: under
    `python_classes = []` pytest reaches a class by type or by `__test__`, and
    one deriving from nothing can be neither. Every other class here would be
    reported, which costs nothing today because this directory writes none.
    """
    assert scenarios.classes_that_cannot_be_judged_in() == ()


# ─── How a row asserts ────────────────────────────────────────────────


def test_no_refusal_body_in_this_directory_is_written_out() -> None:
    """Every refusal a row asserts is read off the record, never written out beside it.

    Not tidiness. A defence asserted against a copy of ADR-0002's mapping keeps
    passing after the declaration under it changes — the suite stays green and
    the thing it was protecting is gone. `refusal_records.refusal_body` derives
    the body from the `Reason` instead, so the two disagree loudly.

    What pins the values themselves is
    `tests/matrix/test_the_reason_mapping.py`, which holds ADR-0002's table over
    both declared sets in both directions. That is where a literal is the
    assertion rather than a copy of one.
    """
    assert scenarios.restated_refusal_payloads() == ()


def test_a_row_added_without_a_test_fails_the_drift_check() -> None:
    """The demonstration, run rather than described.

    A new row arrives exactly like this: appended to the table, `status:
    asserted`, with nothing declaring it yet. The check has to name it, and the
    only way to know it does is to add one — so this appends a row to the
    committed text in memory, parses that, and asserts the check reports it.
    Nothing is written to the working tree.
    """
    appended = (
        (scenarios.REPO / scenarios.SCENARIOS).read_text(encoding="utf-8")
        + """
  - name: a_row_nothing_falsifies
    basis: adr
    prevents: Nothing. It exists for the length of this assertion.
    citation:
      source: ADR-0010 §The list is data; the tests are hand-written
    normative_strength: null
    removal: Delete the check that reported this row.
    status: asserted
    floor: false
"""
    )
    grown = read_suite(appended)

    assert grown.names - SUITE.names == {"a_row_nothing_falsifies"}
    assert scenarios.rows_without_a_test(grown, DECLARED) == {"a_row_nothing_falsifies"}


def test_a_test_declaring_a_row_that_does_not_exist_fails_the_drift_check(
    tmp_path: Path,
) -> None:
    """The other direction, demonstrated the same way: a renamed row leaves a test behind.

    Written into a temporary directory rather than into this one, because the
    collector reads a directory's source and the thing under test is what it does
    with a declaration nobody deleted.
    """
    (tmp_path / "test_something_renamed.py").write_text(
        '@exercises("a_row_that_was_renamed")\ndef test_it() -> None:\n    pass\n',
        encoding="utf-8",
    )
    stray = scenarios.declarations(tmp_path)

    assert [entry.scenario for entry in stray] == ["a_row_that_was_renamed"]
    assert scenarios.declarations_naming_no_row(SUITE, stray) == {
        "test_something_renamed.py::test_it declares 'a_row_that_was_renamed'"
    }


def test_the_collector_sees_the_two_shapes_that_could_have_escaped_it(tmp_path: Path) -> None:
    """A test in a subdirectory, and a test that is `async def`. Both are collected.

    Neither exists in this directory today, and that is the reason to assert
    them: the bijection is a claim about *every* test here, and a collector that
    silently skipped a shape would keep making the claim while it stopped being
    true. pytest would collect both.
    """
    nested = tmp_path / "deeper"
    nested.mkdir()
    (nested / "test_in_a_subdirectory.py").write_text(
        '@exercises("a_row")\ndef test_it() -> None:\n    pass\n', encoding="utf-8"
    )
    (tmp_path / "test_asynchronous.py").write_text(
        '@exercises("another_row")\nasync def test_it() -> None:\n    pass\n', encoding="utf-8"
    )

    assert {entry.scenario for entry in scenarios.declarations(tmp_path)} == {
        "a_row",
        "another_row",
    }


def test_pytest_collects_exactly_what_the_collector_sees(tmp_path: Path) -> None:
    """The third direction of the bijection, and the one nobody writes down.

    *Every row has a falsifier* and *every falsifier names a row* are asserted
    above. The direction neither covers is **no test in this directory declaring
    nothing** — and a test pytest runs that :func:`~scenarios._tests_in` cannot
    see satisfies both halves while breaking that one, invisibly.

    Under pytest's defaults there were three such shapes: `*_test.py`, methods of
    `Test*` classes, and a function named `testfoo`. `pyproject.toml` narrows
    collection to what the collector implements rather than the collector growing
    to match — one declaration of *what counts as a test here* instead of two
    that must be kept equal.

    **The narrowing reaches what is named, and this equality is only over that.**
    A `test_*` name that never appears as a module-level `def` — a
    `unittest.TestCase` method, a name bound by import, a name bound by
    assignment — is in the module namespace pytest reads and not in the syntax
    tree the collector reads, and no setting closes any of the three. So this
    asserts the equality over the shapes settings decide, and
    :func:`test_nothing_here_runs_in_a_shape_the_collector_cannot_see` refuses
    the shapes they do not.

    **Asserted by running pytest, not by reading the setting.** Restating the
    three patterns here would be the second declaration the narrowing exists to
    avoid; what is checked instead is the equality itself, over a directory
    holding one file of every shape. That is also the only form that stays true
    if a later pytest changes what a pattern means.
    """
    (tmp_path / "test_seen.py").write_text("def test_it() -> None:\n    pass\n", encoding="utf-8")
    (tmp_path / "suffix_test.py").write_text("def test_it() -> None:\n    pass\n", encoding="utf-8")
    (tmp_path / "test_in_a_class.py").write_text(
        "class TestThings:\n    def test_it(self) -> None:\n        pass\n", encoding="utf-8"
    )
    (tmp_path / "test_no_underscore.py").write_text(
        "def testit() -> None:\n    pass\n", encoding="utf-8"
    )

    assert _collected_by_pytest(tmp_path) == {
        f"{path.name}::{function.name}" for path, function in scenarios._tests_in(tmp_path)
    }


def test_the_shapes_that_refusal_is_for(tmp_path: Path) -> None:
    """The hole, run in all three of its shapes rather than described.

    The `TestCase` is named for what it tests rather than for the framework,
    which is what makes it worth refusing: it is collected by type, so the name
    changes nothing and a reader checking `python_classes` would conclude the
    opposite. The other two need no trick at all — a `test_*` name is a function
    in the module namespace however it got there.

    All three at once, because the claim is about the *set* the collector misses
    and a file each would let one be closed while the others stayed open. What
    the assertions say together is what a defence deleted without a red check
    looks like: pytest runs three tests, the collector sees none of them, and the
    *every test declares a row* check reports nothing at all.
    """
    (tmp_path / "test_a_test_case.py").write_text(
        "import unittest\n\n\nclass CostCentreLeakage(unittest.TestCase):\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "helper.py").write_text(
        "def test_imported() -> None:\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "test_alias.py").write_text(
        "from helper import test_imported\n\n\n"
        "def _inner() -> None:\n    pass\n\n\n"
        "test_assigned = _inner\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == {
        "test_a_test_case.py::CostCentreLeakage::test_it",
        "test_alias.py::test_imported",
        "test_alias.py::test_assigned",
    }
    assert tuple(scenarios._tests_in(tmp_path)) == ()
    assert scenarios.tests_without_a_declaration(tmp_path) == ()
    assert scenarios.runnable_but_unseen_in(tmp_path) == (
        "test_a_test_case.py::CostCentreLeakage",
        "test_alias.py::test_imported",
        "test_alias.py::test_assigned",
    )


def test_the_refusal_is_a_rule_and_not_a_list_of_the_three(tmp_path: Path) -> None:
    """The shapes nobody enumerated, which is the whole reason the rule is one.

    The three above were found by asking *how could a test arrive unseen* and
    writing down the answers. That question has no last answer, and a refusal
    written as the list of answers so far is a hole with a bibliography: every
    binding form Python has is another way in, and unpacking, `for`, `with … as`,
    the walrus, an import under an `if` and a `def` under one are six that the
    enumeration let through while reporting nothing at all.

    So the check refuses what the *tree* marks as a binding rather than the forms
    a reader thought of, and this is the assertion that says so — every name here
    is one pytest actually collects, taken from a real `--collect-only` run, and
    none of them appears in `runnable_but_unseen_in`'s docstring as a shape to
    look for.

    **The wildcard is the one that reports something else.** `from helper import
    *` binds names that are in the other module, so there is no identifier on the
    line; it is refused under :data:`scenarios.STAR` instead, which is a refusal
    to read a second file rather than a failure to.

    **The `match` capture is the one that needed naming.** Every other binding
    here is an `ast.Name` the tree marks `Store`, which is what lets the rule be
    one line; a capture pattern carries its name as a bare `str` on the node
    instead, so a rule written over `Store` alone reads `case test_captured:` as
    binding nothing while pytest collects it. It is in this list because that is
    the shape a rule can miss while looking complete.
    """
    (tmp_path / "helper.py").write_text(
        "def test_imported() -> None:\n    pass\n\n\ndef test_conditionally() -> None:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_every_other_way_in.py").write_text(
        "import contextlib\nimport os\n\n\n"
        "def _inner() -> None:\n    pass\n\n\n"
        "test_unpacked, test_beside_it = _inner, _inner\n\n"
        "for test_looped in (_inner,):\n    pass\n\n"
        "with contextlib.nullcontext(_inner) as test_bound:\n    pass\n\n"
        "if (test_walrus := _inner) is not None:\n    pass\n\n"
        "if os.name:\n    from helper import test_conditionally\n\n"
        "if os.name:\n\n    def test_under_a_branch() -> None:\n        pass\n\n"
        "match _inner:\n    case test_captured:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_star.py").write_text("from helper import *\n", encoding="utf-8")

    assert _collected_by_pytest(tmp_path) == {
        "test_every_other_way_in.py::test_unpacked",
        "test_every_other_way_in.py::test_beside_it",
        "test_every_other_way_in.py::test_looped",
        "test_every_other_way_in.py::test_bound",
        "test_every_other_way_in.py::test_walrus",
        "test_every_other_way_in.py::test_conditionally",
        "test_every_other_way_in.py::test_under_a_branch",
        "test_every_other_way_in.py::test_captured",
        "test_star.py::test_imported",
        "test_star.py::test_conditionally",
    }
    assert tuple(scenarios._tests_in(tmp_path)) == ()
    assert scenarios.tests_without_a_declaration(tmp_path) == ()
    assert scenarios.runnable_but_unseen_in(tmp_path) == (
        "test_every_other_way_in.py::test_unpacked",
        "test_every_other_way_in.py::test_beside_it",
        "test_every_other_way_in.py::test_looped",
        "test_every_other_way_in.py::test_bound",
        "test_every_other_way_in.py::test_walrus",
        "test_every_other_way_in.py::test_conditionally",
        "test_every_other_way_in.py::test_under_a_branch",
        "test_every_other_way_in.py::test_captured",
        f"test_star.py::{scenarios.STAR}",
    )


def test_a_class_is_judged_by_what_pytest_runs_and_not_by_one_base_name(
    tmp_path: Path,
) -> None:
    """The three shapes a literal `TestCase` missed, run rather than described.

    `_pytest/unittest.py` collects a `TestCase` subclass by *type*, and `unittest`
    spells a `TestCase` three ways: `TestCase`, `IsolatedAsyncioTestCase` and
    `FunctionTestCase`. A fourth class arrives with no base worth reading at all —
    `__test__ = True` is a flag pytest checks on the object, which `python_classes
    = []` does not reach. All four run here and all four were passing the refusal
    unrefused, because the check compared a base's last identifier against the
    literal string (#127).

    So the base test is a **suffix** and the flag is a second mechanism, read off
    the class body. The suffix carries the read-as-written bias the rest of this
    refusal takes: a class deriving from something a reader would call
    `LedgerTestCase` is refused too, and a rename is the whole remedy because the
    invariant is that no such class is in this directory at all.

    **`FunctionTestCase` is the one that reports twice.** Importing it binds a
    concrete `TestCase` subclass into the module, and pytest collects that import
    as well as the subclass below it — which is why the import is refused under
    its own name rather than only the `class` statement being.
    """
    (tmp_path / "test_async_case.py").write_text(
        "import unittest\n\n\nclass PartitionLeak(unittest.IsolatedAsyncioTestCase):\n"
        "    async def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_function_case.py").write_text(
        "from unittest import FunctionTestCase\n\n\nclass ScopeLeak(FunctionTestCase):\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_the_flag.py").write_text(
        "class CostCentreLeak:\n    __test__ = True\n\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == {
        "test_async_case.py::PartitionLeak::test_it",
        "test_function_case.py::FunctionTestCase::runTest",
        "test_function_case.py::ScopeLeak::test_it",
        "test_the_flag.py::CostCentreLeak::test_it",
    }
    assert tuple(scenarios._tests_in(tmp_path)) == ()
    assert scenarios.tests_without_a_declaration(tmp_path) == ()
    assert scenarios.runnable_but_unseen_in(tmp_path) == (
        "test_async_case.py::PartitionLeak",
        "test_function_case.py::FunctionTestCase",
        "test_function_case.py::ScopeLeak",
        "test_the_flag.py::CostCentreLeak",
    )


def test_a_base_renamed_on_the_import_line_is_read_there(tmp_path: Path) -> None:
    """`from unittest import TestCase as Base` resolves nothing — the original is written.

    A base spelled `Base` is unreadable at the `class` statement, and the check
    is not allowed to go looking for it. It does not have to: the import line
    carries both names, so the binding is refused where the rename happens. The
    class below it is then reported as one the check cannot judge, which is the
    honest answer to a name it can no longer read — and between the two, nothing
    about this module passes quietly.
    """
    (tmp_path / "test_renamed.py").write_text(
        "from unittest import TestCase as Base\n\n\nclass RowProbe(Base):\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == {"test_renamed.py::RowProbe::test_it"}
    assert scenarios.runnable_but_unseen_in(tmp_path) == ("test_renamed.py::Base",)
    assert scenarios.classes_that_cannot_be_judged_in(tmp_path) == ("test_renamed.py::RowProbe",)


def test_a_base_from_another_module_is_reported_rather_than_cleared(tmp_path: Path) -> None:
    """The base whose name says nothing, which is the case with no reading left.

    `from helper import Base` binds a `TestCase` subclass under a name that
    carries no suffix to match and no original to read — the answer is in the
    other file, and reading it is the import resolver this is not. So neither
    refusal fires and the class is reported as undecided instead, which is the
    difference between a check that says *I cannot tell* and one that says *no*.

    The helper's own base is deliberately test-free, so pytest collects nothing
    from the import itself: what runs is the subclass written here, and it is the
    only thing this has to account for.
    """
    (tmp_path / "helper.py").write_text(
        "import unittest\n\n\nclass Base(unittest.TestCase):\n    pass\n", encoding="utf-8"
    )
    (tmp_path / "test_quiet.py").write_text(
        "from helper import Base\n\n\nclass RetryAfterRefusal(Base):\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == {"test_quiet.py::RetryAfterRefusal::test_it"}
    assert scenarios.runnable_but_unseen_in(tmp_path) == ()
    assert scenarios.classes_that_cannot_be_judged_in(tmp_path) == (
        "test_quiet.py::RetryAfterRefusal",
    )


def test_the_flag_is_refused_wherever_it_is_written(tmp_path: Path) -> None:
    """The flag under a branch, and the flag set from outside the class.

    `__test__` is the one thing here that reaches pytest without being a base and
    without being a `test_*` name, and a first cut at reading it read the class
    body's top level only — which is the #127 failure in miniature: `if TYPE_CHECKING`
    around it, or `Leak.__test__ = True` on the line below the class, and the
    class is cleared while pytest runs it. Both are on a line a reader can see,
    so both are read.

    The second is not a binding at all — it mutates a name already bound — and it
    is refused under the name it mutates, which is where a reader would look for
    it. That also reaches the shape with no class in it: a module-level `def`
    carrying the flag runs under its own name whatever that name is.
    """
    (tmp_path / "test_under_a_branch.py").write_text(
        "import os\n\n\nclass PartitionLeak:\n    if os.name:\n        __test__ = True\n\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_set_from_outside.py").write_text(
        "class ScopeLeak:\n    def test_it(self) -> None:\n        pass\n\n\n"
        "ScopeLeak.__test__ = True\n\n\n"
        "def audit() -> None:\n    pass\n\n\naudit.__test__ = True\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == {
        "test_under_a_branch.py::PartitionLeak::test_it",
        "test_set_from_outside.py::ScopeLeak::test_it",
        "test_set_from_outside.py::audit",
    }
    assert scenarios.runnable_but_unseen_in(tmp_path) == (
        "test_set_from_outside.py::ScopeLeak",
        "test_set_from_outside.py::audit",
        "test_under_a_branch.py::PartitionLeak",
    )


def test_the_flag_is_read_from_every_shape_that_binds_it(tmp_path: Path) -> None:
    """`=` is one spelling of a binding, and reading only that one repeats #127.

    Each class here leaves `__test__` on itself without ever writing `__test__ =`,
    and the assertion is a real `--collect-only` run: pytest collects all six, so
    a check that reads the assignment alone clears six classes it runs. The
    remedy is the one the module walk already uses — ask what the scope *binds*,
    which is one `Store` identifier for the unpacking, the loop, the `with` and
    the walrus, plus the `match` capture Python spells as a `str`.

    `except … as __test__` is the shape deliberately left out, and it is here to
    hold that out: Python deletes the name when the handler ends, so the class
    carries no flag, pytest collects nothing, and silence is the right answer
    rather than a gap.
    """
    (tmp_path / "test_bound_without_an_assignment.py").write_text(
        "import contextlib\n\n\n"
        "class TupleLeak:\n    __test__, _spare = True, 1\n\n"
        "    def test_it(self) -> None:\n        pass\n\n\n"
        "class ListLeak:\n    [__test__, _spare] = [True, 1]\n\n"
        "    def test_it(self) -> None:\n        pass\n\n\n"
        "class LoopLeak:\n    for __test__ in (True,):\n        pass\n\n"
        "    def test_it(self) -> None:\n        pass\n\n\n"
        "class ContextLeak:\n"
        "    with contextlib.nullcontext(True) as __test__:\n        pass\n\n"
        "    def test_it(self) -> None:\n        pass\n\n\n"
        "class WalrusLeak:\n    _spare = (__test__ := True)\n\n"
        "    def test_it(self) -> None:\n        pass\n\n\n"
        "class MatchLeak:\n    match True:\n        case __test__:\n            pass\n\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_taken_back.py").write_text(
        "class HandlerLeak:\n    try:\n        raise ValueError\n"
        "    except ValueError as __test__:\n        pass\n\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == {
        "test_bound_without_an_assignment.py::TupleLeak::test_it",
        "test_bound_without_an_assignment.py::ListLeak::test_it",
        "test_bound_without_an_assignment.py::LoopLeak::test_it",
        "test_bound_without_an_assignment.py::ContextLeak::test_it",
        "test_bound_without_an_assignment.py::WalrusLeak::test_it",
        "test_bound_without_an_assignment.py::MatchLeak::test_it",
    }
    assert scenarios.runnable_but_unseen_in(tmp_path) == (
        "test_bound_without_an_assignment.py::TupleLeak",
        "test_bound_without_an_assignment.py::ListLeak",
        "test_bound_without_an_assignment.py::LoopLeak",
        "test_bound_without_an_assignment.py::ContextLeak",
        "test_bound_without_an_assignment.py::WalrusLeak",
        "test_bound_without_an_assignment.py::MatchLeak",
    )


def test_the_flag_written_off_is_read_off_only_where_the_value_is_written(
    tmp_path: Path,
) -> None:
    """Which side each false refusal falls on, asserted rather than described.

    Two classes pytest does not collect are refused anyway. `__test__ = 1` is
    truthy but not `True`, and pytest enables collection on `is True` alone; a
    class carrying the flag with no `test_*` method has nothing to run. Reading
    either would mean modelling pytest's two opposed rules — `is True` to enable,
    any falsey value to opt a `TestCase` out — and deciding which applies needs
    the base resolved. So both are refused, and the cost is a rename.

    `__test__ = False` is cleared, and only where the `False` is written against
    the name: unpacked out of a tuple it is a binding with no readable value and
    is refused like the rest.
    """
    (tmp_path / "test_refused_anyway.py").write_text(
        "class TruthyLeak:\n    __test__ = 1\n\n"
        "    def test_it(self) -> None:\n        pass\n\n\n"
        "class EmptyLeak:\n    __test__ = True\n\n"
        "    def helper(self) -> None:\n        pass\n\n\n"
        "class UnpackedOff:\n    __test__, _spare = False, 1\n\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )
    (tmp_path / "test_written_off.py").write_text(
        "class OptedOut:\n    __test__ = False\n\n    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == set()
    assert scenarios.runnable_but_unseen_in(tmp_path) == (
        "test_refused_anyway.py::TruthyLeak",
        "test_refused_anyway.py::EmptyLeak",
        "test_refused_anyway.py::UnpackedOff",
    )


def test_a_class_pytest_cannot_reach_is_left_alone(tmp_path: Path) -> None:
    """The other direction, so the widening is a judgment and not a blanket refusal.

    Under `python_classes = []` a class is collected by type or by `__test__` and
    by nothing else, so a class deriving from nothing is unreachable however it is
    named — `TestThings` included, which is the name a reader would expect to be
    caught and the one `pyproject.toml` turned off. `__test__ = False` is the
    documented opt-out and is read as one *here*, where there is no base to read:
    the class judgment ORs the base test first, so a `TestCase` subclass writing
    the flag off is still refused. That is a false refusal costing a rename, which
    is the trade the whole check is built on.

    Asserted because a check that refused every class would satisfy the invariant
    above by refusing to think, and this directory would never notice.
    """
    (tmp_path / "test_unreachable.py").write_text(
        "class TestThings:\n    def test_it(self) -> None:\n        pass\n\n\n"
        "class Helper:\n    def test_it(self) -> None:\n        pass\n\n\n"
        "class OptedOut:\n    __test__ = False\n\n"
        "    def test_it(self) -> None:\n        pass\n",
        encoding="utf-8",
    )

    assert _collected_by_pytest(tmp_path) == set()
    assert scenarios.runnable_but_unseen_in(tmp_path) == ()
    assert scenarios.classes_that_cannot_be_judged_in(tmp_path) == ()


def _collected_by_pytest(directory: Path) -> set[str]:
    """What pytest, configured as this repo configures it, collects from a directory.

    A subprocess rather than an in-process hook, because the question is about
    the settings in `pyproject.toml` and the run that reads them — an in-process
    collection would inherit this session's own configuration and answer a
    different question.

    **`-c`, not `--rootdir`.** pytest finds its configuration by walking up from
    the arguments, and the arguments here are a temporary directory outside the
    checkout — so `--rootdir` moves where paths are reported from and leaves the
    settings at their defaults, which is the very state this asserts against.
    Naming the file is what makes the run the repo's own.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
            "-c",
            str(scenarios.REPO / "pyproject.toml"),
            str(directory),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # `5` is pytest's *nothing collected*, which is an answer to this question
    # rather than a failure of it: a caller asserting that a directory's classes
    # are out of pytest's reach expects an empty set back, not a raise.
    assert completed.returncode in (0, 5), completed.stdout + completed.stderr
    return {
        line.strip().rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        for line in completed.stdout.splitlines()
        if "::" in line
    }


def test_a_test_carrying_no_declaration_is_reported(tmp_path: Path) -> None:
    """And the third direction: a test that says nothing about which row it is for.

    This is the shape a test written in a hurry takes, and it is invisible from
    the table — every row still has a falsifier, and the suite has grown an
    assertion nobody can trace to a defence.
    """
    (tmp_path / "test_undeclared.py").write_text(
        "def test_it() -> None:\n    pass\n", encoding="utf-8"
    )

    assert scenarios.tests_without_a_declaration(tmp_path) == ("test_undeclared.py::test_it",)


# ─── The rendering ────────────────────────────────────────────────────────────


def _boolean_citation_keys() -> set[str]:
    """Citation keys the table writes as a YAML boolean, read off the file itself.

    Read from the raw document rather than from :class:`~scenarios.Scenario`,
    because the parse coerces every citation value to `str` and `True` arrives
    indistinguishable from a one-word quotation. The renderer sees what the parse
    hands it; this sees what the author wrote.
    """
    document = yaml.safe_load((scenarios.REPO / scenarios.SCENARIOS).read_text(encoding="utf-8"))

    return {
        str(key)
        for entry in document["scenarios"]
        for key, value in entry["citation"].items()
        if isinstance(value, bool)
    }


def test_a_boolean_citation_key_never_renders_as_a_quotation() -> None:
    """A flag says something *about* the quote; it is not part of it.

    `quote_elided: true` sat in `scenario_table.QUOTED` and the write-up
    published `> True` under *Quoted with an elision* seven times. Nothing caught
    it: `Seed renders clean` asks only whether re-rendering leaves the tree
    clean, and a wrong rendering is stably wrong. So this asserts the property
    that check cannot — every blockquote in the document is prose somebody
    wrote, and a boolean reaches the reader as its label or not at all.
    """
    booleans = _boolean_citation_keys()
    rendered = scenario_table.render(SUITE)
    blockquotes = {
        line.removeprefix("> ") for line in rendered.splitlines() if line.startswith("> ")
    }

    assert booleans, "no row carries a flag, so this assertion proves nothing — check the table"
    assert booleans <= scenario_table.FLAGS
    assert booleans.isdisjoint(scenario_table.QUOTED)
    assert not blockquotes & {"True", "False"}
    for key in booleans:
        assert scenario_table.LABELS[key] in rendered, (
            f"{key} renders neither its label nor a value"
        )


def test_every_blockquote_is_a_sentence_some_citation_carries() -> None:
    """Every blockquote is a citation value **verbatim**, character for character.

    What this catches is a renderer that alters a quotation on the way out — a
    prefix left on, a value truncated, a line the renderer composed rather than
    copied. On a table whose whole value is that its citations are real, a
    sentence nobody wrote is the worst available failure.

    **What it cannot catch, deliberately named.** Both sides of the comparison
    read `scenario_table.QUOTED`, so a key wrongly listed as quotable lands in
    `carried` and in `blockquotes` together and this stays green.
    `test_a_boolean_citation_key_never_renders_as_a_quotation` above is the
    assertion that bites there — it reads the booleans off the raw table rather
    than off `QUOTED`, which is why it was red against the renderer that
    published `> True` seven times. This one is kept beside it because the two
    fail on different defects, not because it is the general case of the other.
    """
    carried = {
        row.citation[key]
        for row in SUITE.rows
        for key in row.citation
        if key in scenario_table.QUOTED
    }
    blockquotes = {
        line.removeprefix("> ")
        for line in scenario_table.render(SUITE).splitlines()
        if line.startswith("> ")
    }

    assert blockquotes <= carried

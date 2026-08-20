"""The suite's own invariants: the bijection, the floor, and the standing index.

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

import scenarios
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
    assert completed.returncode == 0, completed.stdout + completed.stderr
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

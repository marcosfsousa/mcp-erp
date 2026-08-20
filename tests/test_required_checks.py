"""The name contract: ADR-0013's table, `ci.yml`'s jobs, and what `main` requires.

A job's `name:` is the status-check identifier branch protection matches, and it
matches by *string*. GitHub does not verify that a required context corresponds
to anything, so renaming a job detaches any rule pointing at the old name: the
check never reports, and **a rule waiting on a check that never arrives is
indistinguishable from one that has not run yet.** The pull request sits pending
rather than failing — which reads as "still working" instead of "misconfigured",
on the pull request that did the renaming, with a green tick.

That is what this file exists to make impossible, and it is why the equality is
asserted **in both directions**: a job with no required context is a seam nothing
gates, and a required context with no job is a branch that can never merge.

**Three documents, not two.** #66 found ADR-0013's table and `ci.yml` disagreeing
in both directions at once — two rows missing from one and one row missing from
the other — so the table is held here too, against the workflow as merged rather
than as described. The ruleset is the third, and it is the one that is not a
file; :mod:`required_checks` reads it from the API for the reason stated there.

**Nothing in this file needs Compose.** It asks whether three enumerations of one
set agree, and it runs in its own job — `Required checks match the ruleset` —
because it must not sit on a cut path. Cutting the decision matrix, third on cut
order `#9`, removes *Decision matrix (wire)* and *Seed renders clean* together,
and a name-contract test inside either would be cut in silence, taking the
argument for required checks with it. *Lint and types* would hold it uncuttably
and would then mean two unrelated things, against ADR-0013's own rule.
"""

from typing import Any

from required_checks import (
    adr_table,
    branch_rules,
    force_pushes_blocked,
    names,
    read_workflow,
    required_contexts,
    source,
    table_job_names,
    trigger_filters,
)

SOURCE = source()
"""The workflow as committed, kept as text because half the checks below edit it."""

JOBS = read_workflow(SOURCE)
"""Its jobs, parsed from those same bytes rather than from a second read."""

CONTEXTS = names(JOBS)
"""The contexts they produce, which is what a ruleset has to match by string."""


def rules_requiring(*contexts: str) -> list[Any]:
    """A branch-rules payload requiring exactly the given contexts.

    The shape GitHub returns, written out here rather than fetched, so the
    demonstrations below can show what this check does with a ruleset that does
    not exist yet — including the one this ticket had to be careful never to
    create: a required context no job produces.

    Its keys are spelled out rather than taken from :mod:`required_checks`'s
    constants, deliberately: this is a transcription of the wire shape, and a
    transcription written through the reader's own vocabulary would agree with
    the reader by construction.

    Args:
        contexts: The contexts the synthetic rule requires.

    Returns:
        A payload with one required-status-checks rule.
    """
    return [
        {
            "type": "required_status_checks",
            "parameters": {
                "required_status_checks": [{"context": context} for context in contexts],
                "strict_required_status_checks_policy": False,
            },
        }
    ]


# ─── The set, as three documents write it ─────────────────────────────────────


def test_every_job_reports_a_context_no_other_job_reports() -> None:
    """Two jobs of one name would be one context standing for two seams.

    The whole contract is a string match, so a duplicated `name:` gives a ruleset
    no way to require one of them — and *one job per seam* would be silently
    false while both documents still counted ten.
    """
    assert len(CONTEXTS) == len(JOBS)


def test_the_adr_table_lists_each_job_once() -> None:
    """The same claim on the table's side, before it is compared to anything."""
    table = adr_table()

    assert len(set(table)) == len(table)


def test_the_workflow_and_the_adr_table_name_the_same_jobs() -> None:
    """ADR-0013 enumerates the seams; `ci.yml` implements them. Neither may lead.

    This is the direction #66 had to fix by hand: *Server posture* was a job with
    no row, and *Published documents are immutable* had been a job with no row
    since the workflow shipped. A row with no job is the more dangerous half —
    it is what would have this ticket require a context nothing produces.
    """
    assert set(adr_table()) == CONTEXTS


def test_the_ruleset_requires_exactly_the_jobs_the_workflow_runs() -> None:
    """The equality this ticket is for, against the live `main` ruleset.

    **Read from GitHub rather than from a committed copy.** A copy would let a
    rename be made consistent across three files while the ruleset kept pointing
    at a context that no longer arrives, which is precisely the failure the
    rename is dangerous for.

    Both directions, in one assertion, because they fail differently and the
    difference is the diagnosis: a job missing from the ruleset is a seam nothing
    gates; a context missing from the workflow is a branch nothing can merge into.
    """
    assert required_contexts(branch_rules()) == CONTEXTS


def test_force_pushes_to_the_protected_branch_are_blocked() -> None:
    """The gap `Published documents are immutable` cannot close from inside.

    With no comparable base commit that job warns and passes, having checked
    nothing. A pull request always carries a base and an ordinary push always
    carries a real predecessor, so the only reachable path to that green tick is
    a force push to `main` — which this rule refuses, in the same ruleset that
    requires the contexts above.
    """
    assert force_pushes_blocked(branch_rules())


# ─── Map constraint `#13`: a required context arrives unconditionally ─────────


def test_no_job_carries_a_conditional_that_could_withhold_its_context() -> None:
    """No job-level `if:`, no matrix — on any job, because every job is required.

    Each produces a context that never reports, and the pull request then sits
    pending rather than failing. The failure is silent by construction, which is
    why it is asserted rather than reviewed.

    Step-level conditionals are untouched and deliberately so: `if: failure()` on
    a step that dumps container logs sits inside a job that always runs, so the
    context still arrives. That is the escape hatch `ci.yml`'s header names, and
    three jobs use it today.
    """
    assert {job.id: job.suppressors for job in JOBS if job.suppressors} == {}


def test_the_workflow_filters_no_event_by_path() -> None:
    """The other half of `#13`, which lives on the triggers rather than on a job.

    A `paths:` filter withholds *every* context in the file at once, so it is the
    same defect at workflow scale — and it is the cheapest one to add by accident,
    because it reads as an optimisation.
    """
    assert trigger_filters(SOURCE) == {}


# ─── The demonstrations: each check, shown failing ────────────────────────────


def test_a_renamed_job_is_reported_against_the_ruleset() -> None:
    """The failure this file exists for, run rather than described.

    A rename looks exactly like this — one string changed in `ci.yml`, nothing
    else — and from the outside it is invisible: the pull request that does it
    goes green, because the check that was required stopped reporting instead of
    reporting red. Here the same edit is made in memory and the disagreement is
    named in both directions at once.
    """
    renamed = read_workflow(SOURCE.replace("name: Seed renders clean", "name: Seed rendered clean"))
    required = required_contexts(rules_requiring(*CONTEXTS))

    assert "Seed renders clean" in required - names(renamed)
    assert "Seed rendered clean" in names(renamed) - required


def test_a_context_required_by_the_ruleset_that_no_job_produces_is_reported() -> None:
    """A rule waiting on a check that never arrives, which is the pending state.

    This is the state the ordering rule at the top of #47 forbids creating, and
    the reason the ruleset could not land before the last job did. It is also
    what a deleted job leaves behind.
    """
    required = required_contexts(rules_requiring(*CONTEXTS, "A job nobody wrote"))

    assert required - CONTEXTS == {"A job nobody wrote"}


def test_a_job_the_ruleset_does_not_require_is_reported() -> None:
    """The other direction: a seam that runs, reports, and gates nothing.

    ADR-0008's *"a check that can never block becomes noise"* is the argument, and
    ADR-0013 refuses an exemption list, so a new job is required or the set
    equality is false. There is no third state to be in by accident.
    """
    required = required_contexts(rules_requiring(*(CONTEXTS - {"Server posture"})))

    assert CONTEXTS - required == {"Server posture"}


def test_a_branch_with_no_required_status_checks_at_all_is_reported() -> None:
    """The state every branch here was in until this ticket: rules, but no gate.

    `main` already carried deletion, force-push and pull-request rules while
    requiring no context at all, so the payload is non-empty and the answer is
    still the empty set. A check that read "has rules" would have passed on it.
    """
    unguarded: list[Any] = [{"type": "deletion"}, {"type": "non_fast_forward"}]

    assert required_contexts(unguarded) == frozenset()
    assert force_pushes_blocked(unguarded)


def test_a_job_level_conditional_is_reported() -> None:
    """`if:` on the job, which is the shape that reads as harmless.

    Written against the job that would most plausibly attract one — the flow that
    reaches the network — because the tempting version of this edit is always
    *skip the expensive job unless something changed*.
    """
    conditional = SOURCE.replace(
        "  authorization-code-flow:\n    name: Authorization code flow\n",
        "  authorization-code-flow:\n    name: Authorization code flow\n"
        "    if: github.event_name == 'push'\n",
    )

    assert [job.suppressors for job in read_workflow(conditional) if job.suppressors] == [("if",)]


def test_a_matrix_is_reported() -> None:
    """A matrix leg, which reports one context per leg and none under its own name.

    The job's `name:` stops being a context at all once a matrix exists — GitHub
    reports `Lint and types (3.13)` — so a rule requiring the bare name waits
    forever on a job that ran and passed.
    """
    matrixed = SOURCE.replace(
        "  lint-and-types:\n    name: Lint and types\n",
        "  lint-and-types:\n    name: Lint and types\n"
        "    strategy:\n      matrix:\n        python: ['3.13']\n",
    )

    assert [job.suppressors for job in read_workflow(matrixed) if job.suppressors] == [
        ("strategy",)
    ]


def test_a_step_level_conditional_is_not_reported() -> None:
    """The escape hatch, asserted so that closing it needs an argument.

    Three jobs already carry `if: failure()` on a log-dumping step. A check that
    grepped for the word `if` would report all three, and the first fix for that
    noise would be to delete the steps — which is the wrong outcome from a check
    that is supposed to be about whether a context arrives.
    """
    assert "if: failure()" in SOURCE
    assert [job.suppressors for job in JOBS if job.suppressors] == []


def test_a_path_filter_on_either_trigger_is_reported() -> None:
    """Both spellings, on both events, since one of them is enough to do it.

    `on:` parses as the boolean `True` under YAML 1.1, so this is also what keeps
    the reader honest about the parse: a filter added to the file has to come
    back out of it.
    """
    filtered = SOURCE.replace(
        "on:\n  pull_request:\n    branches: [main]\n",
        "on:\n  pull_request:\n    branches: [main]\n    paths-ignore: ['docs/**']\n",
    )

    assert trigger_filters(filtered) == {"pull_request": ("paths-ignore",)}


def test_the_adr_table_is_read_as_a_list_of_names_and_not_of_diagnoses() -> None:
    """What the table parser takes from the table, and what it ignores.

    The second and third columns are prose written for a reader — *a red check
    means…* — and a check that compared them would fail on a rewording and mean
    nothing when it passed. Demonstrated on a table of the ADR's own shape rather
    than asserted about the parser in a comment.
    """
    table = """
| Job `name:` | A red check means | Compose |
| --- | --- | --- |
| Lint and types | ordinary Python defect | no |
| Server posture | the server exposes something other than what it should | yes |

Prose resumes here.
"""

    assert table_job_names(table) == ("Lint and types", "Server posture")

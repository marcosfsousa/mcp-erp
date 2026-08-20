"""The three places the job set is written down, and the one that is not a file.

ADR-0013's table, `.github/workflows/ci.yml`, and the `main` ruleset all name the
same set of continuous-integration jobs. Two of them are committed and the third
lives in this repository's settings, which is why this module exists: the
assertions beside it are a three-way set equality, and something has to read the
ruleset from the only place it exists.

**Why the live ruleset rather than a committed copy of it.** A checked-in export
would make this check pass while the branch went unprotected — rename a job, edit
the export to match, and three documents agree about a context the ruleset no
longer requires. The failure this whole ticket exists to prevent is exactly that
one, so the fetch is the point rather than a cost. `GET /repos/{repo}/rules/
branches/{branch}` needs no credential on a public repository; the token is sent
when one is in the environment, for rate-limit headroom rather than for access.

**Nothing here interprets a rule it does not name.** The ruleset carries
`deletion`, `pull_request` and `non_fast_forward` rules too, and this module reads
two of them — the required contexts, and whether force pushes are blocked. The
rest are settings this ticket makes no claim about.
"""

from __future__ import annotations

import functools
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml

HERE: Final = Path(__file__).resolve().parent
"""This directory."""

REPO: Final = HERE.parent
"""The checkout, from this file's own location.

`tests/fixtures.py` already derives the same path, and this re-derives it rather
than importing it. The job that runs this file must stand when the suites around
it are cut or fall over — that is the whole argument for it being its own job —
so a two-line resolution is cheaper than a dependency on a module that belongs to
the wire suites.
"""

WORKFLOW: Final = ".github/workflows/ci.yml"
"""The workflow whose job `name:` values a ruleset matches by string."""

ADR: Final = "docs/adr/0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md"
"""The document that enumerates the jobs, one per seam."""

TABLE_HEADER: Final = "| Job `name:` |"
"""How the job table opens in the ADR, and the only way this module finds it.

Matched on the first column's heading rather than on a section title, because the
heading above that table carries a struck-through count and would move again the
next time somebody amends it.
"""

REPOSITORY: Final = "marcosfsousa/mcp-erp"
"""Whose ruleset this is, when the environment does not say.

`GITHUB_REPOSITORY` is set on every runner and names the *base* repository for a
pull request from a fork, which is the ruleset that decides whether the pull
request can merge. This constant is the local fallback.
"""

BRANCH: Final = "main"
"""The branch the ruleset protects, which is the branch this workflow gates."""

API: Final = "https://api.github.com"
"""GitHub's REST host. The one address this check reaches."""

ATTEMPTS: Final = 3
"""Retries on a transport failure, because this job is required and gates merges.

ADR-0013 is explicit that a flaky required job is the one thing that would earn an
exemption the ruleset does not offer. A single dropped connection to the API is
not a disagreement between the ruleset and the workflow, so it is not allowed to
report as one.
"""

REQUIRED_STATUS_CHECKS: Final = "required_status_checks"
"""The rule type carrying the contexts a branch requires. GitHub's own spelling.

It names both the rule and, inside its parameters, the array of checks — the API
repeats the word at two levels, which is worth knowing before reading the reader
below.
"""

NON_FAST_FORWARD: Final = "non_fast_forward"
"""The rule type that refuses a force push. GitHub's own spelling, again.

Both of these are matched against the API's payload rather than against anything
this repository writes, so a rename on GitHub's side would show up here as a rule
that is suddenly absent — which is the honest failure and not a silent pass.
"""

SUPPRESSORS: Final = ("if", "strategy")
"""The job-level keys map constraint `#13` refuses, as they appear in the file.

`strategy` rather than `matrix`: a conditional matrix leg is what the constraint
names, and a matrix is what makes one possible. `paths:` and `paths-ignore:` are
trigger-level and are read separately — they are not job keys at all.
"""

TRIGGER_FILTERS: Final = ("paths", "paths-ignore")
"""The trigger-level keys map constraint `#13` refuses, on either event."""


@dataclass(frozen=True, slots=True)
class Job:
    """One job of the workflow, in the two terms this check is about.

    Attributes:
        id: The key under `jobs:`, which is what a `name:`-less job reports as.
        name: The status-check context this job produces.
        suppressors: The job-level keys it carries that could withhold that
            context — empty on every job here, and asserted to be.
    """

    id: str
    name: str
    suppressors: tuple[str, ...]


def read_workflow(text: str) -> tuple[Job, ...]:
    """Parse a workflow into its jobs, in the order the file declares them.

    A job with no `name:` reports its job id instead, which GitHub treats as the
    context identically. Both are contracts, so both are read the same way here.

    Args:
        text: The workflow's YAML source.

    Returns:
        Every job in the file, in declaration order.
    """
    document: Mapping[str, Any] = yaml.safe_load(text)
    jobs: Mapping[str, Mapping[str, Any]] = document["jobs"]

    return tuple(
        Job(
            id=job_id,
            name=str(job.get("name", job_id)),
            suppressors=tuple(key for key in SUPPRESSORS if key in job),
        )
        for job_id, job in jobs.items()
    )


def source() -> str:
    """The committed workflow's text, which is where every check here starts.

    Text rather than parsed jobs, unlike :func:`adr_table` beside it: half the
    checks edit this file in memory to show what they would report, so a second
    read of the same bytes would be the thing that goes stale.
    """
    return (REPO / WORKFLOW).read_text(encoding="utf-8")


def names(jobs: Iterable[Job]) -> frozenset[str]:
    """The contexts a set of jobs produces."""
    return frozenset(job.name for job in jobs)


def trigger_filters(text: str) -> dict[str, tuple[str, ...]]:
    """Which events filter by path, which map constraint `#13` forbids outright.

    `on:` is the trap in this function. PyYAML reads YAML 1.1, under which the
    bare word `on` is the boolean `True` — so the triggers sit under a key that is
    not the string it looks like in the file. Both spellings are accepted here
    rather than one being assumed, because a quoted `"on":` would parse the other
    way and this check would then silently look at nothing.

    Args:
        text: The workflow's YAML source.

    Returns:
        Each event that carries a path filter, mapped to the filters it carries.
        Empty when the workflow runs on every change, which is what `#13` asks.
    """
    document: Mapping[Any, Any] = yaml.safe_load(text)
    triggers: Mapping[str, Any] = document.get("on", document.get(True, {}))

    found = {
        event: tuple(key for key in TRIGGER_FILTERS if key in (settings or {}))
        for event, settings in triggers.items()
    }

    return {event: filters for event, filters in found.items() if filters}


def fetch_branch_rules() -> list[Any]:
    """The rules that actually apply to `main`, read from GitHub.

    This is the only network call in the suite that is not part of the
    authorization code flow, and it is keyless: the endpoint answers
    unauthenticated on a public repository. `GITHUB_TOKEN` is used when the
    environment has one, which on a runner it always does, so the request is
    counted against the workflow's rate limit rather than against the runner's
    shared address.

    Neither the repository nor the branch is a parameter. There is one ruleset
    this check is about — the one gating the branch this workflow runs against —
    and a parameter would invite a caller to ask about a different one.

    Returns:
        The endpoint's array of active rules, each with its `type`.

    Raises:
        OSError: When the API could not be reached after :data:`ATTEMPTS` tries.
            The message names the API rather than the ruleset, because an
            unreachable endpoint is not a disagreement about required contexts.
    """
    slug = os.environ.get("GITHUB_REPOSITORY") or REPOSITORY
    request = urllib.request.Request(
        f"{API}/repos/{slug}/rules/branches/{BRANCH}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    last: OSError | None = None
    for attempt in range(ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                decoded: list[Any] = json.loads(response.read())
                return decoded
        except urllib.error.HTTPError as failure:
            if failure.code < 500:
                raise
            last = failure
        except OSError as failure:
            last = failure
        time.sleep(2 * (attempt + 1))

    raise OSError(
        f"Could not read {slug}'s branch rules from the GitHub API after "
        f"{ATTEMPTS} attempts: {last}. This says nothing about whether the "
        f"ruleset and the workflow agree."
    )


@functools.cache
def branch_rules() -> tuple[Any, ...]:
    """The live rules, fetched once per run.

    Called from inside the assertions rather than evaluated at import, so that
    collecting this file costs nothing and an unreachable API fails a named test
    instead of the collection of every test beside it.
    """
    return tuple(fetch_branch_rules())


def required_contexts(rules: Sequence[Any]) -> frozenset[str]:
    """The status checks a branch's rules require, by context name.

    A branch with no required-status-checks rule has no required contexts, which
    is a state this returns as the empty set rather than as an error: it is what
    every branch in this repository looked like until this ticket, and the
    assertion that reports it is the one that should speak.

    Args:
        rules: The `rules/branches/{branch}` payload.

    Returns:
        Every required context, across every rule of that type.
    """
    return frozenset(
        str(check["context"])
        for rule in rules
        if rule.get("type") == REQUIRED_STATUS_CHECKS
        for check in rule.get("parameters", {}).get(REQUIRED_STATUS_CHECKS, ())
    )


def force_pushes_blocked(rules: Sequence[Any]) -> bool:
    """Whether the branch refuses a push that is not a fast-forward.

    Args:
        rules: The `rules/branches/{branch}` payload.

    Returns:
        True when a `non_fast_forward` rule applies.
    """
    return any(rule.get("type") == NON_FAST_FORWARD for rule in rules)


def table_job_names(text: str) -> tuple[str, ...]:
    """ADR-0013's job table, read as the list of names it is.

    The table is markdown and its first column is the job `name:`. Everything
    after the first column is prose about what a red check means, which nothing
    here asserts against — a diagnosis is written for a reader and would fail this
    check on a rewording.

    Args:
        text: The ADR's markdown source.

    Returns:
        The first column of every row, in the table's own order.
    """
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(TABLE_HEADER))

    rows: list[str] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(line.split("|")[1].strip())

    return tuple(rows)


def adr_table() -> tuple[str, ...]:
    """The committed ADR's job table."""
    return table_job_names((REPO / ADR).read_text(encoding="utf-8"))

"""The masked diff for every drifted transcript — the comparison :func:`transcripts.keep` made.

The drift check names a file and stops, and the next run rewrites that file, so a
drift that does not reproduce leaves nothing behind to read. #108 paid for that
once: a red check on #106 that a rerun of the same commit turned green, and the
only artifact was a filename.

**It prints what the mask compared, not what `git diff` would.** `git diff` on
that same drift reported 107 changed lines led by `date` and `x-served-by` —
fields :func:`transcripts.mask` covers and the verdict therefore never saw — and
a reader who trusts it concludes a clock moved. Under the mask the same drift is
69 lines, every one substantive, and it names its own cause: the beat count fell
and the consent post is gone.

**Asserts nothing.** The step's `git status --porcelain` is the verdict; this is
the diagnosis printed beside it. So it returns 0 on every entry it can be handed,
including the ones it can say nothing useful about — an untracked capture with no
`HEAD:` copy, one deleted from the working tree, a file under the watched path
that is nobody's capture. What it does not swallow is `git` itself failing, which
is a fact about the runner rather than about the exhibit; the step calls it with
`|| true` so that even then the intended `exit 1` is what the job reports.

That coupling is why this lives in `tests/` rather than in a workflow heredoc: it
imports :func:`transcripts.mask`, so the diff it prints is the comparison that
was actually made rather than a second opinion about it.
"""

from __future__ import annotations

import difflib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import transcripts

UNTRACKED: Final = "??"
"""What `git status --porcelain` reports for a capture with no committed copy.

The case the step's `git status --porcelain` was chosen over `git diff
--exit-code` to catch — a beat that is missing entirely. There is no `HEAD:`
copy to diff against, so this prints the fact rather than raising on it.
"""

RENAMED: Final = " -> "
"""How `git status --porcelain` joins a rename's two paths, source first."""


@dataclass(frozen=True, slots=True)
class Entry:
    """One line of `git status --porcelain`, as the two sides a diff needs.

    A pair of bare strings would have been a pair a type checker cannot tell
    apart, and a rename makes them genuinely different paths rather than one path
    twice — which is the case that turned a two-string pair into a type.

    Attributes:
        code: The two-character status code.
        before: Where the committed side is — a rename's source, and the same
            path as `after` for every other status.
        after: Where the working tree's side is.
    """

    code: str
    before: str
    after: str


def drifted() -> list[Entry]:
    """Every capture `git status` reports as changed.

    Parsed by column rather than split on whitespace: the code is the first two
    characters and the paths are everything from the fourth. A rename reports
    both of them, and asking `HEAD:` for the *new* path would answer nothing and
    report a renamed capture as one with no committed copy at all.

    `--untracked-files=all` because the default collapses an untracked directory
    to one entry ending in `/`. That cannot happen while `docs/transcripts/`
    holds a committed README, which is to say it is a fact about the directory's
    contents rather than about this check — and the missing-capture case is
    precisely the one the step chose `git status` over `git diff` to catch.

    Returns:
        One entry per drifted capture, in the order `git status` reported them.
    """
    reported = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", "docs/transcripts"],
        capture_output=True,
        text=True,
        check=True,
        cwd=transcripts.REPO,
    ).stdout.splitlines()

    entries = []
    for line in reported:
        code, paths = line[:2], line[3:]
        before, _, after = paths.partition(RENAMED)
        entry = Entry(code, before, after or before)
        if entry.after.endswith(transcripts.SUFFIX):
            entries.append(entry)

    return entries


def committed(path: str) -> str | None:
    """What `HEAD` holds at `path`, or `None` when `HEAD` holds nothing there."""
    shown = subprocess.run(
        ["git", "show", f"HEAD:{path}"],
        capture_output=True,
        check=False,
        cwd=transcripts.REPO,
    )
    if shown.returncode != 0:
        return None

    return shown.stdout.decode("utf-8")


def diff(entry: Entry) -> str:
    """One capture's drift, under the mask, as the text to print for it.

    Args:
        entry: What `git status` reported for that capture.

    Returns:
        A unified diff of the two masked forms, or a sentence for a case that has
        no two sides to diff.
    """
    fresh = transcripts.REPO / Path(entry.after)

    if not fresh.exists():
        return f"{entry.after}: the committed capture is gone from the working tree."

    before = None if entry.code == UNTRACKED else committed(entry.before)
    if before is None:
        lines = fresh.read_text(encoding="utf-8").count("\n")
        return f"{entry.after}: no committed copy; this run captured it fresh, {lines} lines."

    delta = "\n".join(
        difflib.unified_diff(
            transcripts.mask(before).split("\n"),
            transcripts.mask(fresh.read_text(encoding="utf-8")).split("\n"),
            fromfile=f"{entry.before} (committed, masked)",
            tofile=f"{entry.after} (this run, masked)",
            lineterm="",
        )
    )

    if not delta:
        # `keep` rewrites only when the masked forms differ, so this pair should
        # not exist. It means something other than a substantive change touched
        # the file — a checkout that converted line endings is the one to look
        # for, which is what `.gitattributes` pins these `-text` against.
        return (
            f"{entry.after}: identical under the mask, so the rewrite was not a substantive change."
        )

    return delta


def main() -> int:
    """Print every drifted capture's masked diff, and return 0 whatever they held."""
    for entry in drifted():
        print(diff(entry))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

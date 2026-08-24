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
the diagnosis printed beside it. It exits 0 on every path, including the ones
where it can say nothing useful, because the workflow runs under
`set -euo pipefail` and a non-zero exit here would mask the intended `exit 1`.

That coupling is why this lives in `tests/` rather than in a workflow heredoc: it
imports :func:`transcripts.mask`, so the diff it prints is the comparison that
was actually made rather than a second opinion about it.
"""

from __future__ import annotations

import difflib
import subprocess
from pathlib import Path
from typing import Final

import transcripts

UNTRACKED: Final = "??"
"""What `git status --porcelain` reports for a capture with no committed copy.

The case the step's `git status --porcelain` was chosen over `git diff
--exit-code` to catch — a beat that is missing entirely. There is no `HEAD:`
copy to diff against, so this prints the fact rather than raising on it.
"""


def drifted() -> list[tuple[str, str]]:
    """Every capture `git status` reports as changed, as `(status code, path)`.

    Parsed by column rather than split on whitespace: the code is the first two
    characters, the path is everything from the fourth, and a rename reports
    `old -> new` of which the fresh copy is the second.

    `--untracked-files=all` because the default collapses an untracked directory
    to one entry ending in `/`. That cannot happen while `docs/transcripts/`
    holds a committed README, which is to say it is a fact about the directory's
    contents rather than about this check — and the missing-capture case is
    precisely the one the step chose `git status` over `git diff` to catch.

    Returns:
        One pair per drifted capture, in the order `git status` reported them.
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
        code, path = line[:2], line[3:].split(" -> ")[-1]
        if path.endswith(transcripts.SUFFIX):
            entries.append((code, path))

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


def diff(path: str, code: str) -> str:
    """One capture's drift, under the mask, as the text to print for it.

    Args:
        path: The capture, repo-relative, as `git status` spelled it.
        code: That entry's two-character `git status --porcelain` code.

    Returns:
        A unified diff of the two masked forms, or a sentence for a case that has
        no two sides to diff.
    """
    fresh = transcripts.REPO / Path(path)

    if not fresh.exists():
        return f"{path}: the committed capture is gone from the working tree."

    before = None if code == UNTRACKED else committed(path)
    if before is None:
        lines = fresh.read_text(encoding="utf-8").count("\n")
        return f"{path}: no committed copy; this run captured it fresh, {lines} lines."

    delta = "\n".join(
        difflib.unified_diff(
            transcripts.mask(before).split("\n"),
            transcripts.mask(fresh.read_text(encoding="utf-8")).split("\n"),
            fromfile=f"{path} (committed, masked)",
            tofile=f"{path} (this run, masked)",
            lineterm="",
        )
    )

    if not delta:
        # `keep` rewrites only when the masked forms differ, so this pair should
        # not exist. It means something other than a substantive change touched
        # the file — a checkout that converted line endings is the one to look
        # for, which is what `.gitattributes` pins these `-text` against.
        return f"{path}: identical under the mask, so the rewrite was not a substantive change."

    return delta


def main() -> int:
    """Print every drifted capture's masked diff. Always succeeds."""
    for code, path in drifted():
        print(diff(path, code))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

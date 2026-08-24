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

**Which means it never reads a failure as an answer.** `git show` exits 128 for
a path `HEAD` does not hold *and* for one it holds and cannot read, and — this
is the part that is not guessable — it prints the *same sentence* for both when
the path is on disk, which every drifted capture is. So neither the exit status
nor the message distinguishes them, and a helper that concludes "no committed
copy" from either reports a corrupt repository as a capture that was never
committed: the loudest claim available, made about a committed file, inside the
helper that exists to stop exactly that. :func:`committed` therefore asks `git
ls-tree`, whose exit status answers the question `git show` cannot, and raises
:exc:`GitFailed` when `git` does not answer at all. :func:`main` prints that
against the capture it concerns and exits non-zero, so one unreadable object
costs the diagnosis for that capture and not for the others.

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


class GitFailed(RuntimeError):
    """`git` did not answer, so nothing was learned about what `HEAD` holds.

    Distinct from `None`, which is `git` answering that `HEAD` holds nothing
    there. Collapsing the two is the defect this type exists to make
    unrepresentable: a caller cannot reach the "no committed copy" sentence
    without having been told that by `git`.
    """


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


def asked(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    """One `git` invocation against the repository, its failure left to the caller."""
    return subprocess.run(
        ["git", *arguments],
        capture_output=True,
        check=False,
        cwd=transcripts.REPO,
    )


def failure(argv: str, answer: subprocess.CompletedProcess[bytes]) -> GitFailed:
    """A `GitFailed` carrying what `git` was asked, what it exited, and what it said."""
    said = answer.stderr.decode("utf-8", errors="replace").rstrip()

    return GitFailed(
        f"`git {argv}` exited {answer.returncode}, so nothing is known about whether "
        f"this capture is committed:\n{said}"
    )


def committed(path: str) -> str | None:
    """What `HEAD` holds at `path`, or `None` when `HEAD` holds nothing there.

    Two invocations rather than one, because `git show` cannot answer this
    question and `git ls-tree` can. Asked for a path it fails to resolve, `git
    show` says *exists on disk, but not in `HEAD`* whenever the working tree has
    that path — and it says the identical sentence when `HEAD` genuinely lacks
    it and when a tree object it needs is unreadable. Measured, on `git
    cat-file -e` and `git show` alike: delete the tree object under a committed
    capture and the message is byte-for-byte the one a never-committed capture
    produces. So no reading of `git show`'s stderr can tell those apart, and the
    first draft of this fix, which tried, reported a corrupt repository as a
    capture that was never committed — the bug it was written to remove.

    `git ls-tree` separates all three: a path `HEAD` holds is exit 0 and a line,
    a path it does not hold is exit 0 and no output, and a failure to read what
    it needs is a non-zero exit. Its output is only tested for emptiness, never
    parsed, so `core.quotePath` and C-style quoting of a non-ASCII path change
    nothing here — and no message text is read, so a translated `git` is not a
    consideration either.

    Args:
        path: The committed side's path, relative to the repository root.

    Returns:
        The committed bytes as text, or `None` when `git` answered that `HEAD`
        does not hold that path.

    Raises:
        GitFailed: When `git` did not answer, carrying the invocation, its exit
            status and its stderr. Never `None`, because a `git` that cannot
            read `HEAD` has said nothing about whether the capture is committed.
    """
    listed = asked("ls-tree", "--name-only", "HEAD", "--", path)
    if listed.returncode != 0:
        raise failure(f"ls-tree --name-only HEAD -- {path}", listed)

    if not listed.stdout.strip():
        return None

    shown = asked("show", f"HEAD:{path}")
    if shown.returncode != 0:
        # `ls-tree` just said `HEAD` holds this path, so a `git show` that
        # cannot produce it is a `git` failure with no second reading.
        raise failure(f"show HEAD:{path}", shown)

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
    """Print every drifted capture's masked diff, and say whether `git` answered for all.

    A `GitFailed` is printed against the capture it was raised for and the loop
    goes on, because letting it out here would discard every later capture's
    diff — measured at three drifted captures with only the first unreadable,
    where the diagnosis for the other two is exactly what the reader still needs
    and is still correct.

    Returns:
        0 when every entry was diagnosed, and 1 when `git` failed on any of
        them. Non-zero rather than swallowed, so the failure is a fact about the
        run and not only a line in its output; the step calls this with
        `|| true`, so the `exit 1` the job reports remains the drift check's.
    """
    answered = True

    for entry in drifted():
        try:
            print(diff(entry))
        except GitFailed as failed:
            answered = False
            print(f"{entry.after}: {failed}")

    return 0 if answered else 1


if __name__ == "__main__":
    raise SystemExit(main())

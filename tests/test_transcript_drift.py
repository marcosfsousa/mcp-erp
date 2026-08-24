"""The masked diff the drift check prints, and its agreement with the verdict beside it.

`tests/transcript_drift.py` is a **second** consumer of the comparison
:func:`transcripts.keep` makes. Two readings of one comparison that can disagree
are worse than one reading that is merely terse: a diagnosis printed under the
wrong rules is read as fact, and #108 exists because a reader spent an
investigation on a filename. So what is asserted here is the agreement — a drift
`keep` acts on is a drift the helper prints, and one `keep` ignores prints
nothing.

**A real repository, not a mocked one.** The helper's whole job is to read what
`git status` reported and ask `git` for the committed side, so a test that stood
in for `git` would assert against this file's idea of porcelain output rather
than against `git`'s. Each test builds a throwaway repository in `tmp_path` and
points the module's `REPO` and `COMMITTED` at it.

**No Compose.** `git` and text, so this runs in `Lint and types` beside
`tests/test_transcripts.py`, for the reason that suite gives: a helper that
printed the wrong diff is an ordinary Python defect, and the job that captures
against a running stack cannot see it — the helper only runs when that job is
already red.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import transcript_drift
import transcripts
from test_transcripts import A_CAPTURE

BEAT = "a-beat"
"""The one capture these repositories hold, named like a beat and standing for any."""


def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, committed: str | None) -> Path:
    """A throwaway checkout holding `docs/transcripts/`, with the module pointed at it.

    Args:
        tmp_path: pytest's directory for this test.
        monkeypatch: Used to repoint :data:`transcripts.REPO` and
            :data:`transcripts.COMMITTED`, which both the helper and
            :func:`transcripts.keep` read at call time.
        committed: The capture to commit, or `None` for a repository whose first
            commit holds no capture at all.

    Returns:
        The checkout's root.
    """
    captures = tmp_path / "docs" / "transcripts"
    captures.mkdir(parents=True)

    monkeypatch.setattr(transcripts, "REPO", tmp_path)
    monkeypatch.setattr(transcripts, "COMMITTED", captures)

    def git(*arguments: str) -> None:
        subprocess.run(["git", *arguments], cwd=tmp_path, check=True, capture_output=True)

    git("init", "--initial-branch", "main")
    git("config", "user.email", "capture@example.invalid")
    git("config", "user.name", "The capture")
    # The pin `.gitattributes` carries in the real checkout: these bytes are
    # compared, and a checkout that converted line endings would drift a file
    # nobody edited.
    (tmp_path / ".gitattributes").write_text("docs/transcripts/** -text\n", encoding="utf-8")

    if committed is not None:
        (captures / f"{BEAT}{transcripts.SUFFIX}").write_bytes(committed.encode("utf-8"))

    git("add", "-A")
    git("commit", "-m", "The captured beats")

    return tmp_path


def printed(capsys: pytest.CaptureFixture[str]) -> str:
    """What the helper wrote to stdout, having asserted it succeeded.

    The workflow runs under `set -euo pipefail`, so a non-zero exit here would
    mask the `exit 1` the drift check means to give.
    """
    assert transcript_drift.main() == 0

    return capsys.readouterr().out


def test_a_drift_keep_acted_on_is_a_drift_the_helper_prints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The agreement, in the direction that matters: red check, and the cause named."""
    repository(tmp_path, monkeypatch, A_CAPTURE)
    fresh = A_CAPTURE.replace('"sub": "priya-raman"', '"sub": "tomas-weber"')

    assert transcripts.keep(BEAT, fresh) is True

    out = printed(capsys)

    assert '-  "sub": "priya-raman"' in out
    assert '+  "sub": "tomas-weber"' in out


def test_the_volatile_fields_the_verdict_never_saw_stay_out_of_the_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`git diff` would lead with the clock, and a reader who trusts it concludes wrongly.

    #108's own case: 107 changed lines led by `date` and `x-served-by`, against
    69 under the mask of which every one was substantive. This asserts the
    difference rather than describing it — the drift here moves the clock *and*
    the subject, and only one of them may be printed.
    """
    repository(tmp_path, monkeypatch, A_CAPTURE)
    fresh = A_CAPTURE.replace('"sub": "priya-raman"', '"sub": "tomas-weber"').replace(
        "21:34:54", "22:11:07"
    )

    assert transcripts.keep(BEAT, fresh) is True

    out = printed(capsys)

    assert "tomas-weber" in out
    assert "21:34:54" not in out
    assert "22:11:07" not in out


def test_a_change_keep_ignored_prints_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The other direction of the agreement, and the one a noisy helper would break.

    `keep` leaves the file alone, so `git status` is silent and there is nothing
    to diagnose. A helper that read the working tree instead of the report would
    print a clock moving under a green check.
    """
    repository(tmp_path, monkeypatch, A_CAPTURE)

    assert transcripts.keep(BEAT, A_CAPTURE.replace("21:34:54", "22:11:07")) is False
    assert printed(capsys) == ""


def test_a_capture_with_no_committed_copy_is_reported_rather_than_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The case `git status --porcelain` was chosen over `git diff --exit-code` to catch.

    An untracked capture has no `HEAD:` copy, so the obvious `git show` raises —
    on the one input the verdict exists for. The helper runs *inside* a step that
    is already failing, and a stack trace there replaces the diagnosis with a
    second bug to read.
    """
    repository(tmp_path, monkeypatch, None)

    assert transcripts.keep(BEAT, A_CAPTURE) is True

    out = printed(capsys)

    assert f"{BEAT}{transcripts.SUFFIX}" in out
    assert "no committed copy" in out


def test_a_capture_deleted_from_the_working_tree_is_reported_rather_than_raising(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The mirror case: `git status` reports a path that is no longer on disk."""
    repository(tmp_path, monkeypatch, A_CAPTURE)
    (transcripts.COMMITTED / f"{BEAT}{transcripts.SUFFIX}").unlink()

    out = printed(capsys)

    assert "gone from the working tree" in out


def test_a_file_that_is_not_a_capture_is_left_to_the_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`docs/transcripts/README.md` is under the watched path and is nobody's capture.

    The step's `git status` is red for it, correctly — an edited README under
    that path is a change to committed bytes. The mask has nothing to say about
    it, so the helper does not pretend to.
    """
    repository(tmp_path, monkeypatch, A_CAPTURE)
    (transcripts.COMMITTED / "README.md").write_text("What the mask covers.\n", encoding="utf-8")

    assert printed(capsys) == ""

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
    # The two lines the real `.gitattributes` carries for these files, in the
    # order it carries them — later lines win for the same attribute, so the
    # `-text` that exempts the captures has to sit below the repository-wide
    # normalisation. Copied because the captures are compared byte for byte, and
    # a repository whose line endings behaved differently from the real one would
    # make this suite agree with a mask it is not testing.
    (tmp_path / ".gitattributes").write_bytes(b"* text=auto eol=lf\ndocs/transcripts/*.txt -text\n")

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


def test_a_staged_capture_asks_git_for_a_copy_head_does_not_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The same sentence, reached the other way — through `git` rather than around it.

    An untracked capture is reported from its status code, so the lookup is
    never called. Staging one is what makes `git status` report something other
    than `??` for a path `HEAD` has never held, and therefore the only route by
    which "no committed copy" is `git`'s answer rather than the porcelain's.
    """
    repository(tmp_path, monkeypatch, None)

    assert transcripts.keep(BEAT, A_CAPTURE) is True

    subprocess.run(
        ["git", "add", f"{BEAT}{transcripts.SUFFIX}"],
        cwd=transcripts.COMMITTED,
        check=True,
        capture_output=True,
    )

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


def test_a_renamed_capture_is_diffed_against_the_path_it_came_from(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`git status` reports a rename's two paths, and only the first has a committed copy.

    Asking `HEAD:` for the new one answers nothing, so a renamed capture reads as
    a capture that was never committed — the loudest thing this helper can say,
    said about the wrong file. A rename needs the index, so the capture writers
    cannot produce one; a person running the helper over staged work can.
    """
    repository(tmp_path, monkeypatch, A_CAPTURE)
    renamed = f"the-beat-renamed{transcripts.SUFFIX}"
    subprocess.run(
        ["git", "mv", f"{BEAT}{transcripts.SUFFIX}", renamed],
        cwd=transcripts.COMMITTED,
        check=True,
        capture_output=True,
    )
    (transcripts.COMMITTED / renamed).write_text(
        A_CAPTURE.replace('"sub": "priya-raman"', '"sub": "tomas-weber"'), encoding="utf-8"
    )

    out = printed(capsys)

    assert "no committed copy" not in out
    assert f"{BEAT}{transcripts.SUFFIX} (committed, masked)" in out
    assert f"{renamed} (this run, masked)" in out
    assert '-  "sub": "priya-raman"' in out


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


def test_a_git_that_failed_for_another_reason_is_not_read_as_an_absent_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The mis-diagnosis this helper exists to prevent, made by the helper itself.

    Every `git show` failure exits 128 — a path HEAD does not hold and an object
    HEAD does hold but cannot read are the same number — so reading the exit
    status alone turns a broken repository into the loudest claim available about
    a capture that *is* committed.

    Corrupting the committed blob is the cheapest failure that leaves `git
    status` answering, which is what keeps the entry reaching :func:`committed`
    at all.
    """
    repository(tmp_path, monkeypatch, A_CAPTURE)
    fresh = A_CAPTURE.replace('"sub": "priya-raman"', '"sub": "tomas-weber"')

    assert transcripts.keep(BEAT, fresh) is True

    path = f"docs/transcripts/{BEAT}{transcripts.SUFFIX}"
    blob = tmp_path / ".git" / "objects"
    sha = subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    loose = blob / sha[:2] / sha[2:]
    # Loose objects are written read-only, which on Windows is enforced.
    loose.chmod(0o600)
    loose.write_bytes(b"not an object")

    said = subprocess.run(
        ["git", "show", f"HEAD:{path}"], cwd=tmp_path, capture_output=True, text=True
    )
    assert said.returncode != 0

    with pytest.raises(transcript_drift.GitFailed) as failure:
        transcript_drift.main()

    # Asserted against what `git` said on this runner rather than against a
    # quoted message, because the wording is `git`'s to change between versions
    # and the claim here is that it is passed through.
    assert str(said.returncode) in str(failure.value)
    assert said.stderr.strip().splitlines()[-1] in str(failure.value)
    assert "no committed copy" not in capsys.readouterr().out

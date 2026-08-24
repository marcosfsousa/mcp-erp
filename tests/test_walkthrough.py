"""The write-up's quotations, checked against the captures they name.

`tests/transcript_drift.py` guards the transcript **files** against a run
rewriting them. Nothing guarded a quote **inside** a prose document, and
Markdown has no transclusion — so ADR-0014's *"included from the captured set,
never retyped"* had a rule and no mechanism, and #93 is where the rule stops
being an instruction to whoever is typing.

**Two assertions, and the second is the one that matters.** Every excerpt has to
appear verbatim in the transcript it names, which catches a paste that was later
tidied. And every fenced block has to carry a marker, which catches the failure
the first cannot see: a block nobody labelled, typed from memory, sitting in the
narrative looking exactly like a quotation. #80's eleven drifted claims are the
evidence that a document's prose decays where nothing reads it.

**No Compose.** Every assertion here is a pure function of committed text, so it
runs beside `tests/test_transcripts.py` in the same Docker-free job.

The fixtures below are written out rather than read from `docs/`, on the reason
`tests/test_transcripts.py` gives for its own: a checker fed only real documents
is a checker asserting that the documents agree with themselves.
"""

from __future__ import annotations

import pytest

import transcripts

A_CAPTURE = """A beat

1 of 1
──────────────────────────────────────────────────────────────────────────────

HTTP/1.1 200 OK
content-type: application/json

{
  "jsonrpc": "2.0",
  "id": 2
}
"""
"""A transcript, shaped like a committed one and short enough to quote from."""


def _document(marker: str | None, body: str) -> str:
    """A page of prose with one fenced block on it, marked or not."""
    lines = ["# A beat", "", "Some connective prose, which is hand-written and free.", ""]

    if marker is not None:
        lines.append(f"<!-- excerpt: {marker} -->")

    lines.extend(["```", body, "```", "", "More prose."])

    return "\n".join(lines) + "\n"


# ─── The parser ───────────────────────────────────────────────────────────────


def test_a_marked_block_is_read_with_its_beat() -> None:
    """The marker above the fence names the capture, and the body excludes both fences."""
    (quotation,) = transcripts.quotations(_document(transcripts.FLOW_COMPLETES, "content-type: x"))

    assert quotation.beat == transcripts.FLOW_COMPLETES
    assert quotation.body == ("content-type: x",)


def test_an_unmarked_block_is_read_with_no_beat() -> None:
    """The absence is reported rather than skipped — a skipped block is an uncheckable one."""
    (quotation,) = transcripts.quotations(_document(None, "content-type: x"))

    assert quotation.beat is None


def test_a_block_names_the_line_its_fence_opened_on() -> None:
    """A failure has to say where, or the reader greps a document for a line of JSON."""
    (quotation,) = transcripts.quotations(_document(transcripts.FLOW_COMPLETES, "x"))

    assert quotation.line == 6


def test_a_marker_a_blank_line_above_still_counts() -> None:
    """Markdown tolerates the blank line and so does this; the nearest non-blank line is read."""
    document = "# A beat\n\n<!-- excerpt: the-flow-completes -->\n\n```\nx\n```\n"

    (quotation,) = transcripts.quotations(document)

    assert quotation.beat == transcripts.FLOW_COMPLETES


def test_a_marker_with_prose_after_it_is_not_a_marker() -> None:
    """The whole line, or nothing.

    A marker trailed by a sentence is a comment about a block rather than a
    claim over it, and reading it as a claim would let a fence inherit one.
    """
    document = "# A beat\n\n<!-- excerpt: the-flow-completes --> and then some\n```\nx\n```\n"

    (quotation,) = transcripts.quotations(document)

    assert quotation.beat is None


def test_a_marker_two_blocks_up_is_not_inherited() -> None:
    """The block below a marked block is unmarked, however the paragraphs fell out."""
    document = "<!-- excerpt: the-flow-completes -->\n```\nx\n```\n\nProse.\n\n```\ny\n```\n"

    first, second = transcripts.quotations(document)

    assert (first.beat, second.beat) == (transcripts.FLOW_COMPLETES, None)


def test_an_info_string_on_the_fence_does_not_hide_the_block() -> None:
    """```json is still a fence, and a checker that missed it would miss every pretty one."""
    document = "<!-- excerpt: the-flow-completes -->\n```json\n{}\n```\n"

    (quotation,) = transcripts.quotations(document)

    assert quotation.body == ("{}",)


def test_a_document_with_no_blocks_yields_none() -> None:
    """The write-up starts here, and an outline is a legitimate state for it to be in."""
    assert transcripts.quotations("# A beat\n\nProse only.\n") == ()


# ─── The comparison ───────────────────────────────────────────────────────────


def test_a_verbatim_run_is_found() -> None:
    """Several lines, contiguous, exactly as the capture holds them."""
    quotation = transcripts.Quotation(
        beat=transcripts.FLOW_COMPLETES,
        body=("HTTP/1.1 200 OK", "content-type: application/json"),
        line=1,
    )

    assert not transcripts.misquoted(quotation, A_CAPTURE)


def test_one_altered_character_fails() -> None:
    """The failure the rule was written against: a paste, then a tidy."""
    quotation = transcripts.Quotation(
        beat=transcripts.FLOW_COMPLETES, body=("HTTP/1.1 201 OK",), line=1
    )

    assert transcripts.misquoted(quotation, A_CAPTURE)


def test_trailing_whitespace_is_not_a_difference() -> None:
    """Editors strip it from Markdown and the capture does not, so it says nothing."""
    quotation = transcripts.Quotation(
        beat=transcripts.FLOW_COMPLETES, body=("HTTP/1.1 200 OK   ",), line=1
    )

    assert not transcripts.misquoted(quotation, A_CAPTURE)


def test_leading_whitespace_is_a_difference() -> None:
    """Indentation is structure in a JSON body, and re-indenting a quote rewrites it."""
    quotation = transcripts.Quotation(beat=transcripts.FLOW_COMPLETES, body=('  "id": 2',), line=1)

    assert not transcripts.misquoted(quotation, A_CAPTURE)

    reindented = transcripts.Quotation(
        beat=transcripts.FLOW_COMPLETES, body=('    "id": 2',), line=1
    )

    assert transcripts.misquoted(reindented, A_CAPTURE)


def test_an_elided_middle_fails() -> None:
    """Two lines that are both in the capture, and not next to each other in it."""
    quotation = transcripts.Quotation(
        beat=transcripts.FLOW_COMPLETES,
        body=("HTTP/1.1 200 OK", '  "id": 2'),
        line=1,
    )

    assert transcripts.misquoted(quotation, A_CAPTURE)


def test_an_empty_block_fails() -> None:
    """It matches every transcript at every offset, which is a check that has stopped checking."""
    quotation = transcripts.Quotation(beat=transcripts.FLOW_COMPLETES, body=(), line=1)

    assert transcripts.misquoted(quotation, A_CAPTURE)


# ─── The committed write-up ───────────────────────────────────────────────────


def test_the_write_up_exists() -> None:
    """Asserted rather than skipped around.

    A checker whose target is optional goes green on a repository that lost the
    document, which is the one failure it cannot afford — #93 deletes
    `docs/write-up-notes.md` on the strength of this file existing.
    """
    assert transcripts.WALKTHROUGH.is_file()


def test_every_fenced_block_in_the_write_up_is_marked() -> None:
    """No block gets to be uncheckable by not saying what it is."""
    document = transcripts.WALKTHROUGH.read_text(encoding="utf-8")

    unmarked = [block.line for block in transcripts.quotations(document) if block.beat is None]

    assert not unmarked, (
        f"docs/walkthrough.md has fenced blocks with no <!-- excerpt: … --> above them, "
        f"at lines {unmarked}. Name the beat it came from, or mark it "
        f"`{transcripts.HAND_WRITTEN}`."
    )


def test_every_marker_names_a_beat_or_declares_itself_hand_written() -> None:
    """A misspelt beat is a marker pointing at nothing, which reads as checked and is not."""
    document = transcripts.WALKTHROUGH.read_text(encoding="utf-8")
    allowed = {*transcripts.BEATS, transcripts.HAND_WRITTEN}

    unknown = {
        block.beat
        for block in transcripts.quotations(document)
        if block.beat is not None and block.beat not in allowed
    }

    assert not unknown, f"docs/walkthrough.md names {sorted(unknown)}, which are not beats"


@pytest.mark.parametrize("beat", transcripts.BEATS)
def test_every_excerpt_appears_verbatim_in_the_transcript_it_names(beat: str) -> None:
    """One case per beat, so a red check names the capture rather than the document."""
    document = transcripts.WALKTHROUGH.read_text(encoding="utf-8")
    committed = (transcripts.COMMITTED / f"{beat}{transcripts.SUFFIX}").read_text(encoding="utf-8")

    retyped = [
        block.line
        for block in transcripts.quotations(document)
        if block.beat == beat and transcripts.misquoted(block, committed)
    ]

    assert not retyped, (
        f"docs/walkthrough.md quotes {beat}{transcripts.SUFFIX} at lines {retyped}, "
        f"and the lines it quotes are not in it. Re-copy from the committed capture; "
        f"the connective prose is free, the block is not."
    )

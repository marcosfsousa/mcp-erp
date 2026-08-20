"""The attack suite, rendered for the write-up.

`docs/attack-suite/scenarios.yaml` has always said that *"the write-up's table
renders from it"*, and ADR-0014 §*What a machine can keep true, a machine keeps
true* is the decision that built the renderer. **The rendering is committed and
`Seed renders clean` refuses a diff**, like every other rendering here.

It reads the table through `scenarios.py`, which is the only thing that parses
that file — the same module the invariants beside it read, so a renderer and a
check cannot come to disagree about what a row says.

**Every count is counted from the rows.** `meta` is the standing index a reader
walks and `test_the_suite_holds_together.py` is what holds it to the rows; a
rendering that copied it would publish a number nothing had checked.

**The citation is walked, not destructured.** Its shape varies by basis and by
what was harvestable — nineteen rows quote a clause, fifteen name a decision,
seven quotes are elided and one is corrected — so this walks the mapping in a
fixed order and renders anything it does not know under its own key name. A
renderer built from named fields would drop the next key silently, which on a
table whose whole value is that its citations are real is the worst way to fail.

**`history` renders apart from `note`, and that is the point of the field.** A
note recording a withdrawn claim still contains the claim's words, and a cell
carrying them can be skimmed as an assertion — which is what #12 found on
`row_probe_indistinguishable` and left for whoever built this.

**No prose.** ADR-0014 keeps the connective narrative hand-written and free.

Run it from a checkout to re-render::

    uv run python tests/attack_suite/scenario_table.py
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from scenarios import SCENARIOS, Scenario, Suite, suite

REPO: Final = Path(__file__).resolve().parents[2]
"""The checkout, from this file's own location."""

RENDERING: Final = "docs/attack-suite/scenarios.md"
"""Where the rendered table is committed, beside the source it renders."""

CITATION_ORDER: Final = (
    "source",
    "url",
    "quote",
    "quote_elided",
    "quote_corrected",
    "retrieved",
    "context",
    "also",
    "note",
)
"""The keys a citation may carry, in the order they read best.

Anything a row carries that is not here is rendered after them under its own
name, so a key added to the table appears in the write-up on the same commit
rather than on the one that remembers to come back here.
"""

QUOTED: Final = frozenset({"quote", "quote_elided", "quote_corrected", "context"})
"""Citation keys whose value is somebody else's sentence, and so a blockquote."""

LABELS: Final = {
    "source": "Decided by",
    "url": "Clause",
    "retrieved": "Retrieved",
    "context": "Context, and not the basis",
    "also": "Also",
    "note": "On the citation",
    "quote_elided": "Quoted with an elision",
    "quote_corrected": "Quoted with a correction",
}
"""How each citation key reads in a document. `quote` needs none — it is the sentence."""


def render(rows: Suite) -> str:
    """The whole document: a title, its provenance, the derived index, and the rows."""
    lines = [
        "# The attack suite",
        "",
        f"<!-- Rendered from {SCENARIOS} by tests/attack_suite/scenario_table.py. Do not edit. -->",
        "<!-- `Seed renders clean` re-renders this file and refuses a diff. -->",
        "",
        f"{len(rows.rows)} named scenarios: what each one stops, the clause or decision "
        f"behind it, and the exact deletion that would let it through.",
        "",
    ]

    lines.extend(_index(rows))
    lines.extend(_table(rows))

    lines.append("## Each scenario, with its citation and its removal")
    lines.append("")
    for row in rows.rows:
        lines.extend(_scenario(row))

    return "\n".join(lines).rstrip("\n") + "\n"


def _index(rows: Suite) -> list[str]:
    """The standing index, counted from the rows rather than copied from `meta`."""
    bases = Counter(row.basis for row in rows.rows)
    strengths = Counter(
        row.normative_strength for row in rows.rows if row.normative_strength is not None
    )

    lines = ["## What the rows are", "", "| | Rows |", "| --- | --- |"]
    lines.extend(f"| basis `{basis}` | {count} |" for basis, count in sorted(bases.items()))
    lines.extend(f"| strength `{name}` | {count} |" for name, count in sorted(strengths.items()))
    lines.append(f"| **asserted** | {len(rows.asserted)} |")
    lines.append(f"| **documented** | {len(rows.documented)} |")
    lines.append(f"| may never be downgraded | {sum(1 for row in rows.rows if row.floor)} |")
    lines.append("")

    return lines


def _table(rows: Suite) -> list[str]:
    """The index a reader scans: one line per scenario, and what it stops."""
    lines = [
        "## The scenarios",
        "",
        "| Scenario | Basis | Strength | Status | Prevents |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| [`{row.name}`](#{row.name}) | {row.basis} "
        f"| {_strength(row)} | {row.status} | {row.prevents} |"
        for row in rows.rows
    )
    lines.append("")

    return lines


def _scenario(row: Scenario) -> list[str]:
    """One scenario in full: what it stops, what it cites, and what would let it through."""
    lines = [f"### `{row.name}`", "", row.prevents, ""]

    lines.append(
        f"**Basis** {row.basis} · **Strength** {_strength(row)} · "
        f"**Status** {row.status} · "
        f"**Floor** {'may never be downgraded' if row.floor else 'may be downgraded'}"
    )
    lines.append("")

    lines.extend(_citation(row))

    if row.removal is not None:
        lines.append(f"**Removal that makes the attack succeed** {row.removal}")
        lines.append("")
    if row.note is not None:
        lines.append(f"**Note** {row.note}")
        lines.append("")
    if row.history is not None:
        lines.append(f"**How this row was narrowed** {row.history}")
        lines.append("")

    return lines


def _citation(row: Scenario) -> list[str]:
    """The citation block, key by key, in :data:`CITATION_ORDER` and then whatever is left."""
    lines: list[str] = []

    for key in _keys(row.citation):
        value = row.citation[key]
        if key in QUOTED:
            if key != "quote":
                lines.append(f"*{LABELS[key]}:*")
            lines.extend([f"> {value}", ""])
            continue

        lines.append(f"**{LABELS.get(key, key)}** {_link(key, value)}")
        lines.append("")

    return lines


def _keys(citation: Iterable[str]) -> list[str]:
    """The citation's keys, known ones in order and unknown ones after, sorted."""
    carried = list(citation)

    return [key for key in CITATION_ORDER if key in carried] + sorted(
        key for key in carried if key not in CITATION_ORDER
    )


def _link(key: str, value: str) -> str:
    """A URL as a link, and everything else as itself."""
    return f"<{value}>" if key == "url" else value


def _strength(row: Scenario) -> str:
    """The normative keyword the quoted sentence carries, or that there is none.

    Rendered as *none* rather than as an empty cell, because the two bases that
    carry no strength carry none **by rule** — `scenarios.yaml`: *"every `adr`
    and `seam` row carries null"* — and a blank reads as a value somebody forgot.
    """
    return f"`{row.normative_strength}`" if row.normative_strength is not None else "*none*"


def main() -> int:
    """Re-render the table from the committed scenario list."""
    rendering = REPO / RENDERING

    rendering.parent.mkdir(parents=True, exist_ok=True)
    rendering.write_bytes(render(suite()).encode("utf-8"))
    print(f"rendered {RENDERING}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

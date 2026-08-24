<!--
  THIS IS AN OUTLINE. The prose is not written yet.

  #93 decided the order: build the check before the prose, not after. The check
  is `tests/test_walkthrough.py`, it is live from the commit that added it, and
  it needs this file to exist — so this file exists, holding the five beats
  ADR-0014 fixed and nothing else.

  Two rules govern what goes below, and they pull in opposite directions on
  purpose.

  **The connective prose is hand-written and free.** ADR-0014 §What a machine
  can keep true, a machine keeps true: putting narrative inside a generator is
  how a write-up stops being written. Nothing checks a sentence here.

  **Every fenced block says where it came from.** One marker on its own line,
  immediately above the opening fence:

      <!-- excerpt: scope-without-role -->

  naming a beat in `tests/transcripts.py`'s BEATS, and the block below it has to
  appear verbatim and contiguously in `docs/transcripts/<beat>.txt`. A block
  that is not a quotation is marked `hand-written` instead — a command the
  reader types, a fragment of configuration. There is no third option: an
  unmarked block fails the check, so the escape is always visible in a diff.

  Tables are **linked, never inlined** — `docs/decision-matrix/matrix.md` and
  `docs/attack-suite/scenarios.md` render from their own sources and a copy here
  would be the two-sources-one-fact drift this whole document is careful about.
  Do not restate a number a rendered table holds.

  `docs/write-up-notes.md` is deleted, and map constraint `12` item 4 updated to
  name this file alone, **in the commit that first renders from it** — that is,
  the first commit that puts one of its entries into prose below. Not this one.
-->

# Walkthrough

*Not yet written. See the comment above for what governs it.*

## 1. The flow completes

Hosted identity document dereferenced, a person logs in, a person consents, the
code is redeemed, the token is used on a real call.

## 2. The three denial classes, side by side

Under-scoped, so the tool is absent from `tools/list`. Scope-without-role, so
`-31010` — a protocol error where a `403` would lie. A segregation-of-duties
violation, which is a domain rejection and not an authorization error.

The middle class is **performed, not asserted**: a real consent screen hands
Priya Raman `erp.decide` and the server refuses her anyway.

## 3. `tools/list` differs between two principals

## 4. Row scoping

Yusuf Demir holds everything Tomas Weber holds, in another cost centre, and
CC-4100 rows come back `not_found`.

## 5. The recorded third-party session

## Linked and quoted, not walked

The batch call's several independent outcomes. The deviation paragraph, pointing
at [`normative-register.md`](normative-register.md). Both tables —
[the decision matrix](decision-matrix/matrix.md) and
[the attack suite](attack-suite/scenarios.md).

## Running it yourself: MCP Inspector

The fastest route from *I read this* to *I ran this*. Its **Legacy default** has
to be called out: an untouched Inspector opens the standalone stream the legacy
leg inherits, which reads as this exhibit contradicting its own no-streams claim
unless the reader is warned. Two frictions worth naming — a pinned beta SDK
predating a fix for 401-on-probe handling, and that it is proxy-mediated and
sends no `Origin`.

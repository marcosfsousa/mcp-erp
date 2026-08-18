# Write-up notes

Lines the write-up will want, captured at the moment they were decided rather
than reconstructed from the ADR trail later. This file is map constraint `#12`'s
item 4 — the write-up's declared state until the write-up exists.

**Shape rule.** One line per note, each sourced to the ADR or ticket that
produced it. No prose sections, no drafts, no argument. A note that needs a
paragraph belongs in an ADR; what belongs here is the sentence the write-up
would otherwise have to rediscover.

**Retirement.** When the write-up exists, constraint `#12` item 4 names **the
write-up alone** and this file is deleted in the same commit that first renders
from it. It is a staging artifact, not a permanent second source — keeping both
would recreate exactly the two-sources-one-fact drift that produced the stale
count in note 4 below.

---

- **Unauthenticated endpoints sit outside the token gate structurally, not by a path allow-list.** The metadata route is a sibling of the mounted application rather than an exemption inside it, so there is no allow-list to get wrong. Same preference for impossible-over-defended-against that produced the gate ordering. — ADR-0013 §The gate chain sits in middleware, ADR-0006

- **The empty-principal shortcut fails open, and it is the tempting design.** A directory miss yielding a principal with no roles gets refused at the role step for every tool that requires a role — and `submit_requisition` requires none, so an unknown subject holding `erp.write` would submit a requisition charged to a null cost centre. The fix is a non-optional `partition`, which makes a miss unable to produce a principal at all. Worth telling because the wrong version looks more elegant. — ADR-0013 §The principal directory, #12

- **Layer 1 learns the shape of a refusal, never its grounds.** It reads `denial_class` and outcome cardinality; it never learns which rule fired, against which attribute, on which row. The distinction between shape and grounds is what makes the transport layer portable, and it is the precise form of a title that otherwise reads as rhetoric. — ADR-0013 §Handlers in layer 3, adapters in layer 1

- **The constraint written to stop derived-artifact drift had itself drifted.** Map constraint `#12` enumerates the four derived artifacts and described `scenarios.yaml` as *"9 of its 31 rows carry `basis: adr`"* while the file declared `total: 32`, `adr: 10`. The rule was correct, the mechanism was correct, and the sentence stating the rule was stale — found by walking it rather than by re-reading it. The honest version of "we mechanise this" includes that the mechanism's own description needs the walk too. — #12, A3

- **A committed row read "asserts indistinguishable timing" with nothing measuring timing.** `row_probe_indistinguishable` carried `status: asserted` and a note claiming a timing property that no test could establish over HTTP against Compose. A security property asserted and unproven is the worst-shaped claim an exhibit like this can carry, because its whole value is that its assertions are trustworthy. Caught before any code existed, narrowed to byte-identity, and constant time is now explicitly not claimed. — #12 Answer 1, ADR-0002, ADR-0013

- **A note that records a withdrawn claim still contains the claim's words.** `row_probe_indistinguishable`'s note carries four sentences of negated timing language as the audit trail of its narrowing; `scenarios.yaml` notes render into the write-up's table, so a rendered cell containing the string *"indistinguishable timing"* can be skimmed as an assertion. When the renderer is built, move narrowing history to a `history` key so the `note` carries only what the row asserts. — #12 V1

- **The amendment idiom was invoked more often than it was executed.** The header-plus-marker convention shows seven in-body markers across the trail but only **two** documents — ADR-0005 and ADR-0006 — that ever carried both halves. Three corrections were recorded only in the correcting document and never back-amended into the target, and two documents' headers omitted amendments their own bodies recorded. Brought into line in one commit; the interesting part is that a convention can be cited as established while being followed twice. — #12 sweep 8

# Write-up notes

Raw material for the write-up, captured when it was found rather than
reconstructed from the ADR trail later. This file is map constraint `#12`'s
item 4 — the write-up's declared state until the write-up exists.

**Two kinds of entry, and one question separates them:** did this come from a
*decision*, or from *looking at the trail*? Decisions go in **Notes**, one line
each. Observations about the trail itself go in **Findings**, which need evidence
and therefore need room. Each section states its own shape rule below.

**Retirement.** When the write-up exists, constraint `#12` item 4 names **the
write-up alone** and this file is deleted in the same commit that first renders
from it. It is a staging artifact, not a permanent second source — keeping both
would recreate exactly the two-sources-one-fact drift that produced the stale
count in the fourth note below.

---

## Notes

**Shape rule.** One line per note, sourced to the ADR or ticket that produced it.
No prose sections, no drafts, no argument. A note that needs a paragraph belongs
in an ADR; what belongs here is the sentence the write-up would otherwise have to
rediscover.

- **Unauthenticated endpoints sit outside the token gate structurally, not by a
  path allow-list.** The metadata route is a sibling of the mounted application
  rather than an exemption inside it, so there is no allow-list to get wrong.
  Same preference for impossible-over-defended-against that produced the gate
  ordering. — ADR-0013 §The gate chain sits in middleware, ADR-0006

- **The empty-principal shortcut fails open, and it is the tempting design.** A
  directory miss yielding a principal with no roles gets refused at the role step
  for every tool that requires a role — and `submit_requisition` requires none,
  so an unknown subject holding `erp.write` would submit a requisition charged to
  a null cost centre. The fix is a non-optional `partition`, which makes a miss
  unable to produce a principal at all. Worth telling because the wrong version
  looks more elegant. — ADR-0013 §The principal directory, #12

- **Layer 1 learns the shape of a refusal, never its grounds.** It reads
  `denial_class` and outcome cardinality; it never learns which rule fired,
  against which attribute, on which row. The distinction between shape and
  grounds is what makes the transport layer portable, and it is the precise form
  of a title that otherwise reads as rhetoric.
  — ADR-0013 §Handlers in layer 3, adapters in layer 1

- **The constraint written to stop derived-artifact drift had itself drifted.**
  Map constraint `#12` enumerates the derived artifacts and described
  `scenarios.yaml` as *"9 of its 31 rows carry `basis: adr`"* while the file
  declared `total: 32`, `adr: 10`. The rule was correct, the mechanism was
  correct, and the sentence stating the rule was stale — found by walking it
  rather than by re-reading it. The honest version of "we mechanise this"
  includes that the mechanism's own description needs the walk too. — #12, A3

- **A committed row read "asserts indistinguishable timing" with nothing
  measuring timing.** `row_probe_indistinguishable` carried `status: asserted`
  and a note claiming a timing property that no test could establish over HTTP
  against Compose. A security property asserted and unproven is the worst-shaped
  claim an exhibit like this can carry, because its whole value is that its
  assertions are trustworthy. Caught before any code existed, narrowed to
  byte-identity, and constant time is now explicitly not claimed.
  — #12 Answer 1, ADR-0002, ADR-0013

- **A note that records a withdrawn claim still contains the claim's words.**
  `row_probe_indistinguishable`'s note carries four sentences of negated timing
  language as the audit trail of its narrowing; `scenarios.yaml` notes render
  into the write-up's table, so a rendered cell containing the string
  *"indistinguishable timing"* can be skimmed as an assertion. When the renderer
  is built, move narrowing history to a `history` key so the `note` carries only
  what the row asserts. — #12 V1

- **The amendment idiom was invoked more often than it was executed.** The
  header-plus-marker convention shows seven in-body markers across the trail but
  only **two** documents — ADR-0005 and ADR-0006 — that ever carried both halves.
  Three corrections were recorded only in the correcting document and never
  back-amended into the target, and two documents' headers omitted amendments
  their own bodies recorded. Brought into line in one commit; the interesting
  part is that a convention can be cited as established while being followed
  twice. — #12 sweep 8

- **A convention can be confidently wrong on a surface it names.** The map-number
  backtick rule binds *"every surface GitHub autolinks — issue bodies, pull
  request bodies, and commit messages, subject lines included."* Backticks
  suppress nothing in a commit message, because commit messages are not rendered
  as Markdown; the rule's own establishing commit mislinked the constraint it
  established. Naming a surface is not the same as having checked it.
  — #12, 2026-08-18

- **"No default" and "never absent" are different constraints, and the design
  needs one without the other.** `decide_item`'s resource takes no default, so a
  handler cannot omit it and receive a truncated permit. It is nonetheless
  nullable, because the other half of the same design says an empty join and a
  foreign row must converge on one return site — which only holds if the absent
  row is passed *into* the chain rather than handled by the caller. The two read
  as contradictory and act on different things: one on the argument list, one on
  the type. — #34, ADR-0013

- **The type checker refused to let the type split be tested, which is the
  proof.** `GateOutcome` and `Decision` are structurally identical records, so
  the obvious assertion is that they are not the same class — and mypy rejects
  it as a non-overlapping identity check before the test can run. The property
  was already held statically, so the only honest thing left to assert at
  runtime is that neither inherits from the other. — #34

- **"Hand-authored except the users" is a rule about a file that nothing can
  enforce, until it is two files.** ADR-0007 wanted the realm's clients and
  mappers authored and only its users generated. Spliced into one file, that
  leaves generated content in the file a reader is invited to edit, one
  hand-edit from being silently overwritten. Two files make it structural: the
  rendered one is never edited, the authored one has no `users` key to edit —
  and it is Keycloak's own export shape, so the split costs nothing invented.
  — #35, ADR-0007

- **The count of generators is fixed by the count of renderings, not by the
  count of layers.** ADR-0013 named two generators and split them by the
  vocabulary each speaks; the seed has three renderings, and the third speaks
  layer 3's words, so layer 3 ends up holding two. The rule survived being
  counted wrongly, which is the useful part: it produced the answer rather than
  being bent to fit it. — #35, ADR-0013

- **The one place the two vocabularies touch is a generator, and that is why a
  drift check is the right control.** A cost centre is a domain fact and a
  partition is a policy attribute; they hold the same value for a person, and
  nothing derives one from the other at request time. The duplication happens
  once, by rendering, so it is checkable by re-rendering — where a duplication
  by hand would only be checkable by remembering. — #35, ADR-0003

- **The plain-HTTP deviation reaches further than the register row states, and
  the extra distance is cookies.** Keycloak marks its authentication-session
  cookies `Secure; SameSite=None` whatever the scheme, so a conforming cookie
  jar cannot complete an authorization code flow over plain HTTP — the login
  post comes back *Restart login cookie not found*, which reads like a rejected
  password. Browsers do not hit it, because they treat `http://localhost` as a
  trustworthy origin — and they decide that on the **name**, so a hostname that
  merely resolves to loopback gets no pass. A `127.0.0.1 keycloak` hosts line
  fixes resolution and cannot fix this. — #36, ADR-0007, register row 2

- **A foreign issuer has to *assert* a subject, because it cannot own one.** A
  Keycloak user id is the primary key of `USER_ENTITY` across the whole
  database rather than per realm, so the neighbour realm cannot hold a user
  whose id is one of the Cast's subjects. The subject matters: skip the `iss`
  check with a *foreign* subject and the call still fails, at the principal
  directory, so `foreign_issuer_token` would go red on its own removal while
  proving nothing about the issuer. The constraint and the requirement pull in
  opposite directions, and a claim mapper is what satisfies both. — #36, ADR-0007

- **Readiness is a claim about a process, and what a dependent needs is a claim
  about state.** Keycloak reports `started in 3.7s` and opens both ports about
  four seconds before the realm import begins, so `/health/ready` goes green on
  a server with no realm. Anything waiting on that signal starts against an
  empty authorization server and fails on something unrelated to what it was
  asserting. The probe is the realm's own metadata document instead, matched on
  the exact issuer — which makes it two checks in one. — #36

- **A one-line contradiction between an artifact and three documents survived a
  full review round.** The seed shipped the issuer as `http://localhost:8081/...`
  while ADR-0005, ADR-0006 and `docs/normative-register.md` all named
  `http://keycloak:8081/...`; the review that cleared it quoted the value in
  passing and read past the hostname. Nothing in the machinery compares a seed
  to an ADR, and the walk that would have caught it is the one constraint `#12`
  performs over *derived* artifacts — which the seed, being a source, is not.
  — #36, #35

- **A closed vocabulary with no word for a refusal makes that refusal's removal
  unobservable.** ADR-0006 fixed six rejection descriptions and none of them was
  *issuer*. A token from the neighbour realm is signed by keys we do not have, so
  a server that had deleted the `iss` check entirely would still refuse it — as
  `unknown_key` — and `foreign_issuer_token` would stay green on its own recorded
  removal. Every attack row records the exact deletion that makes it pass, and a
  deletion nothing can see is not one. The seventh word is what turns the control
  from present into observable. — #37, ADR-0006

- **Where a gate lives is decided by the shape of its refusal, not by where its
  inputs are known.** ADR-0013 put gates 5 and 6 at dispatch *"where the `Action`
  is known"*, and the `Action` is knowable in middleware too. What actually
  decides it is that the scope refusal is a `403` carrying a
  `WWW-Authenticate` header, and by dispatch the response is a JSON-RPC envelope
  at `200` with no status code left to set. Gate 6's two shapes fit inside that
  envelope; gate 5's does not. — #37, ADR-0013, ADR-0002

- **The freshness hint is per caller, and a per-server setting cannot express
  it.** `ttlMs = min(5 minutes, remaining token lifetime)` depends on the token in
  front of you, so the protocol package's server-wide cache hint is the wrong
  granularity by exactly one dimension. The comparison this note originally drew
  — to ADR-0013 refusing a per-tool streaming flag on the `Action` — went moot
  four days later when the stream was cut and a flag choosing between one thing
  stopped being a granularity question at all. The cache hint stands on its own.
  — #37, ADR-0002

- **A design position that rests on having the thing it refuses is one
  verification away from nothing.** ADR-0002 declined to cut SSE because *having
  exactly one stream is what makes the refusal of a standalone stream a position
  rather than an absence*. The one stream was on an unbuilt tool, so the position
  rested on a promise; and when #37 checked all three proof tiers, none opened,
  asserted on, or depended on a stream. What replaces it is a normative register
  row saying the thing outright — the `MUST` that names both response modes binds
  a **client's** ability to read them, never a server's obligation to produce
  one. Stating a position is stronger than arranging to imply it. — #37, ADR-0002

- **The cut order was never a sequence, and the record proved it before anyone
  read it that way.** Map `#9` ranks four things from most expendable to least.
  Both cuts taken so far were taken out of order — ADR-0005 took rank 4 first —
  and rank 1 has never been defined, so a sequence reading was never executable.
  The bullet recording the first taking said *"the first cut is spent"*, meaning
  *one cut* and reading as *rank 1*. Restated as a ranking rather than corrected
  into an order, because the ranking is what both takings actually honoured.
  — #37, ADR-0005, ADR-0011

- **A constraint that is false at the wire is worse than one that is silent.**
  The first draft of `#6`'s replacement said *there is no standalone
  server-initiated stream*. Executing it found one: a `GET` carrying a token
  with no version header opens `text/event-stream` on the legacy leg and holds
  it. The constraint is a **modern-era** claim, and the legacy stream is
  inherited, gated, and named — which is the same amendment ADR-0006 already
  took when its gate chain turned out to describe the modern leg only. The
  second draft also had to qualify `405`: unauthenticated is `401`, from the
  token gate, before the transport is reached. — #37, ADR-0008, ADR-0009

- **Not every wrong request is a refusal, and treating one as a refusal is how a
  vocabulary rots.** A vendor absent from `submit_requisition`'s `enum` is a
  caller's spelling mistake: nothing was authorized, nothing was denied, and the
  tempting move is to reach for the closed reason vocabulary because there is one
  and it is right there. It answers `-32602` and carries no `reason` — a refusal
  shape here would tell a model to route around a wall that is not there, which
  is the collapse the three denial classes exist to prevent arriving through a
  fourth door. The three shapes describe *decisions about a caller*, and that is
  the line, not *anything that went wrong*. — #39, ADR-0013, ADR-0002

- **A denial class can be built, shaped and unreachable, and the honest report
  says which.** Both tools in the first slice that exercises all three policy
  entry points are gated by scope alone — reading is, and ADR-0003 rejected a
  fifth role for submitting — so `role_missing`'s `-31010` has no caller that
  reaches it at the wire until a role-gated tool exists. It is declared, its
  record states its own shape, and layer 2 asserts it; nothing over HTTP does.
  The alternative was to invent a role requirement so a criterion could be ticked,
  which would have contradicted an ADR to make a test green. — #39, ADR-0002,
  ADR-0003

- **The tool with no resource still declares the field it never consults.**
  `submit_requisition` stops at `decide_call`, and only `decide_item` reads
  `partition_bypass` — so its empty set changes no behaviour today. Declaring it
  anyway is what stops the value being a latent grant the day the tool acquires a
  resource, and this is the one ticket that declares one of each, so the
  asymmetry `{auditor}`-on-reads / empty-on-writes is visible in a single diff
  rather than tool by tool. Nothing in the type objects to the wrong value, and
  ADR-0013 records that as a known cost rather than closing it: a constructor
  check reading *bypass is legal only on a read* would be layer 2 legislating a
  rule the ADR left open, on a field whose whole point is that layer 3 owns it.
  — #39, ADR-0013, ADR-0007

- **The order two rules are written in decided whether a capability hole was
  observable.** `approve_requisition` declares the threshold before the submitter
  edge. The other order is equally correct on every row where one rule fires, and
  it would have hidden the thing ADR-0003 built a third cost centre to show:
  CC-4300 holds one Person, so every requisition charged to it is submitted by
  the only Person who could decide it, and a submitter-edge-first `Action` answers
  `segregation_of_duties` there for ever. The refusal that names a remedy nobody
  in the organisation can fill would have been unreachable — not by a decision,
  but by a tuple's order. — #40, ADR-0003, ADR-0013

- **A remedy that is true and unfulfillable is the point, and it needs a named
  test rather than a matrix row.** `over_threshold` in CC-4300 truthfully reports
  `retry_as_other_person_helps: true` while the one Person holding the role it
  points at is in another centre — and gets `not_found` on the row, so she cannot
  even see what she is the remedy for. A matrix row expecting `over_threshold`
  would assert the refusal and say nothing about the hole; what makes it a
  write-up centrepiece is the second call. — #40, ADR-0003

- **`already_decided` is not a decision about the caller, so it is not in the
  chain.** Every principal gets it on a decided row, and no role, scope or person
  changes that — which is exactly what a relationship rule is not. It is answered
  by the handler, **after** the chain permits, so a caller who may not decide a
  row learns nothing about whether it has been decided; and **at** the write
  rather than against the row hydration returned, because a check that is not the
  write is a race two callers both pass. The tempting version is a third entry in
  `Action.rules`, which reads tidier and puts a fact about the row in the field
  the vocabulary reserves for facts about the pair. — #40, ADR-0013, ADR-0002

- **A denial class stopped being unreachable, and the honest report is the same
  shape as the admission was.** #39 shipped `role_missing` declared, shaped and
  with no caller that reached it at the wire, and said so rather than inventing a
  role gate to tick a criterion. The first role-gated tool made it reachable, and
  Priya Raman is why: ADR-0007 gives her `approver` in the realm and nothing at
  the server, so the realm issues her `erp.decide` and the server refuses her —
  a divergence between two stores of the same truth, engineered on purpose, doing
  the work it was engineered for. — #40, ADR-0007, ADR-0002

---

## Findings

**Shape rule.** An observation about the trail as a whole rather than a
consequence of any decision in it. Sourced to the **walk or the date** that
produced it, not to an ADR — there is no ADR to cite, and inventing one would
misrepresent it as a decision. Every count is recorded as the **command that
re-derives it**, never as a stored literal; a snapshot may sit alongside, marked
as a snapshot, so the write-up author re-runs rather than quotes. Citations are
things to check, not facts to reuse. Where a finding has counter-evidence, the
counter-evidence is recorded to the same standard as the finding.

### F1 — The specification began generating its own work

*Found: #12, 2026-08-18. Not a decision; no ADR.*

**The claim, in the author's words, unpolished and recorded as raw material:**

> I specified a portfolio project to the standard of a regulated system, and the
> specification began generating its own work. Thirteen ADRs, a normative
> register, a 33-row attack suite, five map constraints and an eight-job CI
> design exist before any code does. The last three governance walks found
> defects exclusively in the machinery — a stale count in the constraint written
> to stop stale counts, an asserted security property nothing measured, an
> amendment idiom claimed seven times and executed twice — and none in the
> design. Documentation was the only artifact, so consistency-with-the-trail
> became the only available error signal, and that signal is infinitely
> generative.

**Both halves are load-bearing.** The process caught a real overclaim before any
code existed. The same process consumed the build window it was meant to protect.
A section carrying only the first half is marketing; only the second, apology.

#### Re-derivation — run these, do not quote the snapshot

```sh
# ADRs
ls docs/adr/*.md | wc -l

# normative register rows
grep -c '^| [0-9]' docs/normative-register.md

# map constraints (numbered top-level items in issue 2's body)
gh issue view 2 --json body -q .body | grep -cE '^[0-9]+\. \*\*'

# attack suite: rows, basis split, status split, floor — and whether meta agrees
python -c "
import yaml,io,collections
d=yaml.safe_load(io.open('docs/attack-suite/scenarios.yaml',encoding='utf-8'))
s=d['scenarios']; m=d['meta']
b=collections.Counter(r['basis'] for r in s)
st=collections.Counter(r['status'] for r in s)
f=sum(1 for r in s if r.get('floor'))
print(len(s), dict(b), dict(st), 'floor', f)
print('meta agrees:', len(s)==m['total'], dict(b)==m['basis_split'], f==m['floor'])
"

# executable code
find . -name '*.py' -not -path './.git/*' | wc -l

# CI jobs — the design, since ci.yml is still the skeleton
#   count rows in ADR-0013 §Eight continuous-integration jobs

# commits per day
git log --date=short --format='%ad' | sort | uniq -c
```

#### Snapshot — 2026-08-18, a snapshot and not a source

ADRs 13 · register rows 5 · map constraints 13 · attack suite 33 rows
(clause 19 / adr 11 / seam 3; 32 asserted / 1 documented; floor 11; meta agrees
in all three dimensions) · CI jobs designed 8, existing 0 · Python files 0 ·
`src/` directories 0.

**The drafted claim says "five map constraints"; no derivation produces five.**
Total is 13. Constraints added after the charting session (notes 1–9 were
authored while charting) is 4 — constraints 10, 11, 12 and 13. Whichever was
meant, the number in the draft is a stored literal that does not survive its own
check, which is the phenomenon the finding is about, occurring inside the
finding's first draft. Recorded because it is evidence, not because it is
embarrassing. Resolve it against a re-run before the write-up quotes any figure.

#### The three machinery defects — citations to check, not facts to reuse

| Defect | Artifact | Walk that found it |
| --- | --- | --- |
| Stale count in the constraint written to stop stale counts | map issue 2, constraint 12 item 3, against `docs/attack-suite/scenarios.yaml` `meta` | #12, Part A check A3 |
| Security property asserted with nothing measuring it | `scenarios.yaml` row `row_probe_indistinguishable`, `note` field, `status: asserted` | #12, sweep 1 (fired the stop rule) |
| Amendment idiom claimed seven times, executed twice | headers and in-body markers across `docs/adr/*.md` | #12, sweep 8 |

A fourth, found after the ADR landed and belonging to the same class: the
map-number backtick convention binds commit messages by name, and backticks do
not suppress autolinking there — so the commit establishing constraint 13
mislinked it to an unrelated pull request. See the last entry under *Notes*.

The second one is the reason the process cannot be written off: it was a false
security claim in a committed artifact, and nothing but a trail walk was in a
position to catch it, because no code existed to fail.

#### Counter-evidence, to the same standard

**The design decisions did not churn.** Verified 2026-08-18:

- `grep -h '^- \*\*Status:\*\*' docs/adr/*.md | sort | uniq -c` → **13 Accepted,
  0 Superseded, 0 Rejected.**
- Amendment dispositions across the trail: **10 × "No decision here is reversed",
  1 × "No decision here is changed", 1 × "No finding, option or decision
  changed"** — 12 amendments, zero reversals.
- Nothing reversed ADR-0004's layer split or ADR-0012's scope model; ADR-0013
  discharged the first and built on the second.

**Three vocabulary changes are the domain being learned, not instability.** Each
verified in place:

- `already_approved` → `already_decided`, plus `already_invoiced` — ADR-0003
  §Consequences: *"`approve_requisition` carries `decision: "reject"`, rejection
  is equally terminal, and the old name does not cover it."*
- `senior_approver` → `unlimited_approver` — ADR-0003 §The rules the fields
  serve: *"Renamed from `senior_approver` 2026-08-16 by ADR-0012: the role was
  never about seniority."*
- scope word `approve` → `decide` — ADR-0012: *"`decide` is both more accurate
  about the tool's contract and domain-free."*

All three are a name being corrected to fit a contract that did not move. That is
a different phenomenon from the machinery defects above, and the write-up should
not let a reader merge them.

#### The cost, in one line

The build window opened 2026-08-18, and the day's work was documentation commits
— `git log --date=short --format='%ad' | sort | uniq -c` for the shape of the
twelve days before it.

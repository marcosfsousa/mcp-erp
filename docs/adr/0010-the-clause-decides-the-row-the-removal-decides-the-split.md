# ADR-0010: The clause decides the row; the removal decides the split

- **Status:** Accepted
- **Date:** 2026-08-12
- **Ticket:** [#9 Enumerate the attack suite](https://github.com/marcosfsousa/mcp-erp/issues/9)
- **Evidence:** [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md) (the clause list and its nine open ambiguities); [ADR-0001](0001-off-the-shelf-clients-cannot-run-a-modern-only-server.md), [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md), [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md), [ADR-0006](0006-fail-closed-in-a-fixed-order.md), [ADR-0007](0007-the-realm-is-the-exhibit.md), [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md), [ADR-0009](0009-not-built-is-not-unreachable.md); map constraints #4, #7, #8, #9, #11; MCP Security Best Practices §State Handle Hijacking, fetched 2026-08-12

## Question

Map constraint #4 fixed the suite at *"10–12 named scenarios each citing the spec/RFC clause it defends"*. That sentence was written while charting, before a single clause had been read.

Five tickets have closed since, and every one of them handed scenarios forward — eighteen from the clause research, five from ADR-0002, one from ADR-0006, five from ADR-0007, three from ADR-0009, and a handful more from ADR-0001. Deduplicated, the inherited pool is about thirty-three candidates.

**No defensible filter lands on twelve.** Dropping the authorization-server group, the client-side group, ADR-0002's clause-less five and ADR-0009's three still leaves about nineteen. The number could only be reached by deliberately not defending clauses this project had already enumerated and cited.

So the question is not *which twelve*. It is what governs membership at all, and what the artifact is for.

## Decision

### The clause governs; the count yields

One scenario per distinct clause this project enforces. **Map constraint #4's number is amended to that rule**, and the count becomes an output.

The alternative was to rank thirty-three candidates against each other and defend the cut line. That exercise has no honest answer — every candidate is a `MUST` or `MUST NOT` somebody wrote down, and "we tested twelve of the thirty-one rules we found" is a worse sentence than any table.

The issue framed the suite as demonstrating *judgement rather than diligence*, and that framing survives intact: the judgement is visible in the admission rules below, not in the size of the list.

### Authorship, not the process boundary, decides whose clause

A clause is ours if the defence lives in something this repository authors — our server's code, or our hand-authored realm file. It is not ours if the defence lives in vendored code we merely configure.

This is the one rule that honours [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md) and [ADR-0007](0007-the-realm-is-the-exhibit.md) at the same time instead of choosing between them. *The authorization server is a dependency, not a deliverable* — so the four Client ID Metadata Document scenarios (`cimd_id_url_mismatch`, `cimd_redirect_uri_injection`, `cimd_symmetric_secret`, `cimd_ssrf_loopback`) are out; they assert Keycloak's validation logic, and a red there is a Keycloak bug. *The realm is the exhibit* — so `pkce_downgrade_plain`, `password_grant_refused` and `refresh_token_replay` are in; each asserts a line we wrote.

`cimd_ssrf_loopback` fails a second test independently: inside Compose every address **is** private, so the scenario inverts where we run it.

Applied to the client side, the rule admits `mixup_iss_mismatch` — exercisable against the neighbour realm [ADR-0007](0007-the-realm-is-the-exhibit.md) already provisions, a genuinely different issuer with its own keys. `as_metadata_issuer_spoof` is refused on cost rather than principle: it needs a hostile metadata host stood up for one row.

### Three bases, one table

Rows carry a `basis`: a **specification or RFC clause**, a **project ADR**, or the **era seam**.

Admitting the second was the load-bearing call. A clause-only suite would have deleted the exhibit's entire purchase-to-pay attack story — segregation-of-duties bypass, double approval through a batch retry, cost-centre probing — which is the half a domain reader recognises first, and three of which appear in the ticket's own candidate list. Citing your own ADR is not a weaker row than citing a specification. It is a stronger one, because it shows threat reasoning the standard did not hand you.

The era seam is its own basis rather than a footnote because [ADR-0009](0009-not-built-is-not-unreachable.md) asked for exactly that: its three assertions must run early and keep running, and they make a different kind of claim — about where token verification sits relative to era routing, not about a refusal.

### One row asserts nothing, and it says so

**Threshold evasion by splitting a requisition is undetectable in this model.** Detecting a split needs aggregation over a window; [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md) left time a deliberate blank page and no entity carries a timestamp, and the €5,000 threshold is evaluated per requisition against `amount`. Splitting €9,000 into two of €4,500 succeeds, by construction.

It is adopted anyway, with `status: documented, not asserted` — stating the attack, naming the control that would stop it, and citing the omission that makes it live. It is the one attack a purchase-to-pay reader thinks of unprompted, and naming a gap you chose not to close is a stronger demonstration of judgement than omitting it quietly.

This costs the suite's defining property on exactly one row, so the exception is visible in the table and **stays at one**.

### Identifiers stay guessable, deliberately

The specification says a server **SHOULD** use *"secure, non-deterministic handles"* and *"avoid predictable or sequential identifiers that could be guessed"*. A requisition identifier is a state handle by that document's own definition — an identifier a stateless server mints and receives back as an ordinary tool argument.

**We do not follow it.** Identifiers are sequential and legible (`req_0104`, the form ADR-0003 already used illustratively), and the deviation is recorded here and amended into [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md), where a reader looking at the schema will find it.

The reason is not convenience. [ADR-0002](0002-refusal-shape-follows-the-remedy.md) already made *indistinguishability* the load-bearing control: a requisition in another cost centre returns `not_found`, byte-identical to one that never existed, timing included. Unguessable identifiers would make that control impossible to exercise in its natural form — the probe scenario would have to be handed the foreign identifier out of band, turning a demonstrated defence into an asserted one. That is precisely the failure this ticket's own standard forbids: a test that passes for the wrong reason proves nothing.

Defence in depth is the thing being traded away, and the write-up says so rather than presenting the choice as free.

### The removal note is the unit of proof, and the unit of splitting

Every row records **the exact removal that makes it pass** — *delete the `aud` comparison*, *return before the header/body check*, *skip the key-set refetch* — confirmed by hand when the scenario is written.

Mutation tooling was considered and is not available here. [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) put every scenario on real HTTP against Compose, with [ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md)'s ejection test as the single in-process exception. A mutation tool runs the suite once per mutant across hundreds of mutants, against a Compose cycle measured in hours. There is no in-process suite to mutate.

The removal note then does second duty: **rows split when their recorded removals differ, and merge when they do not.** This is what makes the list's shape follow from a rule rather than from taste, and it settles the overlaps:

- `row_probe_indistinguishable` and `state_handle_hijack` describe the same caller reaching the same foreign record, but split — the first asserts **disclosure on the read path** (`not_found`, byte-identical, timing included), the second asserts **possession does not authorize a mutation** (a foreign identifier presented to `approve_requisition` or `record_invoice` is refused *and leaves state unmodified*). Different removals, and the second is the only row in the suite that asserts a refused write changed nothing.
- `signature_invalid`, `unknown_key` and `malformed_token` share clause #4's citation with `token_expired` but split from it, because deleting signature verification, deleting the key-set refetch and deleting the parse guard are three different deletions.

Paired with [ADR-0006](0006-fail-closed-in-a-fixed-order.md)'s closed rejection vocabulary, which carries the collision half: no two scenarios may pass for the same reason.

### The table is protected; the tests are cuttable, visibly

Map constraint #4 protects the suite from cuts. That protection was written for twelve scenarios and now covers thirty-one, in a solo build.

**The protection moves to the table.** All thirty-one rows are protected — name, basis, citation, what it prevents, recorded removal. The **asserting test** is cuttable per row down to a floor, and a cut row keeps its place with `status: documented, not asserted`, exactly like the threshold row.

The `status` column becomes the cut mechanism. A protection nobody can honour under pressure gets ignored silently; a table that shows how much is asserted versus merely named is a stronger artifact than one claiming a uniformity it does not have.

### The floor, and the line where the artifact changes its name

Never downgradable: **one asserting scenario per step of [ADR-0006](0006-fail-closed-in-a-fixed-order.md)'s gate chain**, plus **[ADR-0009](0009-not-built-is-not-unreachable.md)'s three seam assertions**, plus **everything map constraint #8's ship line names outright** — which is audience binding, so both audience rows survive rather than collapsing into one token-gate representative.

That computes to **eleven**:

| Gate step | Asserting scenario |
| --- | --- |
| 1 `Origin` | `dns_rebinding_origin` |
| 2 shape | `header_body_mismatch` |
| 3 exemption branch | `auth_bypass_via_method_header_mismatch` |
| 4 token | `token_expired` |
| 5 scope | `insufficient_scope` |
| 6 domain | `retry_after_sod_denial_other_person` |
| era seam | `legacy_unauthenticated_refused`, `legacy_underscoped_same_denial_class`, `legacy_discover_exemption_unavailable` |
| ship line | `audience_confusion`, `audience_missing` |

Step 3 is a conditional rather than a refusal, so its coverage is the scenario proving the exemption cannot be abused.

**The floor is a backstop, not a plan.** The plan of record is thirty asserting and one documented. At the floor it is eleven asserting and twenty documented — nearly two to one against, and at that ratio the table stops reading as a suite. So a trigger is written in with it: **below twenty asserting rows, the write-up retitles the table** from *attack suite* to *clause inventory, N proven*. A cut that changes what the artifact is should change what it is called.

### A ceiling, because the split rule has no natural stopping point

**Soft cap of thirty-five.** Crossing it triggers a review of the split rule rather than an automatic new row — above that the likely cause is recorded removals differing cosmetically rather than genuinely, which is the rule applied too finely.

### The list is data; the tests are hand-written

One committed data file is canonical: name, basis, citation, what it prevents, recorded removal, status. Tests are hand-written and declare which scenario they exercise by name, with a drift check asserting a bijection and the threshold row as its single declared exemption.

Generation was rejected. Matrix rows share one shape — principal × tool × resource → expected — and attack scenarios share almost none: a malformed header, a token in a query string, a replayed refresh token. Generating their bodies needs a per-scenario escape hatch, which is the *"language of its own"* `CONTEXT.md` rules out for the matrix and would be worse here.

Tests being the canonical carrier was rejected for a narrower reason: the accepted-risk row has no test, and would need a skipped one to hold its metadata. A skipped test in a security suite is a bad thing to own.

### Citations are pinned, quoted and dated

A revision-dated URL — never `/latest/` — the normative sentence quoted verbatim rather than paraphrased, and the date it was read.

**This is not ceremony.** The upstream pages link internally to `/specification/latest/…`; the Security Best Practices page does it in its opening paragraph. A citation harvested by following those links points at a moving document, and the quoted `MUST` can change under a table claiming to cite `2026-07-28`.

A re-fetching freshness check was rejected: map constraint #11 says nothing external floats, and putting `modelcontextprotocol.io` on the critical path would make the citation check less trustworthy than the citations.

## Options considered

1. **Hard cap at ten to twelve**, ranking the pool and defending the line. Preserves constraint #4 literally; requires deliberately not defending twenty enumerated, cited clauses, and the ranking has no honest tie-breaker.
2. **A protected core plus a cuttable extended set**, decided up front. Bounds the commitment cleanly — and it splits the artifact permanently, where the `status` column achieves the same bounding while keeping one table and making each cut visible at the moment it is taken.
3. **Subject-under-test as the membership rule.** Coherent, and it does not reach twelve either; it also cuts the realm-side scenarios ADR-0007 provisioned clients for.
4. **Clause-only membership**, sending ADR-0002's five and ADR-0009's three elsewhere. Homogeneous table; moves segregation-of-duties bypass and double approval into the matrix, which is explicitly *not* protected from cuts.
5. **Opaque random identifiers**, following the `SHOULD`. No deviation to explain and genuine defence in depth; makes the row-probe defence untestable in its natural form and costs #15's walkthrough its readable record names.
6. **Building the threshold defence** — timestamps and an aggregation rule. The most recognisable domain control in the exhibit; reopens a decision ADR-0003 closed on purpose and pulls unspecified audit-trail work into this ticket.
7. **Per-defence kill switches with a continuous-integration job** proving each removal. The only continuous proof of the property; puts a runtime flag that disables audience validation into production code, which would be the most quotable thing a reviewer could hand back.
8. **Executable mutation patches** in a directory. Re-runnable rather than historical; roughly thirty diffs against code not yet written, and a rotted patch is worse than a recorded sentence because it looks maintained.
9. **A second ADR for the identifier deviation**, on ADR-0009's precedent. Gives it a title a security reader would search for; costs a third exception to a cap now broken more often than kept, when an amendment puts the fact where the schema is.

## Consequences

**Cost.** Thirty-one rows to author, each needing a verbatim citation, a recorded removal confirmed by hand, and a distinguishable assertion. A `status` column that has to be explained or it reads as unfinished work. A deliberate deviation from a security `SHOULD` in a project whose subject is security, which needs its paragraph or it reads as an oversight. And a number that grew from twelve to thirty-one, which needs the amendment above or it reads as scope creep.

**Map constraint #4 is amended** — its number replaced by the rule, its protection moved from the tests to the table, with the floor and the retitling trigger recorded alongside.

**Map constraint #7 is not amended.** This ticket produces one ADR. The identifier decision lands as an in-place amendment to ADR-0003, which is where a reader of the schema will meet it.

**One candidate is held outside the thirty-one.** `unsupported_protocol_version` (`-32022`) becomes a row only if ADR-0009's seam assertions show it is reachable — that ADR voided the earlier observation about it because era routing precedes the gate chain, and whether a modern-era request declaring an unsupported version still arrives there is a property of `mcp` 2.0.0 that ADR-0008 recorded as read, not executed.

**`audience_missing` carries a project-ADR basis, not a clause.** Research 0003's ambiguity #5 establishes that nothing in the specification states what a server does with an audience-less token. Fail-closed is our decision, and claiming a clause for it would be the one kind of dishonesty this table cannot afford.

**Input to other tickets.**

- **#12 (module boundaries)** owns where the scenario data file finally lives and how the drift check is wired. The file is authored now at [`docs/attack-suite/scenarios.yaml`](../attack-suite/scenarios.yaml); its home is not a decision this ticket should make.
- **#11 (scope granularity)** — `insufficient_scope` asserts on the `WWW-Authenticate` challenge's `scope` parameter, so the scope vocabulary it settles is what that row quotes.
- **#15 (walkthrough)** inherits legible identifiers as a working assumption, and the deviation paragraph as something the walkthrough can show rather than describe.

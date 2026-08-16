# ADR-0011: It runs on the reader's machine, and the deviation is ours

- **Status:** Accepted
- **Date:** 2026-08-15
- **Ticket:** [#10 Decide whether Cloud Run deployment is required](https://github.com/marcosfsousa/mcp-erp/issues/10)
- **Evidence:** [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md) §"Practical read for the exhibit", [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md) §"Claude Desktop / claude.ai connectors"; [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md), [ADR-0007](0007-the-realm-is-the-exhibit.md), [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md), [ADR-0010](0010-the-clause-decides-the-row-the-removal-decides-the-split.md); RFC 8414 §2 and §3, RFC 9728 §1.2; map constraints #1, #4, #5, #7, #8, #9

## Question

Is a hosted deployment required, or does it stay additive?

The ticket attached a promoting condition: if #3 found the Client Identity Metadata Document normative, client identity is a dereferenceable HTTPS URL, something must be publicly fetchable over TLS, and purely-local stops being sufficient.

**The condition did not fire, and it did not merely fail to fire.** #3 established that identity documents are hosted by the **client**, not the resource server — so the capability hosting was meant to enable does not need it — and [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) then published the conformance client's document as a static file on GitHub Pages, which *"decouples 'a public HTTPS document' from 'a public deployment of the server'"* and left this ticket, in that ADR's own words, *"genuinely open rather than being decided from inside this ticket."*

What was left is a decision on the exhibit's own merits, and one cost nobody had assigned to it.

## Decision

### No public deployment. It runs on the reader's machine.

Three reasons, in order of weight.

**1. The promoting condition is not merely unfired — the capability does not need hosting.** Identity documents are client-hosted; ours is on Pages; the authorization server needs only *outbound* HTTPS. Research 0003 records the residual cases precisely: public deployment becomes required *"the moment you want a hosted Claude surface to connect, or the moment you write your own MCP client that must publish its own CIMD."* The second is ours and ADR-0008 already solved it without a deployment. The first is declined below.

**2. "Deploy" is not one service.** The ticket body costed Cloud Run for the server and a free-tier Postgres beside it. That is not the shape. The server validates tokens issued by Keycloak, which [ADR-0007](0007-the-realm-is-the-exhibit.md) calls the exhibit — a publicly reachable server whose issuer exists only on a laptop cannot complete a single flow. Hosting means the server, Keycloak, and a database each: a different cost and a different lifecycle from the one the ticket described. And a **permanently reachable authorization demo is a surface to defend for no demonstrative gain** — seeded demo credentials, published, standing.

**3. The evaluation moment is `docker compose up`**, which ship line #8 already delivers in full.

**Cut order #9 loses the entry rather than keeping it as an unbuilt additive item.** A decided no with reasons is an artifact; a loose end is a loose end. The entry sat fourth of five — more protected than the decision matrix and the streaming response mode — so what is removed is a comparatively protected item, not a nearly-cut one.

### Every known reason to deploy was examined, and each was declined on its own

Recorded so the decision cannot be reopened by re-running an argument already lost.

| Reason to deploy | Disposition |
| --- | --- |
| Publish our own client's identity document | **Solved without deploying.** GitHub Pages, [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) |
| Demonstrate the conformant HTTPS issuer form | **Declined.** The deviation is carried instead — see below |
| A hosted Claude surface connecting inbound | **Declined.** See the tunnel, below |

**The asymmetry is deliberate and it binds future work.** Reopening requires a reason not visible today. A later ticket must show new evidence, not re-argue one of these three.

### The ephemeral tunnel, rejected and recorded

A temporary public URL onto a local run — alive only for a recording — has neither permanence nor a standing defence burden, so it escapes reason 2 above on its own terms. It is still refused.

All three demonstration tiers run on the viewer's own machine: the conformance client, Claude Code with Anthropic's published document, and MCP Inspector. [ADR-0007](0007-the-realm-is-the-exhibit.md) says so directly — *"Inspector and Claude Code both run on a user's machine."* **None of the three needs a public URL.**

The only demonstration that does is a claude.ai or Claude Desktop custom connector, because research 0004 found that *"Anthropic's infrastructure is the HTTP client, not your machine […] A localhost dev server is unreachable; you need a tunnel or a deployment."* The same document caps its value: connectors carry a **documented authorization-spec ceiling of `2025-11-25`** and are legacy-era. A tunnel therefore buys a recording of the legacy leg — the era the exhibit deliberately does not build — which inverts the exhibit's point at a real cost in setup and recording time.

### Deviation 2 is not closed here

This is the cost the ticket body never named, and #10 was carrying it without being told.

[ADR-0005 §Deviations 2](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md) records a hard `MUST` departure: RFC 8414 §2 and §3 require an issuer identifier and its well-known path to use the `https` scheme, RFC 9728 §1.2 requires the same of a resource identifier, and under Compose both are plain HTTP — `http://keycloak:8081/realms/mcp-erp` and `http://localhost:8080/mcp`. No carve-out for localhost, loopback or development exists in either document.

Its justification had two halves. Offline reproducibility stands on its own. The second half does not, and is **withdrawn**:

> ~~The deviation is a property of the local harness, not of the design — a Cloud Run deployment (#10) is genuinely HTTPS and symmetric, and demonstrates the conformant form with no trick.~~

With the deployment declined, no environment this exhibit ships erases the deviation, and a claim resting on an environment we do not build is a claim we cannot make.

**But "permanently" would overstate it, so the framing is *not closed here*, not *owned*.** Declining hosting removes one route. It does not exhaust them. The surviving route is named so a later ticket does not have to rediscover it:

> **ADR-0005's own option 6** — terminating TLS at a fixed hostname inside Compose — rejected there because *"certificate trust becomes a setup step for every client."* That objection is against it as the **default** configuration. As a **non-default opt-in profile** it leaves the zero-setup default untouched, and the objection does not reach it. It was put to the ticket in that form and **declined for v1 on setup cost, not on impossibility.**

**Not built now.** The recorded reason for not building it is a v1 scope judgement, which is a different kind of reason from the ones that killed options 3, 6-as-default and 7 in ADR-0005, and it is recorded separately so it is not mistaken for one.

### The status difference is what stops ADR-0008's principle pointing at itself

A hostile reader who reads [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) and then ADR-0005 finds an apparent asymmetry. To honour one https `MUST` — the identity document's — that ADR accepted a GitHub Pages dependency, an outbound fetch inside continuous integration, the loss of a clean offline claim for one job, a preflight step, immutable document paths, a two-pull-request publishing sequence and the repository's first required status check, on the principle that *"exhibiting a behaviour and defending against it in one repository would be incoherent."* Deviation 2 is the same class of statement and the bill paid is zero.

**The asymmetry is a status difference, not a missing principle, and it only bites if deviation 2 is permanent.** ADR-0008 closed a `MUST` it could close; this one is deferred with its route identified. Naming that difference is what the two documents needed, because ADR-0008 stated an instrumental reason in principled language: a loopback identity document is **inoperable** — a conformant authorization server follows CIMD draft §6.5 and declines to fetch loopback URLs — so the alternative there was not a cheaper form of the capability but **no capability at all**. It paid to have the tier exist. A plain-HTTP issuer is operable, so the same forcing function is absent and the question stays open on cost rather than being settled by impossibility.

### A tension worth naming whether or not it changes the decision

The exhibit ships `dns_rebinding_origin`, a scenario premised on a network-positioned adversary reaching a loopback server. It therefore **concedes that a loopback deployment has a meaningful network adversary** — and then runs discovery unauthenticated over a channel that same adversary controls, since plain-HTTP metadata has no integrity protection and every artifact it names (the JWKS URI, the authorization endpoint, the token endpoint) is downstream of that fetch.

This is stated rather than buried. It does not change the decision — closing it needs the opt-in TLS profile above, not a deployment — but a reader who finds the tension unaided will trust the register less than one who finds it listed.

### Derived artifacts are updated in the same commit as the ADR that changes them

This ticket found cut order #9 stale in three of four places while every ADR it derives from stayed correct. That is the fourth instance this month of a **derived artifact drifting from sources that were individually right**:

| Instance | What drifted |
| --- | --- |
| Research 0003, 2026-08-06 | Conflated two independent axes; needed a reconciliation commit after ADR-0001 landed |
| Deviation-record shape, 2026-08-12 | Three ADRs each recorded a deviation differently — *"the pattern was not carried forward"* — which is why [`docs/normative-register.md`](../normative-register.md) exists |
| Map constraint #4, 2026-08-12 | The charting-era "10–12 scenarios" figure, replaced by a rule in [ADR-0010](0010-the-clause-decides-the-row-the-removal-decides-the-split.md) |
| Cut order #9, today | Three of four entries superseded by closed ADRs |

**The rule is promoted to a standing map constraint (#12), in the same-commit form.** All four instances had a correct source and a reviewer who did not look, which is exactly what a re-check obligation depends on. The register already proves the working mechanism in one domain — *"Add the row in the same commit as the ADR that creates it. Reconstructing this set by re-reading the ADR trail at write-up time is how one gets missed."* — and the constraint generalises that rather than inventing one.

It is promoted on four instances, not one. That matters: the map's own promotion rule is that a constraint earns standing status by outgrowing its origin, and generalising from a single case inverts it. The deployment decision itself is therefore **not** generalised — map constraint #5 is amended in place and nothing broader is claimed from it.

**The constraint names its artifacts, and the list is deliberately short.** A walk over named artifacts is mechanisable; "keep derived things current" never is, and a list with soft members gets checked softly. Only genuinely derived artifacts are enrolled:

1. **The map's constraints.** Admitted on narrow grounds — nothing computes them, and notes 1–10 were authored while charting. What is true is that **ADRs write back into the map**, so when one lands the check is *does this amend a constraint?* That check has fired four times in four weeks: note #4 by ADR-0010, note #11 by ADR-0008, and notes #5 and #9 by this ADR.
2. **[`docs/normative-register.md`](../normative-register.md)** — *"Every row is already decided in an ADR."*
3. **[`docs/attack-suite/scenarios.yaml`](../attack-suite/scenarios.yaml)** — nine of its thirty-one rows carry `basis: adr`, and its membership and split rules come from ADR-0010.
4. **The write-up** — *not yet written; joins when it exists.* Enrolled now with a declared state rather than left to a future ticket, which is how ADR-0005's Deviations section decayed into three shapes.

`CONTEXT.md` and the research documents are deliberately excluded. Both are sources: ADR-0001 was amended to match `CONTEXT.md`, not the reverse, and research documents are dated primary-source findings that feed ADRs.

**"Same commit" where there is no commit.** Three of the four artifacts are files and move in this ADR's own commit, literally. The map is a GitHub issue and has none, so for it the unit is the **same act** — the working session that lands the ADR, never a later pass.

That distinction surfaced an asymmetry the constraint would otherwise have inherited, and **this ADR is the instance that found it**. A file cannot be updated before the ADR that changes it exists; the map can be, and was — it carried `→ ADR-0011` while this document sat unmerged on a branch. The drift runs in the opposite direction from the four instances above: the derivative ahead of its source rather than behind it, with a shorter window and a visible cause. It is still a pointer that resolves to nothing.

So the constraint runs both directions: **every map reference to an ADR not yet on `main` names the pull request too — pointers and in-sentence attributions alike — and the markers come off at merge.** Enrolled the same way the write-up was: a declared state beats an unexplained absence.

### The first walk was performed, and the constraint carries its date

A constraint whose first act is a violation is dead on arrival. All four artifacts were walked on **2026-08-15**, and the date is recorded in the constraint — without a last-walked-clean date the next walker cannot separate new drift from inherited and has to re-derive everything, which is the work that does not get done. The baseline is a record of an event, in the same category as a citation's retrieval date, and events do not drift.

Three fixes fell out, and all three had sources that were individually correct.

**1. Map constraint #4's basis split was wrong.** It recorded *"specification clause (20), project ADR (8), era seam (3)"*; `scenarios.yaml`, which declares itself the single source of truth, has **19 / 9 / 3**. Totals agree at 31. The row that moved is `audience_missing`, and ADR-0010 says so explicitly — *"`audience_missing` carries a project-ADR basis, not a clause […] claiming a clause for it would be the one kind of dishonesty this table cannot afford."* The file was right, the ADR was right, the derived note was wrong. Everything else checks: 30 asserting, 1 documented, matching ADR-0010's plan of record and the single-documented-row invariant.

**2. The register was missing a row, for a dateable reason.** ADR-0008 sent the statelessness asterisk to the write-up because the register did not exist yet — that ADR landed 2026-08-11 and the register was created 2026-08-12. **Row 5 is added as an Interpretation.** It meets row 4's stated admission test — *"the judgement call most likely to be wrong, and the one a hostile reader would come here to find"* — and a hostile reader of a stateless-protocol exhibit goes looking for exactly this. It is an interpretation rather than plain compliance because satisfying `MUST NOT rely on prior requests` requires reading *relying on prior requests* as relying on their **state** rather than as sharing a process with a leg that handshakes. Right reading, still a reading.

**3. The map's *Decisions so far* was missing #9 entirely.** That section carries one line per closed ticket. #9 closed 2026-08-12 with [ADR-0010](0010-the-clause-decides-the-row-the-removal-decides-the-split.md) and no line was ever added — found only because the walk enumerated the map rather than reading the part this ticket was editing. The entry is written from ADR-0010 and note #4, transcription rather than decision, on the same standard as the cut-order reconciliation. This ticket's own entry was added beside it.

**A bounded check for other rows unenrolled by the same one-day gap found none.** ADR-0001 (keeping `registration_endpoint` implements a `MAY`), ADR-0002 (its refusal shapes are proven, not deviated — `row_probe_indistinguishable`, `retry_after_role_denial`, `retry_after_sod_denial_*`), ADR-0004 (no normative statement), ADR-0007 (quotes RFC 9700 §4.14.2's hard `MUST` and **follows** it — *"Refresh tokens rotate, with zero reuse"* — proven by `refresh_token_replay`) and ADR-0009 (proven by its three `basis: seam` rows) are all clean. The register's own rule excludes plainly-followed statements; they are proven instead.

## Options considered

1. **Required, promoted into the v1 ship line.** A reader points their own client at a public endpoint and completes a flow without cloning. Rejected: monthly spend with no free tier for the database, three services to keep alive, a standing abuse surface, and an evaluation moment `docker compose up` already delivers.
2. **Stays additive, built post-v1.** No change to the map, built if the ship line goes green with time and budget left. Rejected because an unbuilt additive item is a loose end a reader can notice, and the question is answerable now.
3. **Replaced by a hosted artifact** — the write-up and the recorded third-party session as the public surface, no live server. Not a rival: those ship regardless, and framing them as a substitute would imply hosting was otherwise needed.
4. **An ephemeral tunnel for one recorded session.** Rejected above, and recorded so it is not re-litigated.
5. **Re-ground deviation 2 on configurability** — keep *harness, not design* and prove it by asserting no scheme is hardcoded, so the conformant form is one environment variable away. Rejected: it demonstrates that nothing blocks HTTPS, not that HTTPS works, and dressing a weaker proof in the stronger claim's language is what created this problem.
6. **Build the opt-in TLS profile now**, closing deviation 2 inside Compose. Genuinely closes it, and it is the route recorded above. Declined for v1 on setup cost — a second configuration to maintain and document, plus certificate trust for anyone who takes it — not on impossibility.
7. **A new standing constraint generalising the deployment refusal** — public surfaces static, anything that runs runs on the reader's machine. Rejected: one instance, and the map's promotion rule is that a constraint earns standing by outgrowing its origin.
8. **The derived-artifact rule in re-check form** — artifacts re-checked when an ADR closes. Rejected: all four instances had a correct source and a reviewer who did not look, which is precisely what a re-check obligation depends on.
9. **Forward-only application of the derived-artifact rule**, with the first walk deferred to a follow-up ticket. Rejected: a constraint whose first act is a violation is dead on arrival, and the deferral would land past the build window opening on 18.08.
10. **Repair cut order #9 in full**, including defining what *conformance traceability* names. Rejected as scope: transcription of closed ADRs is this ticket's to do, deciding an undefined entry is not.

## Consequences

**Cost.** A hard `MUST` deviation the exhibit now carries with no environment that erases it, and a write-up that must say so plainly rather than gesturing at a deployment. The conformant HTTPS issuer form is never demonstrated in any configuration this exhibit ships. A demonstration class — the claude.ai custom connector — is permanently out of reach, though it was capped at the `2025-11-25` authorization spec and would have exercised the legacy leg. And a standing map constraint with a list that has to be walked, plus a date that has to be moved when it is.

**The write-up inherits one sentence it cannot soften.** It will have to carry, in substance: *the issuer identifier and the protected-resource identifier both use plain HTTP where RFC 8414 §2 and §3 and RFC 9728 §1.2 each require the `https` scheme with no carve-out for loopback or development, and no configuration this exhibit ships demonstrates the conformant form.* Paired with the route that would close it, and with the `dns_rebinding_origin` tension named above rather than left for a reader to find.

**Three documents amended.** [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md) withdraws the *harness, not design* framing and voids one *Input to other tickets* entry; its audience-mapper sentence also stops calling a local URL *"the real deployment URL"*, which read as though a non-local deployment were the real one. [ADR-0007](0007-the-realm-is-the-exhibit.md) loses a forward reference to a decision now made — cosmetic, since the baked realm copy's own reasons are independent and unchanged. [`docs/normative-register.md`](../normative-register.md) narrows row 2's justification and gains row 5.

**Three map constraints amended, one added, and the ticket record repaired.** #5 no longer says *"Cloud Run is additive"*; #9 loses this ticket's entry, loses a conditional #3 resolved in the negative, and has its remaining entries reconciled against closed ADRs; #4's basis split is corrected; #12 is new, and carries the *same act* clause plus the unmerged-pointer rule that this ADR's own landing sequence exposed. In *Decisions so far*, #7's line stops repeating the withdrawn *harness* framing — it carried the same claim as ADR-0005 and went stale for the same reason — and entries are added for **#9**, which the walk found missing, and for this ticket.

**Cut order #9 is reconciled, not re-derived.** Every fact written into it comes from a closed ticket's ADR — transcription, not decision. *Conformance traceability* is left in place and **flagged as undefined**: the phrase appears nowhere else in this repository, and defining it is a real decision that belongs to whoever owns it.

**Input to other tickets.**

- **#15 (walkthrough)** inherits a hard boundary: no live URL and no tunnel, so every demonstration runs on the viewer's machine and the recorded third-party session is the only remote-viewable artifact. The tunnel's rejection is recorded here precisely so #15 does not re-open it.
- **#11 (scope granularity)** and **#12 (module boundaries)** inherit nothing from the deployment decision, and both inherit map constraint #12: an ADR either of them produces updates the artifacts derived from it in the same commit.
- **Whoever owns cut order #9's fourth entry** inherits an explicit flag that *conformance traceability* is undefined.

**Not a contradiction of map constraint #7.** This ticket produces one ADR. The derived-artifact rule lands in the map as a standing constraint rather than as a second ADR, following the precedent [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) set when its pinning rule *"outgrew both documents"* and became constraint #11.

**Caveat.** Nothing here was executed. The claim that hosting means three services is architectural, and the routes that would close deviation 2 are described rather than tried — option 6's certificate-trust cost in particular is quoted from ADR-0005, not measured.

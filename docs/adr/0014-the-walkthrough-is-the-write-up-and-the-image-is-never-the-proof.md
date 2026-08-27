# ADR-0014: The walkthrough is the write-up, and the image is never the proof

- **Status:** Accepted
- **Date:** 2026-08-20
- **Ticket:** [#15 Shape the demo walkthrough](https://github.com/marcosfsousa/mcp-erp/issues/15)
- **Evidence:** [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md), [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md), [ADR-0007](0007-the-realm-is-the-exhibit.md), [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md), [ADR-0010](0010-the-clause-decides-the-row-the-removal-decides-the-split.md), [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md), [ADR-0012](0012-the-token-names-a-capability-never-a-role.md), [ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md); [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md); map constraints #1, #4, #5, #6, #7, #8, #12; MDN `Set-Cookie`, W3C Secure Contexts §3.1, RFC 6265bis §5.7 step 13
- **Amended:** 2026-08-27 — additive, by [#142](https://github.com/marcosfsousa/mcp-erp/issues/142). The five-minute question is **narrowed by a minute in front of it**: a first-contact reader arriving from a contract posting rather than from the protocol, recorded here for the first time. The README gains a **short form above the card**, with a soft ceiling declared in the file and asserted by a test, and its **title gains a job**. See *What the README carries, and what it refuses to*. No decision here is reversed — the card, the one embedded proof and the convention-plus-five pointer are untouched.

## Question

What does a technical reader who gives this five minutes actually look at?

The exhibit exists to close two gaps in freelance contract postings — the Model Context Protocol as a build task, and OAuth 2.0 / OpenID Connect / role-based access control — and neither is legible from a repository tree. Something has to carry the claim to a reader who will not clone anything.

The ticket was parked on 2026-08-18 rather than answered, on the ground that choosing between annotated wire transcripts, a recorded terminal session and a rendered page against an *imagined* transcript is the one call on this map that gets strictly better with its subject in front of it. That condition is discharged: every build ticket #32–#46 has merged, and `main` is green on nine jobs including four that need the stack up — `Server posture`, `Decision matrix (wire)`, `Attack suite (wire)` and `Authorization code flow`. The subject exists.

## Decision

### The wall came first, and one non-default profile takes it down

Found by execution while standing Keycloak up, and recorded on #36, #46 and ADR-0007: Keycloak marks `AUTH_SESSION_ID`, `KC_RESTART` and `KC_AUTH_SESSION_HASH` `Secure; SameSite=None`, and a browser refuses to store a `Secure` cookie delivered over plain HTTP unless the host is literally `localhost`, `*.localhost`, or a loopback address. The issuer is `http://keycloak:8081/realms/mcp-erp`, and the `127.0.0.1 keycloak` hosts-file line ADR-0005 priced buys *resolution* — W3C Secure Contexts §3.1 decides on the literal host string, so resolution is not what the rule reads.

**A human cannot complete a login in a browser against this stack today.** Our own clients dodge it by clearing the flag on the cookie objects, which is a concession a browser has no way to make.

That is not a detail of the demonstration; it is the demonstration. ADR-0007 nominates Priya Raman's realm-versus-server drift as the walkthrough's most explainable moment, ADR-0012 calls the consent screen *"the only place a human ever sees the three capabilities rendered as a delegation choice"*, and ADR-0008 calls the recorded third-party session *"the only evidence a reader cannot call circular."* All three are browser-driven.

**ADR-0005's option 6 is taken, as the non-default opt-in profile [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md) already named**: terminate TLS at a fixed hostname inside Compose. `https` is a secure context by scheme, so no host list applies and the service name works for the browser and inside the network alike. ADR-0011 declined it for v1 *"on setup cost, not on impossibility"* — that objection was aimed at it as the **default**, and it does not reach a profile taken deliberately by someone about to record a demonstration, for whom trusting a certificate is one documented step among several.

The zero-setup default is untouched: `docker compose up` still brings up plain HTTP, and every headless tier still passes without the profile.

### The walkthrough is the write-up, and the README is the only other surface

The ticket asked whether the skim reader and the reader who works through the narrative synthesis are one artifact or two. They are two, and **neither of them is new**.

Map constraint `#7` already commissions *"one narrative synthesis at the end linking down into"* the decision records; map constraint `#12` enrols **the write-up** as a derived artifact with the declared state *not yet written; joins when it exists*; and `docs/write-up-notes.md` declares itself that write-up's staging file, to be **deleted in the same commit that first renders from it** — which is what happened on 2026-08-26, so the link that stood here now points at [`docs/walkthrough.md`](../walkthrough.md). The walkthrough *is* that synthesis. Inventing a third document beside it would create two artifacts whose difference nobody could state in six months — the two-sources-one-fact drift `write-up-notes.md` explicitly refuses to become.

The other surface is the **root README, which does not exist**. The repository root holds `CLAUDE.md` and `CONTEXT.md` and nothing else, so a reader landing on the repository page today gets a file tree. It has one job — survive five minutes and hand off — and one standing rule: **everything on it that is not the card or its single proof is a link.** A README is the artifact most likely to grow a second copy of the argument.

GitHub Pages stays one directory wide. Publishing the write-up there is additive, cheap to add later, and against ADR-0011's instinct to keep the published surface short.

### Five beats, and three artifacts linked rather than walked

The walkthrough walks:

1. **The flow completes.** The hosted identity document is dereferenced, a person logs in, a person consents, the code is redeemed, and the token is used on a real call.
2. **The three denial classes, side by side** (ADR-0002) — under-scoped, so the tool is absent from `tools/list`; scope-without-role, so `-31010`, a protocol error where a `403` would lie; and a segregation-of-duties violation, which is a domain rejection and not an authorization error. **The middle class is performed, not asserted**: a real consent screen hands Priya Raman `erp.decide` and the server refuses her anyway. ADR-0007's nominated moment is not a sixth beat — it is what makes this one worth watching.
3. **`tools/list` differs between two principals**, so the delegation ceiling is visible in the protocol surface itself.
4. **Row scoping**, where Yusuf Demir holds everything Tomas Weber holds in another cost centre and CC-4100 rows come back `not_found` rather than forbidden.
5. **The recorded third-party session.**

Beats 3 and 4 earn their place on a specific ground: they are where *role-based access control* stops being a phrase. A reader who has integrated an API has seen `403` and has not seen `tools/list` return a different set of tools to a different token.

**Three candidates are linked and quoted rather than walked.** The batch call with several independent outcomes is a good paragraph and a poor scene — it reads as an implementation detail to anyone not already thinking about idempotency. The deviation paragraph is stronger as one honest paragraph pointing at [`docs/normative-register.md`](../normative-register.md) than as a staged moment. The decision matrix and the attack suite are tables, and a table is quoted from, not narrated.

**One candidate in the ticket body was already stale and is struck.** #15 nominated *"the batch `approve_requisition` SSE stream showing mixed verdicts in one call"*. There is no stream: #37 took ADR-0002's option 5, amended map constraint `#6` to *"every modern POST is answered `application/json`"*, and moved the position the one stream protected into the normative register as its *No streamed response mode* interpretation. Several outcomes from one request survives; the stream does not.

### What a machine can keep true, a machine keeps true

The ticket asked whether the walkthrough renders from the same source the tests do, or is prose free to drift. It is split by what each part is, because the two halves fail differently.

**The tables render.** Map constraint `#4` has committed the decision matrix to *"one source rendering into both tests and the write-up"* since the charting session; [`docs/decision-matrix/matrix.yaml`](../decision-matrix/matrix.yaml) drives `tests/matrix/` in its entirety and generates the fixtures, and the write-up half has never been built because there was no write-up. [`docs/attack-suite/scenarios.yaml`](../attack-suite/scenarios.yaml) is the same shape, with its counts asserted against the file by `tests/attack_suite/test_the_suite_holds_together.py` after two separate incidents of hand-kept copies drifting within a commit of being corrected. **This is the ticket that discharges that half of constraint `#4`.**

**The transcripts are captured artifacts**, not prose: a run writes them, a committed copy is what the write-up includes, and a check refuses a diff — the `Seed renders clean` pattern extended to a further rendering.

**The connective prose is hand-written and free.** Putting narrative inside a generator is how a write-up stops being written.

The evidence that this split is the right one is in the tracker: #80, open, *"The written claims have drifted from the code, in eleven places."* The failure mode is whole claims going stale, not stray literals — which is also why an assert-the-literals-only approach was declined.

#### Captures are committed verbatim, and masking happens inside the check

The volatile set is small and known: the bearer token and its signature, `iat` / `exp` / `auth_time`, `jti`, `sid`, the realm's per-boot key identifier, the authorization code, `state`, the challenge, and the session cookies. What does not vary is everything the exhibit claims — `sub`, `aud`, `iss`, the granted scopes, the ordinal identifiers, list ordering, error codes and refusal shapes.

So the artifact is **exactly what came off the wire**, and the check re-captures, masks the volatile fields on *both* sides, and compares. The file changes only when something substantive changed. A reader and a machine look at the same object, which is the standard the rest of this exhibit holds itself to.

**The committed bearer token is not a secret, and the write-up says so in one line**, in the same register `seed.yaml` already uses for the password. It is minted by a throwaway local realm whose signing keys are regenerated every boot, it expires in five minutes, and it is issued to a Person whose password is committed as `not-a-secret-demo-password`. It is unverifiable by anyone, anywhere, five minutes after capture — and a real expired token is better evidence than a placeholder, because a reader can decode it and check `aud` against what the write-up claims.

**Rejected: making the run deterministic.** Pinning the realm's signing key and freezing the clock would buy byte-identical captures at the cost of a property [ADR-0007](0007-the-realm-is-the-exhibit.md) chose deliberately — fresh signing keys on every boot, which is what makes key rotation exercised rather than asserted. Spending that to make a document tidier is a bad trade.

### The image is never the proof

Two moments are pixels rather than bytes, and ADR-0011 rules out both a live URL and a tunnel, so they have to be carried into the document.

The consent screen and the refusal that follows it ship as **screenshots, each sitting beside the captured transcript that proves what it claims**. The transcript is load-bearing and checked; the image is illustrative and is not. That ordering is the whole rule, and it is what makes it acceptable to admit an artifact class the diff check cannot police into a repository that today contains **zero binary files**.

**Exactly one recording exists**, and it is the third-party session, because that beat is a demonstration of contact and has no textual substitute we could author without circularity.

### Claude Code carries the recording; Inspector carries the reader

Research 0004 found two off-the-shelf clients that can drive a modern-only server, and they are not interchangeable.

**Claude Code 2.1.223** has the modern era compiled in behind an undocumented `MCP_PROTOCOL_NEGOTIATION=auto`, complete era-independent OAuth, and a `client_id` that is **Anthropic's own hosted metadata document**. ADR-0007 verified by execution that our realm satisfies the gate that path needs. The recording therefore shows a vendor's shipped product, using a document that vendor publishes, driving our server — and an assistant calling ERP tools, which is the first gap in its natural habitat. Nothing in that chain is ours except the thing under test.

**MCP Inspector 2.1.0** is the reference tool and ships as a **written path, not a recording**. It is the fastest route from *I read this* to *I ran this*, and its two frictions are wrong for a recording and right for a document: it pins a beta SDK predating a fix for 401-on-probe handling, and ADR-0007 measured that it is proxy-mediated and sends no `Origin`. Its Legacy default is called out explicitly, because map constraint `#6` records that an untouched Inspector opens the standalone stream the legacy leg inherits — which reads as the exhibit contradicting its own no-streams claim unless the reader is warned.

**The recording lives as a release asset, with one committed still frame as its poster.** A repository-committed animated image would put tens of megabytes into every future clone forever so that one skimming reader avoids one click; GitHub's attachment content-delivery network would leave the artifact untracked, unversioned, and held by an opaque URL — the same *held by nothing* shape ADR-0008 wrote a section about on finding the account-name hazard. A release asset keeps it in this repository's own namespace and gives it a version, and the still frame means the write-up shows the consent screen at rest to a reader who never plays it.

### The gating job performs the centrepiece

[ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) handed this ticket *"which Person the conformance client authenticates as"*. #46 answered it by execution, with a **pair**: Priya Raman, who holds `approver` in the realm so the authorization server grants all three capability scopes, and Rafael Costa, who holds `invoice_clerk` alone so `erp.decide` is declined — which is how ADR-0012's open verification item about the `scope` response parameter got answered. **The pair is ratified.**

What it *calls* is extended by exactly one call. The leg currently earns Priya's token through a real consent screen and then calls `list_requisitions`, which succeeds; the refusal that makes her the exhibit's most explainable moment is asserted only on **minted** tokens in `tests/matrix/` and `tests/wire/`. So Priya's earned token is presented to `approve_requisition` and the assertion is `-31010`.

The duplication is deliberate and answerable in the sentence the write-up wants anyway: **every other proof of `-31010` uses a token we minted for ourselves, and this one uses a token a human consented to at a login screen.** It also fixes an inconsistency the capture rule would otherwise have: the beat's transcript now comes out of a run the merge gate protects, rather than one nothing checks.

### Three tickets, and the narrative is last

| Ticket | What it holds | Checkable by |
| --- | --- | --- |
| **(i) The TLS profile** | The opt-in Compose profile, its certificate story, the documented trust step | A browser completing a login against the service name |
| **(ii) The machinery** | Transcript capture and masking with its diff check; the table rendering that discharges constraint `#4`; the added conformance call; the root README | Continuous integration |
| **(iii) The narrative** | The write-up, the screenshots, the recording and its release, retiring `write-up-notes.md` | Reading |

The profile stands alone because it is the only piece that changes how the stack runs and the only one that can fail for environmental reasons on someone else's machine; bundling infrastructure with a rendering pipeline is how a ticket stops being reviewable. Machinery and narrative split because one is checked by a machine and the other by a person, and those want different reviews.

**(iii) is worked last — after every other issue in this repository is closed, not merely after (i) and (ii).** It deletes `write-up-notes.md`, which must stay available to anything still in flight, and it would otherwise narrate over code that open bugs are about to change; #80 documents eleven such places today.

**The gate is one standing condition, not a set of edges.** The narrative ticket may start when `gh issue list --state open` returns nothing but itself. Nothing to maintain, nothing for a future ticket to remember, falsifiable in three seconds — where per-issue `blocked_by` edges would impose exactly the re-check obligation map constraint `#12` was promoted to reject, after four instances of a correct source and a reviewer who did not look.

It is strict, so it carries a **named override**, in the shape ADR-0008 accepted for a Pages outage: the condition may be overridden at the cost of **one recorded override** — a comment on the narrative ticket naming which open issues were judged unable to affect a claim, and why. A label would have left nothing behind.

### What the README carries, and what it refuses to

*Amended 2026-08-27 by [#142](https://github.com/marcosfsousa/mcp-erp/issues/142) — the reader this section answers for is narrowed, and two things join the page above the card. Nothing below the marked passages changes.*

**The reader is a first-contact reader with about a minute, and the five minutes above are what they spend next.** Every reader this repository's trail names is already inside the subject matter: the *technical reader* of #2 §Notes and of this document's own §Question, the *hiring reader* of ADR-0005, and the *hostile reader* [`docs/normative-register.md`](../normative-register.md) is written for. None of them arrives cold. The reader who does — who has not come looking for Streamable HTTP and does not yet know what a Model Context Protocol server is — had no budget recorded anywhere, and #142 measured what that cost: at `126c24c`, **402 of the page's 785 words came before its one proof**, so the exhibit's shortest complete thought was its third section. The minute is not a competitor to the five. It decides whether the five are spent at all.

**A short form above the card**, hand-written, with a **soft ceiling declared beside it and asserted by a test**. Soft in the shape [`docs/decision-matrix/matrix.yaml`](../decision-matrix/matrix.yaml) already uses for its own: the number lives in the artifact the test reads, and red means *check whether this has started restating the page below it*, not *delete a sentence*. That is the right instrument here for a specific reason — this is the one surface in the repository made of prose that nothing else renders, and a hard cap would make every future edit a negotiation with a linter on the one page with no source to be re-rendered from. **The number is not restated here**, on the reasoning map note `#4` gives for every other derived count. Every count, figure or identifier inside the short form is included from a checked artifact or absent.

**What the short form is that the walkthrough is not.** [`docs/walkthrough.md`](../walkthrough.md) walks the argument end to end, five beats and their wire excerpts; the short form **states the claim once and shows the single artifact that settles it, and it narrates nothing**. That sentence is load-bearing rather than descriptive: option 4 below refuses two documents whose difference nobody could state, and a third surface is that same question a third time. **If a future edit makes the distinction untrue, the short form has stopped being a different kind of object and should go rather than grow.**

**The title carries first contact.** It is the first line a reader's eye lands on and the only one that runs before the card, so it names what this is **with the acronym expanded**, and it does not spend itself on the repository name — GitHub prints `marcosfsousa/mcp-erp` in the page header directly above it, so an `# mcp-erp` heading is a duplicate of the line above it and the exhibit's most-read line says nothing. It was exactly that until #142.

A card: what this is, the two gaps it closes, and how to run it — including the `127.0.0.1 keycloak` hosts-file line and the opt-in profile for anyone who wants the browser beats.

**One embedded proof**, and only one: `tools/list` answered for two different tokens, side by side. It is the exhibit's shortest complete thought — same server, two tokens, different tools — and the only beat that lands both gaps in a single artifact. It is **included from the captured set**, never retyped, so the skim surface and the deep surface cannot disagree.

**A pointer outward that is a convention plus five names, not an index.** GitHub renders a directory's README when a reader clicks into it, so the ten per-directory READMEs need no listing — one sentence stating that every directory holding something non-obvious carries its own README covers all of them and stays true when an eleventh appears. What a reader cannot discover by browsing is named explicitly: [`CONTEXT.md`](../../CONTEXT.md), [`docs/adr/`](.), [`docs/normative-register.md`](../normative-register.md), [`docs/decision-matrix/matrix.yaml`](../decision-matrix/matrix.yaml) and [`docs/attack-suite/scenarios.yaml`](../attack-suite/scenarios.yaml). The research notes stay unlisted; every ADR cites them by name in its Evidence line, so they are one hop from anyone who wants them.

The register is the highest-value line on that list. A document that volunteers where the project knowingly violates a `MUST` is the strongest signal on the page, and nobody would find it by clicking around.

## Options considered

1. **Do not build the TLS profile; split the beats into performed and described.** Cheapest, and pre-authorised by the inherited-hazard comment on this ticket. Rejected: it ships the exhibit's most explainable moment as prose and leaves ADR-0008's only non-circular evidence tier unbuilt.
2. **Build the profile inside this ticket.** Rejected on shape, not on merit — every other map ticket produced a decision and handed the build to its own issue.
3. **One artifact: the root README is the walkthrough.** A README long enough to walk five beats is not skimmable; one short enough to skim is not the synthesis.
4. **A `docs/walkthrough.md` beside the planned write-up.** Two documents whose difference nobody could state, which is the drift `write-up-notes.md` exists to avoid.
5. **Publish the write-up to GitHub Pages.** Additive and cheap later; declined now to keep the published list a list somebody wrote.
6. **Walk every nominated candidate, all nine.** Makes the write-up carry both tables inline rather than link to them.
7. **Hand-written throughout.** Every literal in it becomes a future #80.
8. **Fully rendered, prose included.** The most machinery available, and narrative inside a generator does not get written.
9. **Prose with every literal asserted by an existing test.** No new machinery; polices the wrong unit, since the observed failure is whole claims.
10. **Placeholders for volatile fields.** An exhibit about token validation showing no token.
11. **A deterministic run** — pinned signing key, frozen clock. Spends ADR-0007's exercised key rotation for byte-identical captures.
12. **A recording as a committed animated image.** Inline playback everywhere, tens of megabytes in every clone forever.
13. **A recording on GitHub's attachment content-delivery network.** Free, and untracked, unversioned, held by an opaque URL.
14. **Inspector as the recorded client.** The better picture of the tool surface; a beta-SDK rough edge against an authenticated modern server is a thing to explain on camera.
15. **Recording both clients.** Two re-record burdens for one claim.
16. **Reworking the cast toward CC-4100's complete chain** for the conformance leg. Trades the exhibit's most legible moment for a second demonstration of something `tests/wire/` already proves green.
17. **Per-issue `blocked_by` edges to enforce "last".** Precise, and an obligation on every future ticket to remember an edge.
18. **A `blocked:last` label.** Review rather than mechanism.
19. **A full asserted index in the README**, some thirty links checked by a test. A second table of contents competing with the write-up's, and a list that needs maintaining where a sentence does not.

## Consequences

**Cost.** A Compose profile and a certificate story that did not exist. A capture-and-mask pipeline and a further rendering under `Seed renders clean`'s discipline. One extra call in a merge-gating job. The repository's **first binary files** — two screenshots and a still frame — and its **first release**. A recording that is a manual act, and stale the day the login screen changes. And a write-up that cannot start until the tracker is empty, which is a real scheduling constraint accepted with its override.

**Two items this ticket was holding are discharged without a decision, because the build already answered them.** The list-ordering hazard ADR-0003 left open — no entity carries a timestamp, so list results have no defined order — was taken by #39: `ORDER BY requisition.id`, with the docstring stating it is *"for the reader and for nothing else"* and no test asserting it. *Arbitrary but deterministic, pending the audit-trail work* is what shipped. And ADR-0008's hand-off on the conformance client's Person was answered by #46 with the pair ratified above.

**ADR-0007's owed line gets an owner.** Its Cost section records *"A committed password that needs one line of write-up so nobody reads it as a leaked secret."* That debt has been ownerless because there was no write-up; it lands on ticket (iii). Nothing else about the password changes — Direct Access Grants are disabled on every client and the refusal is asserted by `password_grant_refused`, so it is not exchangeable for a token; ADR-0011 declined any deployment; and the realm is rebuilt from file into an in-memory database on every boot. The exposure is nil, and the risk is that a reviewer who does not read the comment files a finding.

**Map constraint `#4` is half discharged and half still open.** The write-up half now has a ticket. The matrix remains unprotected by the attack suite's cut rules, which is unchanged by this decision.

**The normative register is untouched.** Nothing here departs from a clause. The opt-in profile does not close row 2 either: the deviation is a property of the **default** configuration, which is unchanged, and a profile a reader may decline to take does not erase what `docker compose up` does. Row 2 stays *not closed here*, with its route now built rather than merely named.

**Cost, 2026-08-27 by [#142](https://github.com/marcosfsousa/mcp-erp/issues/142).** A second marked region in the README, rendered by the same generator as the first; a ceiling test on hand-written prose, which is a check on a surface that until now had none; and a standing risk that the short form and the card below it converge. The convergence is what the ceiling is asserted to make somebody look at. If the short form makes a section below it redundant, that is a finding to file rather than a re-cut folded in — the five existing sections are outside #142.

**Input to other work.** Ticket (i) is the first thing in this project whose acceptance criterion is a human action in a browser. Ticket (iii) inherits every write-up debt booked across the ADR trail, `write-up-notes.md` included, and is the commit that deletes it.

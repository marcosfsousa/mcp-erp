# ADR-0003: The schema is the policy function's argument list

- **Status:** Accepted
- **Date:** 2026-08-06
- **Ticket:** [#6 Fix the ERP data model and seed fixtures](https://github.com/marcosfsousa/mcp-erp/issues/6)
- **Evidence:** map constraints #2 (four entities, governing rule), #3 (intersection authorization), #4 (matrix as data, not a DSL); [ADR-0002](0002-refusal-shape-follows-the-remedy.md), which handed this ticket the multi-cost-centre question

## Question

What do Vendor, Requisition, PurchaseOrder and Invoice actually hold, what rules do those fields serve, and who is in the seeded cast?

The map's governing rule is that a field earns its place only if it changes an authorization decision. Applied honestly, that rule says the schema is not a model of purchasing — it is the argument list of the policy function, written down. Everything below follows from taking that literally, with exactly one exception, named as such.

## Decision

### Cost centres are flat; breadth is a role, not a wider membership

Three cost centres — `CC-4100` Facilities, `CC-4200` Engineering, `CC-4300` Marketing — as a flat list of codes. Every person holds **exactly one**. No hierarchy, no membership table.

A person who must see more than one centre holds the `auditor` role, which reads across all of them. Row scoping is therefore one equality check plus one role bypass, and the two mechanisms stay distinguishable: an auditor reading three of three is visibly different from an approver who merely belongs to two, which is the reason the third cost centre exists at all.

**ADR-0002's open question is closed in the negative.** `submit_requisition` keeps no `cost_centre` input. A requisition is stamped with the submitter's own centre, so a cross-centre submission stays inexpressible rather than merely refused, and no schema anywhere enumerates the organisation's centres. Multi-membership would have forced that input back, and with it a free-text value whose refusal leaks which centres exist — the exact probing surface ADR-0002 designed out.

### The entities

| Entity | Fields |
| --- | --- |
| **Vendor** | `id`, `name` |
| **Requisition** | `id`, `cost_centre`, `vendor`, `amount`, `currency`, `description`, `submitted_by`, `status` |
| **PurchaseOrder** | `id`, `requisition_id`, `approved_by`, `status` |
| **Invoice** | `id`, `purchase_order_id`, `recorded_by` |

`status` on a requisition is `submitted | approved | rejected`; on a purchase order, `open | invoiced`. `currency` has one legal value, `EUR`, and is kept anyway — an amount without a currency is a defect waiting for a second currency, and ADR-0002 already specified amounts as a decimal string plus an explicit currency.

**Invoice is where the governing rule bites hardest.** It carries no amount, no vendor, no supplier reference — the purchase order fixes all three, and since a purchase order takes exactly one invoice at full value, an amount field could only restate one. Recording an invoice validates two things: the order is `open`, and the caller is not the person who approved it.

**PurchaseOrder does not copy the cost centre forward.** ADR-0002 described it as carrying "the approver identity and cost centre forward"; the identity is load-bearing and the cost centre is a join away. Denormalising it would buy a shorter query and a second copy of a fact that can disagree with the first.

`description` is the **one exception** to the governing rule, granted for the reader's benefit — "40 ergonomic desk chairs" narrates in a way `req_0104` does not, and issue #15's walkthrough has to be readable by a human. Display names on people are part of the same exception. It is recorded here as a single carve-out so a reviewer can check the claim against exactly one place rather than trusting that the rule held everywhere.

### Identifiers are sequential and legible, against a specification SHOULD

*Amended 2026-08-12 by [#9](https://github.com/marcosfsousa/mcp-erp/issues/9).*

This ADR listed `id` on every entity and left its form open. [#9](https://github.com/marcosfsousa/mcp-erp/issues/9) closed it, because the form decides what an attack scenario can assert.

**Identifiers are sequential and human-readable** — `req_0104`, the shape this document already used illustratively above — and the same for the other three entities.

That is a deliberate deviation from the specification. A requisition identifier is a **state handle** by the specification's own definition: an identifier a stateless server mints and *"receive[s] back as an ordinary tool argument on each request"*. The mitigation text carries two halves, and we follow one:

> MCP servers **MUST NOT** treat possession of a state handle as authentication. […] MCP servers **SHOULD** use secure, non-deterministic handles generated with secure random number generators. Avoid predictable or sequential identifiers that could be guessed by an attacker.
>
> — [MCP Security Best Practices §State Handle Hijacking](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices#state-handle-hijacking), fetched 2026-08-12

The `MUST NOT` is honoured and asserted twice over — [ADR-0002](0002-refusal-shape-follows-the-remedy.md)'s indistinguishable `not_found` on the read path, and a refused write that leaves state unmodified. **The `SHOULD` is not followed**, and the reason is that following it would delete the proof of the first.

ADR-0002 made indistinguishability the load-bearing control. Unguessable identifiers would make that control impossible to exercise in its natural form: the probe scenario could no longer *guess* a foreign identifier, it would have to be handed one out of band from the seed — turning a demonstrated defence into an asserted one, which is the failure the attack suite exists to forbid. Legible identifiers also keep #15's walkthrough readable and the matrix's set-equality assertions reviewable by a human.

What is genuinely traded away is defence in depth: an attacker reaches the row-scoping check rather than being stopped before it. The write-up states that rather than presenting the choice as free. Recorded in [ADR-0010](0010-the-clause-decides-the-row-the-removal-decides-the-split.md), which owns the two scenarios that rest on it.

### The rules the fields serve

1. **Row scoping.** You see requisitions in your own cost centre. `auditor` reads all three and writes nothing.
2. **Threshold: €5,000.** At or below, `approver` suffices. Above, `senior_approver` — which has no upper limit, so it covers small requisitions too and nobody needs to hold both.
3. **Segregation of duties, two edges.** Submitter ≠ approver, tested against `Requisition.submitted_by`. Approver ≠ invoice recorder, tested against `PurchaseOrder.approved_by`. This is what makes `record_invoice` earn its place; with one edge it would demonstrate no authorization behaviour of its own.
4. **Terminal states.** A second decision on a decided requisition returns `already_decided`; a second invoice against an order returns `already_invoiced`. Both write paths are idempotent by the same mechanism, which is what ADR-0002's promise — that a model retrying a whole batch cannot double-approve — rests on.

**No delegation, and no editor.** The only identity in any check is the person the token names. There is no update tool among the five, so a requisition is immutable once submitted and no editor identity exists to reason about. Delegation is deliberately absent: OAuth 2.0 *is* a delegation protocol — an application acting on a user's behalf — and modelling a second, human-to-human delegation in the same exhibit would blur the exact word it exists to demonstrate. It survives as a write-up paragraph, the same shape the map already uses for policy engines.

### Four roles

`approver`, `senior_approver`, `invoice_clerk`, `auditor`. Submitting is gated by scope alone: anyone who can reach the server may raise a requisition against their own centre, which is true of real organisations and keeps the role set to the tools where a role denial is interesting. Role names remain placeholders owned by #11, as do the scope strings.

### Identity: one seed file, two renderings

The seed file is the single source of truth for the organisation and lists a chosen, readable subject for each person. A build step renders it twice — into the ERP database rows, and into the authorization server's user import. The join at request time is on the standard `sub` claim, scoped by issuer, with the values fixed in the repository.

The alternatives all failed on the same axis. Keying on `email` or `preferred_username` puts a claim the OpenID Connect specification explicitly declines to guarantee as stable or unique in the position of a primary key — quotable chapter and verse, in front of the exact reader this exhibit targets. Late-binding real subjects from a provisioning step makes `docker compose up` depend on something the repository does not contain, against ship line #8.

**#7 inherits a constraint:** whatever authorization server it chooses must accept imported user identifiers. Keycloak's realm import does; a self-authored server does trivially.

### The cast

Seven people. Every one reaches a branch nothing else reaches.

| Person | Centre | Roles | Exists to make reachable |
| --- | --- | --- | --- |
| Priya Raman | CC-4100 | — | Scope-only submit; `role_missing` on approve |
| Tomas Weber | CC-4100 | `approver` | Approves others' ≤ €5,000; refused above; refused on own — and is the submitter edge 1 tests against |
| Ingrid Holm | CC-4100 | `senior_approver`, `invoice_clerk` | Approves above threshold; two roles composing on one person; cannot invoice what she approved (edge 2, negative) |
| Rafael Costa | CC-4100 | `invoice_clerk` | Edge 2, positive — the counterparty who *can* invoice Ingrid's approvals |
| Yusuf Demir | CC-4200 | `approver` | Row scoping — CC-4100 rows return `not_found` |
| Anna Lindqvist | CC-4200 | `auditor` | Breadth by role — reads 3 of 3, writes nothing |
| Mei Tanaka | CC-4300 | `approver` | The third centre's inhabitant: makes an auditor's 3-of-3 distinguishable from merely holding two centres |

Four vendors ship as rows; the `enum` ADR-0002 put in `submit_requisition`'s schema is generated from them at startup, so the tool definition cannot drift from the data.

### The capability holes are deliberate

| | submit | approve ≤ €5k | approve > €5k | record invoice |
| --- | --- | --- | --- | --- |
| CC-4100 | ✓ | ✓ | ✓ | ✓ |
| CC-4200 | ✓ | ✓ | ✗ | ✗ |
| CC-4300 | ✓ | ✓ | ✗ | ✗ |

**CC-4100 is the only centre where the purchase-to-pay chain runs end to end.** The other two are row-scoping foils that can start a chain they cannot finish. Completing them would add four people who reach no new branch, since both separation edges and the threshold are already fully covered in CC-4100.

Stating this yields a point worth making. In CC-4200, an over-threshold refusal truthfully reports `retry_as_other_person_helps: true` while no such person exists in the organisation. **A remedy names a class of action, not an available human.** One matrix row lands deliberately on that hole and asserts it, so the distinction is tested rather than merely described — conflating the two is how authorization systems come to promise things the organisation cannot deliver.

### The organisation is authored; the test data is generated

The seven people, three cost centres and four vendors are hand-written and stable — they are the cast, and legibility is the point. The disposable per-row requisitions are **generated from the decision matrix definition**, which is map constraint #4 applied once more: one source rendering into tests, prose, and now fixtures.

Each write row owns a fixture outright, so no row can disturb another, and the seeder wipes and reloads once before a full run rather than between rows. That leaves #8 free to choose an in-process runner or real HTTP later, and it puts no reset route on a server whose entire subject is authorization.

Generation also removes the correspondence that would actually rot. Read rows assert what a principal can see; every write fixture added changes that answer. A generator that emitted all of them can compute it, where a human maintaining it by hand cannot.

**Guardrail.** Each row's `given` block is a flat literal record — cost centre, amount, submitter, state — with no defaults, no inheritance, and no references to other rows. The generator is a loop emitting one requisition per row, with an id derived from the row's own name. The moment a `given` block wants a conditional, it is becoming the DSL constraint #4 refused, and review should catch it. The generated seed is **committed** and continuous integration fails on any diff, so what ships is readable as data rather than knowable only by executing a script.

### The matrix skeleton

Columns: `id` · `principal` · `tool` · `given` · `expect`.

`principal` is **person × scope set**, not person. Effective permission is granted scope ∩ role permission, and the two inputs are only genuinely independent if the matrix can vary them independently — including the case the exhibit most wants to show, a senior approver whose application asked only for read scope and who therefore cannot approve. Fixing scopes per persona would have filled the cast with people existing solely to be under-scoped.

`expect` is `allowed` or a `reason`. Wire shape, remedy and both retry booleans are **derived** from the reason, and ADR-0002's reason-to-shape mapping is asserted in exactly one dedicated test. Rows stay short enough to render as prose, and changing the mapping is a one-line change.

Read rows assert **set equality** over returned identifiers. Row scoping is a question of which rows come back, not in what order; asserting an order would assert something the authorization model does not care about.

About 29 rows: `tools/list` 4, `submit_requisition` 3, `approve_requisition` 9, `record_invoice` 6, `list_requisitions` 4, `get_requisition` 3. Roughly 18 are write rows, each owning a generated fixture.

## Options considered

1. **A cost-centre hierarchy, or letting a person hold several.** Both make row scoping richer and both reopen `submit_requisition`'s cost-centre input, taking the enumeration leak with it. The hierarchy additionally buys recursive resolution and a tree the demo must explain before the authorization point lands.
2. **One separation edge instead of two.** Simplest rule, one stored identity — and `record_invoice` stops earning its place, contradicting ADR-0002's stated reason for including it. Three edges was also rejected: submitter ≠ invoice recorder is the least defensible in real purchase-to-pay, where the requester routinely confirms what arrived.
3. **Dual control above the threshold** — two approvals from two people. Genuinely richer, and it yields a third separation edge free. Rejected for the partial state it requires: a `partially_approved` status, an approvals list rather than one identity, and a real interaction with per-item idempotency, all to demonstrate a tier the role already demonstrates.
4. **High-value approval as its own scope.** Attractive because it pushes the rule into the layer the exhibit is about, and it collides with ADR-0002's rule that caller-level refusals are whole-call: whether the scope applies depends on the item's amount, so one expensive item would fail an entire batch with a `403`.
5. **An invoice amount, checked against the order.** Either exact match or a cap. The cap is a genuine control — over-invoicing against a legitimate approval is the classic purchase-to-pay fraud — but it is domain fraud, not protocol or authorization, so the attack suite never showcases it. The exact match is input validation wearing an authorization costume: its remedy is "correct your number", which is not one of the three the vocabulary is built around.
6. **Vendors restricted per cost centre.** The only version where Vendor changes an authorization decision unaided, and therefore the only one that passes the governing rule without help. Rejected as a fourth relationship rule the map never asked for, with a refusal that leaks which vendors serve which centres.
7. **A fifth role gating submission.** Uniform — every write tool checks scope then role — and it makes the `-31010` denial reachable on the first tool a walkthrough touches. Rejected as a role modelling a permission almost everyone holds.
8. **Resetting the database between matrix rows.** Small seed, matrix rerunnable forever. In-process rollback decides #8 by implication and leaves the matrix, unlike the attack suite, never crossing a network boundary. Truncate-and-reseed over HTTP needs either a test-only reset route — the single most quotable finding a reviewer could hand back — or a runner holding a database credential, which undercuts the black-box claim it exists to make.
9. **Timestamps now.** See below; deliberately deferred rather than decided.

## Consequences

**Corrections to ADR-0002.**

- `already_approved` becomes **`already_decided`**. `approve_requisition` carries `decision: "reject"`, rejection is equally terminal, and the old name does not cover it. **`already_invoiced`** joins the closed vocabulary. The full set is now `insufficient_scope | role_missing | segregation_of_duties | over_threshold | not_found | already_decided | already_invoiced`.
- The purchase order carries the approver identity forward but **not** the cost centre.
- The multi-cost-centre question ADR-0002 handed here is answered **no**, so `submit_requisition`'s input schema stands as written.

**A named open question, left open on purpose.** No entity carries a timestamp. *When* things happened — and whether that belongs on the entities as columns or in an append-only decision log — is handed to the audit-trail work the map lists as unscoped, which is the right owner and would otherwise inherit a choice made here without its context. The cost is real: list results have no defined order until someone specifies one, so #15's walkthrough cannot rely on a stable presentation sequence.

**Cost.** The seed file grows a second output format and a regeneration step, and continuous integration gains a drift check. The `given` block is a small format that must be actively kept from growing into a DSL. Three cost centres mean enough seeded requisitions to keep each populated. And the coverage table is a maintenance burden of its own: every person added to the cast has to earn a line in it, which is the point, and will feel like friction the first time it bites.

**Input to other tickets.**

- **#7 (authorization server)** must choose one that accepts imported user identifiers, and must be able to issue narrow-scope tokens to the same user, since the matrix varies scope independently of person.
- **#8 (what performs the run)** is unconstrained: per-row fixtures work identically in-process and over the wire.
- **#9 (attack suite)** gains nothing new here; the capability-hole row belongs to the matrix, not the suite.
- **#11 (scope granularity)** inherits four role names and every scope string as placeholders.
- **#12 (module boundaries)** inherits a seam: the seed generator reads the matrix, and the policy function reads neither.
- **#15 (demo walkthrough)** gets a cast with stated justifications and no stable ordering.
- **Audit trail** (map, not yet specified) inherits the timestamp question with a blank page.

**Not contradicted:** ADR-0001. Nothing here binds ERP context at connection time; roles and cost centre are resolved per request from the token's subject.

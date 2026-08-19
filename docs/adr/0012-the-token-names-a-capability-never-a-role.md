# ADR-0012: The token names a capability, never a role

- **Status:** Accepted
- **Date:** 2026-08-16
- **Ticket:** [#11 Settle scope granularity and naming](https://github.com/marcosfsousa/mcp-erp/issues/11)
- **Evidence:** [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md), [ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md), [ADR-0007](0007-the-realm-is-the-exhibit.md); map constraints #2, #3, #10; RFC 6749 §3.3, RFC 6750 §3, RFC 9728

## Question

Coarse scopes or resource-shaped scopes, and what are they called?

Deferred while charting because what an authorization server can practically issue, and how it presents consent, constrains the answer. [#7](https://github.com/marcosfsousa/mcp-erp/issues/7) has since chosen Keycloak and settled the realm's shape, so the constraint is now known rather than guessed at.

The trap the ticket named: **if scopes end up isomorphic to roles, the intersection model degenerates** and the headline argument of the write-up weakens. A token that says `requisition:approve` while the ERP says `approver` is not demonstrating an intersection; it is demonstrating the same fact twice.

## Decision

### Three scopes, coarse and flat

```
erp.read     list_requisitions, get_requisition
erp.write    submit_requisition, record_invoice
erp.decide   approve_requisition
```

Granularity lives almost entirely on the role side, which is what keeps scope plainly a ceiling and role plainly the detail.

**The scopes do not imply one another.** A token's scope set is a plain set; the `tools/list` filter is membership and nothing else. All 2³ = 8 subsets are legal, including `{erp.decide}` without `erp.read` — a caller who may approve a requisition but may not list one. Both directions of the ceiling stay expressible, and no authorization rule hides inside string parsing.

The wart is real and kept: an approve-only caller cannot discover the identifiers it is entitled to act on. That is honest OAuth behaviour, not a defect to design around, and the ladder below never issues that set outside the one row that exists to prove membership is not implication.

**Why `erp.decide` rather than a resource-shaped set.** Resource-shaped scopes (`requisition:approve`, `invoice:record`) map closer to the tool set, and dropping one hides exactly the tool it names. They also twin two of four role names, and the token starts restating the role model. Under coarse verbs, precision is not lost — it moves to the side that can carry it. `erp.write` covers both `submit_requisition` and `record_invoice`, and the ERP role decides which of the two the caller actually reaches. That is the intersection doing visible work rather than being asserted.

### `decide`, not `approve`

[ADR-0007](0007-the-realm-is-the-exhibit.md) bars domain vocabulary from the access token: putting `unlimited_approver` on the wire would make the *token contract itself* domain-shaped, so that cloning this repository for another purpose leaves the wire format still talking about purchasing. `read` and `write` are domain-free by any reading. **`approve` is not** — it is a purchase-to-pay act, and it is the same objection ADR-0007 raised against the role name.

[ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md) does pre-license some of this — *"scope strings are inevitably domain-shaped, so the portable part is the scheme"* — so this was arguable rather than contradictory. It is argued here rather than absorbed.

There was a clean escape and it is taken. `approve_requisition` does not only approve: [ADR-0002](0002-refusal-shape-follows-the-remedy.md) gives it `decision: "approve" | "reject"`, and ADR-0003's terminal-state reason is already `already_decided`. **`decide` is both more accurate about the tool's contract and domain-free.** The purchase-to-pay meaning survives in Keycloak's per-scope consent screen text, which is a display field and never appears on the wire.

### The scheme is constructed, never parsed

```
scope_for(capability) = f"{namespace}.{capability}"
```

Each tool declares one **capability** — `read`, `write` or `decide`. Layer 2 owns the vocabulary, the join, and the comparison. Three things derive from that single declaration and are never hand-maintained: the `tools/list` filter, `scopes_supported` in the protected resource metadata (RFC 9728, RECOMMENDED), and the `scope` parameter of the `403` challenge ADR-0002 specifies (RFC 6750 §3).

| Tool | Capability | Scope |
| --- | --- | --- |
| `list_requisitions` | `read` | `erp.read` |
| `get_requisition` | `read` | `erp.read` |
| `submit_requisition` | `write` | `erp.write` |
| `record_invoice` | `write` | `erp.write` |
| `approve_requisition` | `decide` | `erp.decide` |

**The capability is not the policy function's `action`.** `submit_requisition` and `record_invoice` share `erp.write` but differ on whether `invoice_clerk` is required, so the policy function keeps receiving the tool's own identity. The capability answers *what must the token carry*; the tool identity answers *what may this caller do with it*. Collapsing them would put the role check on the listing path and fold ADR-0002's middle denial class into its first — the collapse that ADR is mostly about refusing.

**Dot, not colon.** A colon is the URI scheme delimiter, so `erp:read` is a syntactically valid URI with scheme `erp`. In an exhibit where RFC 8707 resource indicators and `aud` values are genuine URIs, and where a reader is watching for exactly that confusion, the ambiguity is not worth the continuity with ADR-0002's placeholder strings. URI-shaped scopes were rejected outright: #7 made the audience value environment-dependent by design, so a URI-shaped scope would change between Compose and anywhere else, and register deviation 2's plain-HTTP problem would spread from the audience into the scope vocabulary.

**Layer 2 constructs strings and never parses one.** Nothing splits a scope on `.`, and nothing inspects a namespace. This is what keeps the prefix a naming convention for humans and metadata rather than a structure the server depends on.

### Unrecognised scopes are inert

The check is **exact, case-sensitive set membership** against the three known strings. Case sensitivity is not ours to choose — RFC 6749 §3.3: *"The value of the scope parameter is expressed as a list of space-delimited, case-sensitive strings."*

Every token will carry at least one string we did not define: `openid` at minimum, the decoy's `hr.read`, and the audience-bearing client scope's name where it is included in token scope. `erp.admin`, `ERP.READ` and `hr.read` are all inert for exactly the same reason `openid` is — they are not in the set. There is no unknown-scope code path, no namespace awareness, and nothing to fingerprint.

This mints one attack-suite row, `scope_exact_match`, whose removal is *"replace exact case-sensitive set membership with any laxer comparison."* It carries `basis: adr` and `normative_strength: null`, because RFC 6749 §3.3's sentence is definitional and contains no normative keyword — the table forbids a row asserting a strength its quote does not contain. The RFC rides in the `context` field, which exists for *"a real clause that is NOT the basis… where one exists but governs a different party."* §3.3 governs how the authorization server represents the scope parameter, not how a resource server compares it. The fit is precise rather than convenient.

### Issuance: one role scope mapping, listing two roles

**`erp.decide` is the only scope carrying a role scope mapping, and the mapping lists both `approver` and `unlimited_approver`.** `erp.read` and `erp.write` carry none.

Role-gating `erp.write` at issuance was never available: ADR-0003 gates submitting by **scope alone, no role**, so a mapping there would lock every submitter out of a scope they are entitled to. Leaving it ungated is not a concession — it is what makes the intersection visible on `record_invoice`, where the scope is handed out freely and `invoice_clerk` decides whether it achieves anything.

The mapping lists two roles because [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md)'s cast gives **Ingrid Holm** `unlimited_approver` and `invoice_clerk` and *not* `approver`. A single-valued mapping on `approver` would mean her token never carries `erp.decide`, `approve_requisition` would be unlisted for her, and *"approves above threshold"* — the branch she exists to make reachable — would be unreachable, taking edge 2 negative with it. ADR-0007 documents that a role scope mapping expresses exactly *"holds at least one of these roles"*, so listing both uses the mechanism as designed, invents no realm state, and keeps **Priya Raman the only person whose Keycloak roles and ERP roles disagree**.

**This strengthens the isomorphism argument rather than complicating it.** `erp.decide` now maps from two roles that differ on precisely the authority a scope cannot express — the threshold — so **the scope twins no role name at all**. The count of collisions between the scope vocabulary and the role vocabulary is zero, not one:

| | Expressible as a scope | Expressible as a role |
| --- | --- | --- |
| May reach the deciding tool | yes | — |
| May decide at or below €5,000 | no | `approver` |
| May decide at any amount | no | `unlimited_approver` |
| May record invoices | no | `invoice_clerk` |
| May read across cost centres | no | `auditor` |

Priya's drift row survives untouched: she holds `approver` in Keycloak and no role in the ERP, so her token carries `erp.decide` and the call refuses with `-31010`, which is the state ADR-0002's middle denial class needs and which a `403` would lie about.

### Consent is required on all four clients

Each capability scope carries consent screen text; the audience-bearing default client scope has *Display on consent screen* off, because it is infrastructure rather than a permission. The screen therefore shows exactly three lines:

> - Read purchase requisitions in your cost centre
> - Raise requisitions and record invoices on your behalf
> - Approve or reject purchase requisitions on your behalf

The consent screen is the only place a human ever sees the three capabilities rendered as a delegation choice, and it is where the exhibit's central claim stops being asserted and becomes visible. The cost is one more form post in a headless client that already posts Keycloak's login form, since ADR-0007 disables direct access grants on every client.

**A limitation stated rather than discovered.** Keycloak's consent screen is grant-or-deny for the whole request; it does not let a person deselect individual optional scopes. The screen therefore **displays** the ceiling and does not let the person narrow it. Narrowing happens in the client's `scope` parameter. Flagged for assertion at build time rather than trust, alongside the exact semantics of *Include in token scope*, on which two readings of Keycloak's own documentation disagree.

### The working set of token shapes

ADR-0007 defines the matrix principal as *person × scope set*. Three flat scopes bound that axis at eight by construction, which across seven people is 56 principals before tools or resources enter. The hard ceiling is structural; the working ceiling is a rule.

**Four cumulative sets are the spine.** A non-cumulative set is admitted only by citing the row that requires it, and every admission is recorded here.

| Set | Reaches | Exists to make reachable |
| --- | --- | --- |
| `{}` | nothing | `tools/list` returns empty; absence is the fourth refusal |
| `{erp.read}` | 2 tools | row scoping; the read-only ceiling |
| `{erp.read, erp.write}` | 4 tools | may draft, may never approve — the delegation story |
| `{erp.read, erp.write, erp.decide}` | all 5 | threshold, segregation of duties, the full path |

**Admitted exceptions**

| Set | Admitted by |
| --- | --- |
| `{erp.decide}` | `tools/list` purity — proves membership alone, with no implication between scopes |

Anything beyond this table needs a named row before it exists.

### Role names ratified, with one rename

`senior_approver` becomes **`unlimited_approver`**. The role was never about seniority: ADR-0003 has to explain in a parenthetical that it *"has no upper limit, so it covers small requisitions too and nobody needs to hold both."* A name needing that gloss every time it appears is doing poorly, and the new one states the property directly.

`approver`, `invoice_clerk` and `auditor` are ratified unchanged, and CONTEXT.md's *"Current names are provisional"* is removed.

**`approver` names both a role and a position, deliberately.** CONTEXT.md defines **Approver** as a position — occupied once, by one Person, on one chain — expressly distinct from a role, which is held standing. The pairing is now stated at the glossary entry rather than left for a reader to resolve, because segregation of duties is checked against the position and never against the role.

**A clarifying clause the capability split makes visible.** ADR-0003's cast says the `auditor` role *"reads 3 of 3, writes nothing"*. That describes the **role**, which confers no write authority — not Anna Lindqvist's reachable surface. Submitting is gated by scope alone, so a token carrying `erp.write` lets her raise a requisition against her own cost centre like anyone else. The two statements were always compatible; separating capability from role is what makes the distinction legible, so it is recorded rather than left to be rediscovered.

### The scope scheme is a portable pattern

This answers the question map constraint #10 and ADR-0004 routed here in as many words.

**Layer 2 owns** the shape, the construction rule, exact case-sensitive comparison, metadata derivation, and the three capability words as a fixed set with an extension point for a domain needing a fourth. **Layer 3 supplies** only the namespace token `erp`, and which tool declares which capability. That single token is the one domain-shaped part, which is exactly what ADR-0004 predicted was unavoidable.

Falsified the way ADR-0004 requires: **deleting the layer-3 module leaves layer 2 building, the capability vocabulary intact, `scopes_supported` rendering empty, and layer 2's own tests passing.**

The choice of `decide` is what makes this claim honest rather than aspirational — it beat `approve` precisely because all three words survive ejection. Had `approve` won, the vocabulary would have been layer 3 wearing a layer-2 label.

### One open verification item

The role scope mapping above deliberately manufactures the situation RFC 6749 §3.3 governs: a person without `approver` or `unlimited_approver` requests `erp.decide` and silently does not receive it, because Keycloak omits an unpermitted scope and the flow succeeds. That behaviour is itself conformant — the same section says the authorization server *"MAY fully or partially ignore the scope requested by the client"* — so it is a property of the design, not a Keycloak quirk.

But the narrowing triggers a `MUST`:

> If the issued access token scope is different from the one requested by the client, the authorization server **MUST** include the "scope" response parameter to inform the client of the actual scope granted.
>
> — RFC 6749 §3.3, retrieved 2026-08-16

**Whether Keycloak honours this on the authorization code flow is unverified.** The issues found ([keycloak#29614](https://github.com/keycloak/keycloak/issues/29614), [keycloak#30704](https://github.com/keycloak/keycloak/issues/30704)) concern token exchange and refresh, not our path, and do not settle it.

The conformance client compares the `scope` response parameter against what it requested and reports any silent narrowing. The outcome is decided by observation and **not pre-committed here**: if Keycloak honours the `MUST`, the exhibit gains a conformance proof and no register row; if it does not, this becomes **a normative register row of its own**, in the same shape as the RFC 8707 finding ADR-0005 already carries. *(Number dropped 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which took row 6 for an unrelated interpretation before this one was ever observed. Reserving a register row by number reserves nothing: the register assigns numbers on creation, and two documents claimed the same one within a fortnight. Register rows are cited by what they say from here on.)* Writing the row now would record a gap nobody has observed, in a document whose entire value is being trustworthy.

## Options considered

1. **Resource-shaped scopes** — `requisition:read`, `requisition:submit`, `requisition:approve`, `invoice:record`. Dropping one scope hides exactly the tools it names, which is the sharpest possible `tools/list` demonstration. Rejected: two of four twin a role name, the token begins restating the role model, and the precision bought is precision the role side already carries.
2. **One scope per tool.** Maximally precise and trivially mechanical. The token becomes a copy of the tool catalogue, the consent screen becomes an implementation detail, and scope stops reading as a ceiling at all.
3. **Two verbs, `erp.read` and `erp.write`,** with approving folded into writing. Zero name collisions with the role set — the strongest anti-isomorphism position available. Rejected because it costs the token that may submit but never approve, which is the single most legible delegation story this domain offers, and leaves the ceiling demonstrable only as read-only.
4. **A cumulative ladder** where `erp.decide` implies `erp.write` implies `erp.read`. One line on the consent screen and only four meaningful tokens. Rejected: the ceiling collapses to one dimension, "may approve but not submit" becomes inexpressible, and a single scope naming a privilege level is a role wearing a scope's clothes.
5. **`erp.read` as an implicit floor** on every token, removing the approve-without-read wart. Rejected: a scope that is never absent proves nothing, and the wart is a true statement about set-valued scopes rather than a defect.
6. **Refusing a request whose token carries an unrecognised `erp.`-prefixed scope**, as a configuration-drift signal. Rejected: it requires parsing the prefix, makes a realm edit able to break a running server, and hands an attacker an oracle for discovering which `erp.*` names exist.
7. **The policy function owning the tool-to-scope mapping**, with a scope-only calling mode for listing. Rejected: it reintroduces roles onto the listing path, where ADR-0002's three denial classes can collapse to two by accident.
8. **A composite Keycloak role gating `erp.decide`.** Behaviourally identical to listing two roles, and it adds a Keycloak concept the realm does not otherwise use — a fourth thing to explain in a file ADR-0007 says is read as evidence.
9. **Giving Ingrid Holm the `approver` realm role** so the mapping could stay single-valued. Rejected: it makes a second person's Keycloak and ERP roles disagree, and a reader comparing the two sets then finds two mismatches with only one of them meaningful.
10. **Consent off, or on a fifth demonstration client.** Off makes the ceiling legible in a trace and invisible to a person. A fifth client keeps continuous integration untouched but means the walkthrough exercises a client the attack suite never does, in a realm whose ADR gives each of four clients one stated job.

## Consequences

**Cost.** A vocabulary indirection — capability, scope string, role, position — in a repository whose product is being readable, and a glossary that now has to hold `Capability` and `Role` apart in the reader's head. The headless conformance client picks up a consent-form post on the job that gates merges. Three ADRs take amendments. And `erp.write` covering two tools means the write ceiling can never be narrowed without reopening this document.

**What it buys.** The scope vocabulary and the role vocabulary now collide on **zero** names, so the intersection cannot degenerate into saying one fact twice — the trap the ticket was opened to avoid. The scheme is the second layer-2 artifact with a falsifiable portability claim. And the consent screen turns the exhibit's central argument into something a reader sees rather than something the write-up asserts.

**Build notes, since no such artifact exists.** Two steps that must not be discovered on 18.08: the headless conformance client posts a consent form as well as a login form, and asserts requested-versus-granted scope on the token response. Tiers 2 and 3 are browser-driven and gain a human click, which is a demonstrative gain. The attack suites are unaffected — ADR-0008 mints their tokens directly — as is ADR-0004's in-process ejection test. Keycloak state is fresh on every boot, so continuous integration always takes the first-consent path, which makes it deterministic rather than sometimes-remembered.

**Input to other tickets.**

- **[#12](https://github.com/marcosfsousa/mcp-erp/issues/12) (module boundaries)** inherits the layer split above as a sixth acceptance criterion alongside ADR-0004's five: the capability vocabulary, the join rule, the comparison and the metadata derivation are layer 2; the namespace token and the per-tool declarations are layer 3. The ejection test now has a scope-shaped assertion.
- **[#15](https://github.com/marcosfsousa/mcp-erp/issues/15) (demo walkthrough)** inherits the consent screen as a scripted beat, and the working-set ladder as the token shapes the walkthrough may use.
- **The decision matrix** inherits the four-set ladder and the rule that any further scope set must cite the row admitting it. The matrix remains unprotected, as ADR-0010 recorded.

**Not contradicted:** ADR-0002's three denial classes, all of which survive intact — absence from `tools/list`, `403` with `insufficient_scope`, and `-31010` for scope-without-role. ADR-0004's ejection test, which gains an artifact rather than an exception. ADR-0007's suppression of roles from the wire, which this document extends from claims to scope strings.

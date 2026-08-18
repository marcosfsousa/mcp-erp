# ADR-0002: Refusal shape follows the remedy

- **Status:** Accepted
- **Date:** 2026-08-06
- **Ticket:** [#5 Design the tool surface](https://github.com/marcosfsousa/mcp-erp/issues/5)
- **Evidence:** MCP `2026-07-28` [tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [caching](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/caching), [basic/index](https://modelcontextprotocol.io/specification/2026-07-28/basic/index), [authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization); [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md)
- **Amended:** 2026-08-12 — substantive, by [#6](https://github.com/marcosfsousa/mcp-erp/issues/6). `already_approved` becomes `already_decided` and `already_invoiced` joins the closed vocabulary; the multi-cost-centre question this ADR handed on is answered *no*. Recorded in [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md) *§Consequences* at the time and back-amended here 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12). See *Surviving contact with a retrying client*. No decision here is reversed.
- **Amended:** 2026-08-11 — substantive, by [#7](https://github.com/marcosfsousa/mcp-erp/issues/7). The stated evidence for the unlisted-tool rule is wrong — RFC 9728 publishes no tool names. The rule survives on repaired reasoning, recorded in [ADR-0006](0006-fail-closed-in-a-fixed-order.md) *§The gate order is a security property* and back-amended here 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12). See *Disclose the shape of the API*. No decision here is reversed.
- **Amended:** 2026-08-18 — substantive, by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12). The closed reason vocabulary is **split by layer**; the indistinguishability claim narrows to **byte-identity, with constant time explicitly not measured**; the `ttlMs` proof gains the invariant it depends on. See *Surviving contact with a retrying client*, *Disclose the shape of the API*, *Transport* and *`tools/list`*. No decision here is reversed.

## Question

What tools does the server expose, what are their contracts, and — the substance — what does each of the three denial classes look like on the wire, given an LLM client that will try to retry its way past all of them?

## Decision

### Five tools

| Tool | Kind | Earns its place by |
| --- | --- | --- |
| `submit_requisition` | write | Binding the submitter identity that segregation of duties later tests against |
| `approve_requisition` | write | Tier-1 visibility, tier-3 threshold, tier-3 segregation of duties |
| `record_invoice` | write | The segregation-of-duties counterparty |
| `list_requisitions` | read | Row scoping by cost centre — same tool, same scope, different rows |
| `get_requisition` | read | Existence-vs-permission at single-row granularity |

`PurchaseOrder` is emitted as a side effect of approval and has **no tool of its own**; it is the record that carries the approver identity and cost centre forward for the invoice to match against. `Vendor` has no tool either — its legal values are a JSON Schema `enum` of names inside `submit_requisition`, so the tool definition *is* the lookup. `approve_requisition` takes a list and a `decision: "approve" | "reject"`; rejection is the same authorization decision as approval, so a separate tool would add a `tools/list` row without adding an authorization behaviour.

Every read tool cut — `list_vendors`, `get_vendor`, `list_invoices`, `list_purchase_orders` — was cut for the same reason: it demonstrated no authorization behaviour the surviving two do not.

### Schema shape

Opaque prefixed handles (`req_`, `po_`, `inv_`) as the only identifiers; cost centre as a readable code (`CC-4100`), never a surrogate id; amount as a decimal string plus explicit `currency`; enums as lowercase string literals; references as `{id, label}` pairs, nesting one level deep at most. `outputSchema` is declared on every tool, and results carry both `structuredContent` and a serialized text rendering — the spec asks for the latter, and the two halves have different audiences: the matrix asserts on the structured half, the model reads the text.

The rule behind the shape: **authorization is decided on cost centre, amount, and two identities**, so those four are first-class and unambiguous; everything else flattens.

`submit_requisition` takes **no cost centre** — the requisition is stamped with the submitter's own. A cross-cost-centre submission is therefore inexpressible rather than merely refused, and no schema anywhere enumerates the organisation's cost centres.

### Refusals

Three shapes, keyed on **what would actually fix this for the caller**:

| Situation | Wire | Remedy |
| --- | --- | --- |
| Scope absent, tool called anyway | `403` + `WWW-Authenticate: Bearer error="insufficient_scope", scope=…, resource_metadata=…` | Re-authorize |
| Scope present, ERP role absent | JSON-RPC error `-31010` | An administrator grants the role |
| Domain rule violated | Tool result, `isError: true`, with `structuredContent` | A different person acts |

(The fourth situation — no scope, tool never called — is simply absence from `tools/list`.)

This maps onto the spec's own division of labour. Protocol errors are for "issues with the request structure itself that **models are less likely to be able to fix**"; tool execution errors are "actionable feedback that language models can use to **self-correct and retry**". Clients **MAY** surface the former to a model and **SHOULD** surface the latter. A missing ERP role is precisely not model-fixable; a segregation-of-duties refusal is precisely something the model should act on by routing elsewhere. The channels already encode the distinction we need.

**A `403` on the missing-role case would be a lie.** It carries a `WWW-Authenticate` header instructing the client to acquire a scope it already holds, which produces an identical token and an identical refusal — a loop.

### Two rules that fell out and generalise

**Caller-level refusals are whole-call; item-level refusals are per-item.** Because `approve_requisition` is a batch, a refusal that depends on the *caller* (missing scope, missing role) cannot ride in the result — it replaces the whole response. A refusal that depends on the *item* (not found, over threshold, segregation of duties) must. The batch did not break the three-way split; it exposed the axis the split was already using.

**Disclose the shape of the API; never the contents of the database.** An unlisted tool called anyway returns a `403` naming the tool and the scope, because tool names and scope names are already published unauthenticated in the protected-resource metadata — the refusal discloses nothing new. A requisition in another cost centre returns `not_found`, byte-identical to a requisition that never existed, because its existence and its cost centre are facts only the database holds. The catalogue is public; the rows are not.

*Amended 2026-08-11 by [#7](https://github.com/marcosfsousa/mcp-erp/issues/7) and 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12).* Two corrections to the paragraph above.

**The unlisted-tool justification was wrong.** It read *"tool names and scope names are already published unauthenticated in the protected-resource metadata."* **RFC 9728 has no field publishing tool names**, and `tools/list` requires a token. The reasoning survives; the stated evidence does not. The repaired claim, from [ADR-0006](0006-fail-closed-in-a-fixed-order.md): the refusal names a **scope** genuinely published in `scopes_supported`, and confirms a **tool name the caller themselves supplied**. Neither is a fact only the database holds.

**The indistinguishability claim read *"timing included"*, and is narrowed to byte-identity.** Timing indistinguishability is not provable at either altitude this project tests at, and least of all over HTTP against Compose, where container scheduling and garbage collection swamp the signal; a measured-timing assertion flakes and a flaky assertion gets disabled. What is provable, and what is now claimed: the two paths converge on a **single return site** in layer 2 (asserted structurally, in `tests/authorization/`), and the response is **byte-identical** on the wire (asserted by `row_probe_indistinguishable`). **Constant time is not measured and is not claimed.** This reverses a project commitment, not a normative obligation, so it owes no normative-register row. See [ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md) *§Indistinguishability is byte-identity, at two altitudes*.

### Surviving contact with a retrying client

*Amended 2026-08-12 by [#6](https://github.com/marcosfsousa/mcp-erp/issues/6) and 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12).*

Every refusal carries a closed vocabulary the decision matrix asserts on. It was written here as one flat list; [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md) renamed one value and added another, and [ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md) split it by layer. The list below is the current one:

```
reason (layer 2):  insufficient_scope | role_missing | not_found
reason (layer 3):  segregation_of_duties | over_threshold
                 | already_decided | already_invoiced
remedy:  reauthorize | administrator_grant | different_person | none
retry_identical_helps:       bool
retry_as_other_person_helps: bool
```

`remedy` and both retry booleans stay wholly in layer 2 — they describe client behaviour, not domain facts. Under ADR-0013 a reason is a **record** rather than a string, each layer declaring its own instances, so this table is a description of what is declared and not a lookup anything reads.

`retry_as_other_person_helps` is the field that earns the vocabulary. "Do not retry" is right for two of the three refusals and **wrong** for segregation of duties, where retrying as a different person is the correct move. A single boolean would have flattened the one case the domain exists to demonstrate.

Signalling is not control, so the batch is also **idempotent per item**: a second decision on a decided requisition returns `already_decided` rather than minting a second purchase order. A model that ignores every field and retries the whole batch cannot double-approve.

### Transport

*Amended 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12) — the justification below is restated in layer-2 terms as **a call that yields N independent outcomes**, so it survives ejection of the domain. Layer 1 keys the response mode on outcome **cardinality**, never on the tool's name; see [ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md) §Streaming, restated portably. Nothing below changes.*

`approve_requisition` carries the SSE response mode — the only tool where streaming is earned rather than decorative, because a batch is N independent decisions with N independent outcomes. A single-item call answers with `application/json` instead, so **one tool exercises both response modes**, which is a thing clients MUST support and almost nothing tests. Progress notifications are opt-in via `progressToken`, so the design still holds when the stream is empty.

### `tools/list`

Derived per request from the bearer token, with no session to cache it in. The spec names this exact case:

> The set **MAY** vary by the authorization presented on the request — for example, returning only the tools the caller's granted scopes permit — since credentials are per-request input, not connection state.

Filtering is on **granted scope alone**; ERP role is a call-time check. Filtering on the intersection would be marginally friendlier and would collapse the missing-role denial class into the missing-scope one, destroying the distinction this ADR is mostly about.

- `cacheScope: "private"` — forced. The spec warns that a `"public"` result from an authenticated endpoint "may be shared between callers", i.e. across access tokens. A scope-filtered listing marked public is a cross-principal leak.
- `ttlMs = min(300000, milliseconds until the token expires)`. Because the listing filters on scope alone, it is a **pure function of the access token**: new scopes mean a new token, which is a different cache key under `private`. The cache therefore *cannot* serve a listing that misrepresents the caller's scopes. The 5-minute cap covers the only other input — which tools are deployed.

  *Amended 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12) — the invariant this proof rests on, now that it has a named implementation.* [ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md) makes the filter `permits_scope(principal, action)`, and a `Principal` is **directory-derived**. The purity argument above survives only while `permits_scope` reads **token-derived fields exclusively** — issuer, subject, granted scopes — and never roles or partition. The tempting future change is a role check on listing, reasoning *why list a tool they will be refused on?*; it would make a directory revocation invisible for up to five minutes on an unchanged token, and nothing in the code would object. **If `permits_scope` ever reads a directory-derived field, this `ttlMs` argument must be re-derived.**
- `listChanged: false`. `notifications/tools/list_changed` announces that the *server's* tool set changed; ours is five tools fixed at deploy. What varies is per-caller, which the notification cannot express. Declaring it would also require `subscriptions/listen`, a second streaming endpoint against map constraint #6.

## Options considered

1. **Collapse missing-scope and missing-role into one `403`.** Simplest to explain and wrong in the exact way the exhibit exists to show — see the retry loop above.
2. **Make every refusal a tool result.** Maximally legible to a model, but the OAuth layer then never sees an authorization failure, so a client never re-authorizes even when that is the correct move, and attack-suite clause #6 has nothing to fire on.
3. **Explicit `row_out_of_scope` on `get_requisition`.** Would make row scoping visible at single-row granularity. Rejected: it turns the read scope into an identifier-enumeration and cost-centre-mapping primitive — a textbook finding, in front of the exact reader this exhibit targets.
4. **Stream the policy tiers instead of a batch.** A lovely teaching artifact, but the policy function is one pure call over in-memory data; streaming it is visualisation, not transport. The narration survives as `structuredContent` and as the audit trail, which need no stream.
5. **Cut SSE entirely** (it is #3 in the map's cut order). Rejected while a genuine justification exists: having exactly one stream is what makes the write-up's refusal of a *standalone* stream a design position rather than an absence.
6. **Reinstate `list_vendors`.** Demonstrates no authorization behaviour. It is there because a real ERP would have one, which is the reasoning the map's governing rule exists to reject.

## Consequences

**A correction to carry.** The role-denied code is `-31010`, not a value in `-32000…-32019`. That sub-range is **legacy** — "New codes **MUST NOT** be allocated in this sub-range" — and new application codes **SHOULD** be allocated outside the reserved range `-32768…-32000` entirely. Any implementation reaching for the "implementation-defined" JSON-RPC range under this revision is wrong.

**Cost.** Per-item idempotency is real work with real state. The remedy vocabulary is a fifth thing that must stay honest as the domain grows. Three refusal code paths need three tests, and a reviewer must be told *why* they differ or the design reads as inconsistency.

**Acknowledged limit.** Enumerating vendors in the input schema does not survive past a few dozen vendors; at ERP scale it needs a lookup tool. We have four. This is stated so a reader finds it acknowledged rather than missed.

**Input to other tickets.**

- **#9 (attack suite)** inherits five named scenarios: `retry_after_role_denial`, `retry_after_sod_denial_same_person`, `retry_after_sod_denial_other_person`, `row_probe_indistinguishable`, `double_approval_via_batch_retry`.
- **#11 (scope granularity)** — ~~every scope string here (`erp:requisition:read|submit|approve`, `erp:invoice:record`) is a placeholder, as are the role names (`approver`, `senior_approver`, `invoice_clerk`)~~. *Closed 2026-08-16 by [ADR-0012](0012-the-token-names-a-capability-never-a-role.md).* The scopes are **`erp.read`, `erp.write`, `erp.decide`** — coarse, flat, and constructed from a capability each tool declares. The `403` challenge above quotes them in its `scope` parameter. Role names are ratified with one rename: `senior_approver` becomes **`unlimited_approver`**.
- **#6 (data model)** owns whether a person can hold more than one cost centre. If they can, `submit_requisition` regains a `cost_centre` input and the question of how the model learns its legal values reopens.
- **#12 (module boundaries)**, which this ticket blocks, inherits a clean seam: the policy function returns a `reason`, and three separate adapters render it as a `403`, a JSON-RPC error, or a tool result. The refusal *decision* and the refusal *shape* are different concerns.

**Not contradicted:** ADR-0001. The `tools/list` derivation depends on no connection state, consistent with its finding that ERP context must not be bound at connection time.

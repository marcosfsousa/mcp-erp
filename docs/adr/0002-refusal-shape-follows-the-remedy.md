# ADR-0002: Refusal shape follows the remedy

- **Status:** Accepted
- **Date:** 2026-08-06
- **Ticket:** [#5 Design the tool surface](https://github.com/marcosfsousa/mcp-erp/issues/5)
- **Evidence:** MCP `2026-07-28` [tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [caching](https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/caching), [basic/index](https://modelcontextprotocol.io/specification/2026-07-28/basic/index), [authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization); [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md)

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

**Disclose the shape of the API; never the contents of the database.** An unlisted tool called anyway returns a `403` naming the tool and the scope, because tool names and scope names are already published unauthenticated in the protected-resource metadata — the refusal discloses nothing new. A requisition in another cost centre returns `not_found`, byte-identical to a requisition that never existed, timing included, because its existence and its cost centre are facts only the database holds. The catalogue is public; the rows are not.

### Surviving contact with a retrying client

Every refusal carries a closed vocabulary the decision matrix asserts on:

```
reason:  insufficient_scope | role_missing | segregation_of_duties
       | over_threshold | not_found | already_approved
remedy:  reauthorize | administrator_grant | different_person | none
retry_identical_helps:       bool
retry_as_other_person_helps: bool
```

`retry_as_other_person_helps` is the field that earns the vocabulary. "Do not retry" is right for two of the three refusals and **wrong** for segregation of duties, where retrying as a different person is the correct move. A single boolean would have flattened the one case the domain exists to demonstrate.

Signalling is not control, so the batch is also **idempotent per item**: approving an already-approved requisition returns `already_approved` rather than minting a second purchase order. A model that ignores every field and retries the whole batch cannot double-approve.

### Transport

`approve_requisition` carries the SSE response mode — the only tool where streaming is earned rather than decorative, because a batch is N independent decisions with N independent outcomes. A single-item call answers with `application/json` instead, so **one tool exercises both response modes**, which is a thing clients MUST support and almost nothing tests. Progress notifications are opt-in via `progressToken`, so the design still holds when the stream is empty.

### `tools/list`

Derived per request from the bearer token, with no session to cache it in. The spec names this exact case:

> The set **MAY** vary by the authorization presented on the request — for example, returning only the tools the caller's granted scopes permit — since credentials are per-request input, not connection state.

Filtering is on **granted scope alone**; ERP role is a call-time check. Filtering on the intersection would be marginally friendlier and would collapse the missing-role denial class into the missing-scope one, destroying the distinction this ADR is mostly about.

- `cacheScope: "private"` — forced. The spec warns that a `"public"` result from an authenticated endpoint "may be shared between callers", i.e. across access tokens. A scope-filtered listing marked public is a cross-principal leak.
- `ttlMs = min(300000, milliseconds until the token expires)`. Because the listing filters on scope alone, it is a **pure function of the access token**: new scopes mean a new token, which is a different cache key under `private`. The cache therefore *cannot* serve a listing that misrepresents the caller's scopes. The 5-minute cap covers the only other input — which tools are deployed.
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

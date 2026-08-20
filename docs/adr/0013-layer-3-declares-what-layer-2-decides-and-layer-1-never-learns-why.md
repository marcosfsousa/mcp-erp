# ADR-0013: Layer 3 declares what layer 2 decides, and layer 1 never learns why

- **Status:** Accepted
- **Date:** 2026-08-18
- **Ticket:** [#12 Settle module boundaries](https://github.com/marcosfsousa/mcp-erp/issues/12)
- **Evidence:** map constraints `#1`, `#4`, `#6`, `#7`, `#10`, `#12`; [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md), [ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md) (which handed this ticket five acceptance criteria and four tabled couplings), [ADR-0006](0006-fail-closed-in-a-fixed-order.md), [ADR-0007](0007-the-realm-is-the-exhibit.md), [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md), [ADR-0009](0009-not-built-is-not-unreachable.md), [ADR-0010](0010-the-clause-decides-the-row-the-removal-decides-the-split.md), [ADR-0012](0012-the-token-names-a-capability-never-a-role.md)
- **Amended:** 2026-08-18 — substantive, by [#32](https://github.com/marcosfsousa/mcp-erp/issues/32). `Mount` becomes `Route`, and the accepted cost on exception handling is withdrawn. See *The gate chain sits in middleware, in two tiers*. No decision here is reversed. *(Header added 2026-08-18 by [#34](https://github.com/marcosfsousa/mcp-erp/issues/34); the in-body marker has stood since the amendment landed.)*
- **Amended:** 2026-08-18 — additive, by [#34](https://github.com/marcosfsousa/mcp-erp/issues/34). `Rule` and `Action` are **parameterised on the resource type** as built. See *The `Action` is the seam*. No decision here is reversed.
- **Amended:** 2026-08-18 — additive, by [#35](https://github.com/marcosfsousa/mcp-erp/issues/35). The seed's third rendering needs a generator of its own, so there are **three generators, not two**, and layer 3 holds two of them: the organisation renderer beside the fixture generator. See *Both generators, split by the vocabulary each speaks*. The rule that decides where each lives is unchanged, and no decision here is reversed.
- **Amended:** 2026-08-19 — additive, by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which built the chain. **Gate 5 runs in middleware, not at dispatch**, because its wire shape is an HTTP status and header that a JSON-RPC envelope cannot carry; gate 6 stays at dispatch. And there is a **fifth test directory**, `tests/wire/`, for the wire assertions that belong to no proof artifact. See *The gate chain sits in middleware, in two tiers* and *Test directories, named for artifacts*. No decision here is reversed.
- **Amended:** 2026-08-19 — substantive, by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37). [ADR-0002](0002-refusal-shape-follows-the-remedy.md) cut the SSE response mode, so **response mode is no longer keyed on cardinality — there is one wire shape.** N outcomes **fold** into one result body; the fold is specified here and **not implemented**, and [#41](https://github.com/marcosfsousa/mcp-erp/issues/41) lands it. See *Streaming, restated portably*. This reverses the cardinality keying and nothing else.
- **Amended:** 2026-08-19 — additive, by [#39](https://github.com/marcosfsousa/mcp-erp/issues/39), which built the second and third tools. A handler's third answer — **an argument its own declaration forbids** — is signalled with `ValueError` and rendered as `-32602`, and is deliberately **not** a fourth denial class. And a tool's declaration is **one module per tool** inside layer 3. See *Handlers in layer 3, adapters in layer 1* and *Three sibling packages, one composition root*. No decision here is reversed.
- **Amended:** 2026-08-19 — additive, by [#40](https://github.com/marcosfsousa/mcp-erp/issues/40), which built the first hydrated resource. `load` is built as a **factory binding the store**, so the step's own signature is this document's two parameters and nothing is injected into the chain. And a handler has a **domain precondition** to answer as well as a decision — it constructs a refused `Decision` layer 2 never produced, *after* the chain permits and *at* the write. See *Resource hydration is a named layer-3 step* and *Handlers in layer 3, adapters in layer 1*. No decision here is reversed.
- **Amended:** 2026-08-20 — additive, by [#41](https://github.com/marcosfsousa/mcp-erp/issues/41), which built the first batch. **The fold is implemented**, which settles the two things this document deliberately left open — what holds the N answers, and what `isError` means when some items refused — and surfaces one obligation nothing had stated: a handler deciding more than one item **must settle the call before its first item**, because a caller-level refusal has no rendering inside a result body. `tests/wire/` additionally holds **one assertion that is not over HTTP**. See *Streaming, restated portably* and *Test directories, named for artifacts*. No decision here is reversed.
- **Amended:** 2026-08-20 — additive, by [#42](https://github.com/marcosfsousa/mcp-erp/issues/42), which built the last of the five tools. `load` is **parameterised on the entity it hydrates**, so the `action` parameter this document kept for #42 selects a resource *through the type* and is still never read; layer 3 holds **one store per entity a tool is decided against**, over one pool. See *Resource hydration is a named layer-3 step*. No decision here is reversed.
- **Amended:** 2026-08-20 — additive, by [#66](https://github.com/marcosfsousa/mcp-erp/issues/66), which found the job table and `ci.yml` disagreeing in both directions. A **ninth job, *Server posture***, for `tests/wire/`, and a tenth row for *Published documents are immutable*, which was in the workflow and in no row. The job count is **struck rather than incremented** — it is derived from the seam enumeration, and *one per seam* is the rule. See *Continuous-integration jobs, one per seam* and *Test directories, named for artifacts*. No decision here is reversed.
- **Amended:** 2026-08-20 — additive, by [#43](https://github.com/marcosfsousa/mcp-erp/issues/43), which built the decision matrix. `docs/decision-matrix/matrix.yaml` **exists**, the fixture generator is built, and the fixtures are the seed's **fourth rendering** — so `Seed renders clean` re-renders four and its diagnosis widens from *the seed* to *the source*. The listing's filter left `tests/wire/` for `tests/matrix/`, and this document's five-assertion handoff is discharged. See *Both generators, split by the vocabulary each speaks*, *Test directories, named for artifacts* and *Continuous-integration jobs, one per seam*. No decision here is reversed.
- **Amended:** 2026-08-20 — additive, by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46), which built the authorization code flow and the job that gates it. **Two of the three imagined Compose consumers are real**, so the count the *not factored yet* argument turned on is spent: *Decision matrix (wire)* repeats the pattern step for step and *Authorization code flow* differs where the `yes + network` row predicted. The pattern stays unfactored, #44 is what would settle its shape, and the argument now lives in exactly one place after drifting in three. See *Continuous-integration jobs, one per seam*. No decision here is reversed.

## Question

What are the seams, and where does each concern live?

ADR-0004 made two properties standing constraints — layer 2 survives as a portable pattern, layer 3 detaches cleanly — and handed this ticket the criteria rather than leaving them to be inferred. The falsifiable form is that **deleting the layer-3 module leaves layer 2 building and its own tests passing**. This ADR says what the modules are, what crosses between them, and what proves it.

## Decision

**Only declarations cross a layer boundary.** Layer 3 declares an `Action` per tool and its own reason values; layer 2 decides; layer 1 renders what comes back without learning what produced it.

The title claims that declaration is all that *crosses*. It is not a claim that layer 3 is only declarations — the handlers live there too, and they are the largest thing ejection deletes.

### The policy function has one chain and three named entry points

```python
def permits_scope(principal, action) -> bool: ...             # step 1
def decide_call(principal, action) -> GateOutcome: ...        # steps 1-2
def decide_item(principal, action, resource) -> Decision: ... # steps 1-4
```

One ordered chain — scope, role, row scoping, relationship rules — evaluated in exactly one place, with three entry points naming where a caller stops. `decide_call` runs once for the whole-call gate; `decide_item` runs once per item. This is the batch shape ADR-0002 established: *"caller-level refusals are whole-call; item-level refusals are per-item."*

**`resource` carries no default.** A single `decide(principal, action, resource=None)` truncates the chain on argument absence: a handler that forgets to pass the row gets a permit indistinguishable from a real one — the class of fault ADR-0006 is named for, and the one a non-optional `Principal.partition` closed once already.

**The two entry points return different types.** `GateOutcome` is not a `Decision`, so a whole-call permit cannot be used as an item permit.

**The N+1 evaluation is deliberate.** A batch of N items evaluates steps 1 and 2 once for the call and once per item. They are pure and cheap, and paying for them keeps ADR-0006's fixed order in one implementation rather than two. A reader will otherwise file it as a defect.

**What this does not close, stated plainly.** The type split closes accidental *omission*. It does not close the wrong entry point: a handler that calls `decide_call`, receives a permit, and returns every row without ever calling `decide_item` type-checks cleanly and fails open. Nothing in a signature can force the item path to be walked.

That residual is **structurally untestable in `tests/authorization/`**. Choosing the entry point is a handler obligation, and handlers are layer 3 — the directory that survives ejection survives it precisely by having no handlers in it. The falsifier is therefore behavioural and lives at the wire, in two attack-suite rows: `row_probe_indistinguishable` for the named-resource half, and `list_partition_scoped` for the listing half, declared by this ADR because the listing half had none.

### Purity is structural, not promised

`Principal` arrives frozen and complete — issuer, subject, granted scopes, roles, partition. The policy function takes **no collaborators at all**, so it cannot perform input or output even by accident. Directory lookup is its own named step ahead of it, not an injected dependency.

An injected directory would make purity a promise every implementation must keep, and the seeded implementation reads from a file.

### The `Action` is the seam

Layer 2 defines a frozen `Action` — namespace, capability, required roles, ordered rule tuple, partition-bypass roles — and a `Rule` protocol `(Principal, Resource) -> Reason | None`. Layer 3 declares exactly one `Action` per tool, extending the per-tool declaration ADR-0012 already made single-source-of-truth. Ejection leaves the `Action` type and the chain with no instances declared.

*Amended 2026-08-18 by [#34](https://github.com/marcosfsousa/mcp-erp/issues/34) — the signature above is **parameterised on the resource type** as built: `Rule[R: Resource]`, `Action[R]`, `decide_item(principal, action: Action[R], resource: R | None)`.*

**The parameter states the signature precisely rather than departing from it.** Rule 3 traverses `Requisition.submitted_by` and the threshold reads an amount, and neither is a member of the one-member `Resource` protocol — so an unparameterised `Rule` would make every layer-3 rule cast its way back to the type it was declared beside, in the layer whose types are supposed to be the load-bearing part. `R` is bound to `Resource`, so a rule can only ever narrow what layer 2 already requires, and a resource of the wrong type is a type error rather than a runtime one.

Two costs, both small and both visible at the call site. `permits_scope` and `decide_call` take `Action[Any]`, because they read nothing from a resource and a caller filtering `tools/list` holds every declared action at once. And an `Action` declaration needs an explicit annotation — `LIST_REQUISITIONS: Action[Requisition] = Action(...)` — because an action with no relationship rules leaves a type checker nothing to infer the parameter from.

Recorded here rather than left to a reader diffing the code against this document, which is what the amendment idiom exists for.

**The scope string is derived, never stored as a literal.** ADR-0012 gives layer 2 the shape, the join, the comparison and the three words, with layer 3 supplying only `erp`; `scenarios.yaml`'s `insufficient_scope` row states that the `scope=` strings are *"derived from the capability each tool declares — never hand-written here."* An `Action` therefore holds the **capability**, and its scope string is a derived, unstored property. A stored literal would be a hand-written scope string in the one place the attack suite forbids one. The mechanism — a computed property, or a value computed once at construction — is left to the build ticket; the property is what this ADR fixes.

**`partition_bypass` is not uniform, and assuming it is grants cross-partition writes.** It holds `{auditor}` on the two read tools and is **empty on the three writes**. ADR-0003: *"`auditor` reads all three and writes nothing."* ADR-0012's table: *"May read across cost centres | no | `auditor`."* ADR-0007: *"`auditor` widens which rows are returned, it does not grant reading."* Breadth is a read widening, never a write grant. A reader who adds `{auditor}` to `record_invoice` for symmetry grants cross-partition invoice recording, and nothing in the type would object.

### A reason is a record, not a string

Layer 2 defines `Reason(value, denial_class, remedy, retry_identical_helps, retry_as_other_person_helps)` plus the closed `Remedy` and `DenialClass` vocabularies. Each layer declares its own instances — layer 2 its three, layer 3 its four. **There is no lookup table anywhere:** ADR-0002's derivation becomes a construction invariant, and nothing can name a reason without stating its shape.

ADR-0003's *"exactly one dedicated test"* survives, enumerating the union of both declared sets. Because layer 3's four reasons live in layer 3, that test necessarily imports layer 3 and so lives in `tests/matrix/`, not in the directory the ejection command runs.

**Naming note.** The attack-suite scenario `insufficient_scope` and the layer-2 `Reason` value `insufficient_scope` are character-identical and are different kinds of thing — a stable test identifier and a `Reason.value`. Nothing binds them; no drift check relates them.

### Row scoping reads one member, named `partition`

Layer 2 defines a `Resource` protocol with exactly one member. `principal.partition`, `resource.partition`, `action.partition_bypass`; layer 3 maps it to cost centre. A noun for the value rather than for the mechanism, as ADR-0004's criterion 3 requires. Prose keeps saying *row scoping* for the mechanism.

`row_scope` was rejected because `principal.scopes` (granted scope, from the token) and `principal.row_scope` (cost centre, from the directory) would sit in one record meaning different things, in the exhibit built to keep exactly that vocabulary straight. `unit` is barred by `CONTEXT.md`'s *Cost centre* Avoid line.

### Named versus discovered — the refusal contract

The rule, and the spine the rest of this section hangs from:

> **A resource named in the request is refused, never omitted.**
> **A resource discovered by listing is omitted, never refused.**

**This is entailed by the trail, not new here.** ADR-0002 gives the named case: *"foreign requisition → `not_found`, indistinguishable"*, and its option 3 rejected an explicit `row_out_of_scope` on `get_requisition` because it *"turns the read scope into an identifier-enumeration and cost-centre-mapping primitive."* ADR-0003 gives the discovered case: *"You see requisitions in your own cost centre"*, with read rows asserting *"set equality over returned identifiers."* What was missing is the sentence holding the two halves together — and the missing sentence is why one half went unfalsified.

Three consequences follow from it rather than standing as separate notes.

**Outcomes equal items requested.** A batch yields one outcome per item named in the request — permit or refusal, never a silent drop. This is what makes ~~response mode~~ **the answer** a function of the request rather than of the data, and it is the invariant a future handler would break by filtering a batch instead of refusing its members. *(Wording amended 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37): there is one response mode now, so the invariant is stated against what it always governed — how many answers come back, and from what. It is the same rule and it now carries the fold; see §Streaming, restated portably.)*

**The empty join and the foreign row converge.** A named resource that does not exist and a named resource in another partition are both `not_found`, reached through **a single return site**. Two return sites would make the refusal an existence oracle, which is the finding ADR-0002 declined to ship.

**The listing half had no falsifier.** `row_probe_indistinguishable` covers the named half only. A handler that takes a whole-call permit and lists every partition is a different failure, and until this commit nothing asserted against it. That absence is the argument for writing the rule down: the two halves are one contract, and only one of them was being checked.

### Indistinguishability is byte-identity, at two altitudes, and constant time is not measured

**Byte-identity is provable; timing indistinguishability is not — and least of all over HTTP.** A measured-timing assertion against Compose competes with container scheduling, garbage collection and network jitter; it flakes, and a flaky assertion gets disabled. Every context gates `main`, so a flaky required job is the one that would earn an exemption the ruleset does not offer.

- **Layer 2, in `tests/authorization/`:** convergence is a **single-return-site** property, asserted structurally.
- **The wire, in `tests/attack_suite/`:** `row_probe_indistinguishable` asserts **byte-identical** `not_found`.

Constant time is not measured at either altitude and is not claimed at either. ADR-0002's *"timing included"* and that row's note are narrowed accordingly in this commit. This reverses a project commitment, not a normative obligation — the row is `basis: adr` with `normative_strength: null`, sourced to ADR-0002 — so it is ADR-trail work and owes no normative-register row.

### Resource hydration is a named layer-3 step

Rule 3 traverses two entities: *"Submitter ≠ approver, tested against `Requisition.submitted_by`. Approver ≠ invoice recorder, tested against `PurchaseOrder.approved_by`."* The policy function has no collaborators, so the resource must arrive pre-loaded. A handler calls `load(action, arguments) -> Resource | None` before `decide_item` — the same promotion-to-a-named-step that kept the directory out of the policy function.

**The resource is the thing acted against, never the thing created.** For `record_invoice` it is the `PurchaseOrder`, which is what ADR-0003 already tests against; the invoice does not exist at decision time. `submit_requisition` has **no resource at all** — submitting is scope-only, and partition is server-derived, so out-of-partition writes are inexpressible rather than refused.

`load` returning nothing and `decide_item` returning `not_found` reach the same single return site, per the convergence consequence above.

*Amended 2026-08-19 by [#40](https://github.com/marcosfsousa/mcp-erp/issues/40), which built the first tool needing it.* **The step is a factory over the store, and the two callers share one.**

The signature above is the step's, not the function that builds it: `load(requisitions) -> Load` binds the store, and what the handler calls takes `(action, arguments)` exactly as written here. That is what keeps hydration a *step* rather than a collaborator — there is nothing to inject into the policy function, because the injection happens one level out, in layer 3, where a database dependency already lives.

`get_requisition` and `approve_requisition` call the same one. Two copies of *load by identifier and hand the answer through untouched* would be two places for a handler to start looking at what it got, and the convergence claim is that neither can tell an absent row from a foreign one.

**`action` is not read yet and is kept anyway.** The resource an action is decided against is a property of the action: both callers today name a `Requisition` by identifier, and `record_invoice` is decided against a `PurchaseOrder`, which is the call that makes the parameter select an entity. A narrower signature would be a second shape for a step this document already fixed, and would have to grow the parameter back at #42.

*Amended 2026-08-20 by [#42](https://github.com/marcosfsousa/mcp-erp/issues/42), which built the tool the paragraph above predicted.* **The parameter selects the entity through the type, and it is still not read.**

`load` is parameterised on the resource its store answers with — `load(store: ByIdentifier[R]) -> Load[R]`, where `Load[R]` is this document's `(action, arguments)` with `R` fixed. So `hydrate(ACTION, arguments)` type-checks only when the action was declared against the entity the bound store returns, and hydrating a requisition for an action decided against a purchase order is a red types job rather than a refusal nobody sees. The prediction was that #42 would make the parameter *select an entity*; what it selects with is `R`, and no branch anywhere reads the action's value.

The alternative — one step that inspects the action at run time and picks a store — was rejected for the reason one module per tool exists: it would put a table of tools inside the layer whose whole point is that a tool's identity is its module.

The stores split with it. Layer 3 holds two, one per entity a tool is decided against, over one pool: a handler is written against what it uses, and `record_invoice` uses no requisition. `ByIdentifier[R]` is narrower than either — the one method hydration calls — which is what lets a single `load` serve both without learning that either store exists.

### The principal directory

`lookup(claims) -> Principal | None`, where `Claims` is layer 2's own frozen type carrying issuer, subject and granted scopes. Claims and Principal are not two halves of one thing but two **stages** — the unverified caller the token asserts, and the resolved principal the server stands behind — and that distinction is this exhibit's subject, so making it a type boundary is legible rather than incidental.

**Layer 2 owns the shape, the implementation and the renderer.** The directory is backed by a **committed data file held immutable in memory**, so layer 2 acquires no database dependency, the ejection test runs the real implementation rather than a stub, and `tests/authorization/` stays Docker-free by construction. Resolving roles from the authorization server per request was never available: ADR-0006 rejected *"a hard per-request dependency on the authorization server."*

**Roles leave the ERP `person` table.** They are policy facts, not domain facts — `CONTEXT.md` already says a role is *"resolved server-side per request, never carried in the token."* The person table keeps name and cost centre; the directory keeps issuer, subject, roles and partition. Only the cost-centre-to-partition mapping is duplicated, and it is duplicated by generation, which is what a drift check polices.

**Lookup runs inside `TokenGate`, immediately after ADR-0006's gate 4**, and puts the `Principal` in request state for dispatch to read. ADR-0006 orders *gates*; this is a resolution step, and the amendment there says so.

**A directory miss is an explicit refusal, and `Principal.partition` is non-optional.** The tempting design — a miss yields a principal with no roles, refused at the role step — **fails open.** Map note `#6` makes submitting scope-only and note `#11` leaves `erp.write` deliberately ungated, so an unknown subject holding `erp.write` would clear the scope gate, clear a role gate demanding nothing, and submit a requisition charged to a null cost centre. A non-optional `partition` makes a miss structurally unable to produce a `Principal`.

The miss reuses **`role_missing`**. Its record is byte-identical — denial class `-31010`, remedy `administrator_grant`, both retry booleans false — so by construction they are one reason, not two. It is asserted in `tests/authorization/`, where it matters most: after ejection an empty directory is the normal state. It gets **no attack-suite row**; ADR-0010's single `documented, not asserted` allowance is spent on `threshold_split_evasion`.

**What is claimed about mintability, and what is not.** The realm and the directory are rendered from one seed and **held equal by a checked invariant** — realm subject set equals directory subject set, with Priya Raman declared as an exception on the *role columns only*, never on membership. The stronger claim that a stranger's token is unmintable is **withdrawn**: ADR-0007 engineers realm-versus-server drift on purpose, so a realm user with no directory row is one configuration edit from a state this design deliberately inhabits. The invariant is a test; the unmintability was an assumption about who writes the realm.

### `tools/list` shares one step, and what keeps ADR-0002's cache proof true

`tools/list` cannot call the full chain — that would run the role check and hide a tool from a principal holding the scope but not the role, collapsing the `-31010` denial class ADR-0002 built. So `permits_scope` is step 1 of the chain and is called directly by `tools/list` over the declared actions. One implementation, two call sites, and *listing is a strict prefix of the call gate* becomes visible rather than inferred.

**An invariant that is not obvious and is load-bearing.** ADR-0002 sets `cacheScope: "private"` and `ttlMs = min(300000, milliseconds until the token expires)`, and its proof is that the listing *"is a **pure function of the access token**: new scopes mean a new token, which is a different cache key."*

`permits_scope` takes a `Principal`, which is directory-derived. **The proof survives only while `permits_scope` reads token-derived fields exclusively** — issuer, subject, granted scopes — and never roles or partition. The obvious future change is a role check on listing, reasoning *why list a tool they will be refused on?* That would make a directory revocation invisible for up to five minutes on an unchanged token, and nothing in the code would object. **If `permits_scope` ever reads a directory-derived field, ADR-0002's `ttlMs` argument must be re-derived.**

### Streaming, restated portably

ADR-0002 earns the stream on one tool because *"a batch is N independent decisions with N independent outcomes."* In layer-2 terms: **a call that yields N independent outcomes.**

The restatement is structural, not prose. Handlers **yield** outcomes; ~~layer 1 consumes and keys the response mode on **cardinality** — one outcome answers `application/json`, more than one opens the stream.~~ Layer 1 never learns which argument is the batch, nor that the tool is called `approve_requisition`. This is the idiom layer 1 already uses for refusals, keying on `denial_class` rather than on which rule fired.

~~**A per-tool flag on the `Action` is the wrong granularity.** ADR-0002: *"A single-item call answers with `application/json` instead, so one tool exercises both response modes."* The mode is a property of the call. A flag would also put a transport concern on a record the policy function never reads.~~

**Result rows are not outcomes.** A list returning three requisitions is one outcome containing three rows, so list tools never reach this decision. Determinism comes from *outcomes equal items requested* plus matrix rows fixing the request~~, and each matrix row carries its expected response mode~~.

*Amended 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37) — **there is one wire shape, so there is no mode to key.*** [ADR-0002](0002-refusal-shape-follows-the-remedy.md) took its own option 5 and cut the SSE response mode; every POST is answered `application/json`. The cardinality keying above is void, the per-tool-flag rejection beneath it is moot — a flag choosing between one thing is not a granularity question — and the matrix's expected-response-mode column is dropped rather than kept as a constant, since `matrix.yaml` does not exist yet and a column whose every value is the same changes no assertion.

**The rule that replaces it: N outcomes fold into one result body.** A handler yielding N `Decision`s produces one result carrying N answers, one per item named in the request. That is *outcomes equal items requested* doing the same work through a different door — it was the invariant the response mode was a function of, and it is now the invariant the fold is a function of. Nothing is lost by the cut: a batch still yields one outcome per item, permit or refusal, never a silent drop, and a handler that filtered a batch instead of refusing its members would still be the failure.

~~**The fold is specified here and not implemented, and [#41](https://github.com/marcosfsousa/mcp-erp/issues/41) lands it.**~~ ~~No tool yields more than one outcome yet — the batch tool is unbuilt — so dispatch **refuses loudly** on a cardinality above one rather than folding, naming that ticket in the message.~~ Stated rather than left as a difference between this document and the code, because a spec that describes behaviour the code does not have is the failure mode this trail is named for. ~~The shape of the folded body — what holds the N answers, what `is_error` means when some items refused — is deliberately left to #41, which is where the first caller appears.~~

**What layer 1 still consumes cardinality for.** It counts outcomes: one renders directly, N fold. It still never learns which argument is the batch, nor the tool's name. The negative guarantee is unchanged by the cut and is the half worth keeping.

*Amended 2026-08-20 by [#41](https://github.com/marcosfsousa/mcp-erp/issues/41), which built the batch and the fold.* **The two open questions are answered, and building them found a third nobody had asked.**

**The body is `{"outcomes": [...]}`, one answer per item, in the order the handler yielded them.** The key is `outcome` in ADR-0013's own sense — what a handler yields per item, the second of the two spendings `CONTEXT.md` records for the word — and it names no tool and no argument, which is what let layer 1 keep the guarantee while gaining the fold.

**The fold adds no identifier of its own, and a caller maps answers to items by position.** A permitted answer carries a row because the row *is* the answer and the handler put it there; a **refusal** carries none, and that is the half the rule is about. A refusal that named its row would make `not_found` on a foreign row distinguishable from `not_found` on a row that never existed, which is the existence oracle [ADR-0002](0002-refusal-shape-follows-the-remedy.md) declined to ship, arriving through the fold instead of through the refusal. Layer 1 could not add one in any case — it never sees the request's items — so what this fixes is that nothing *else* may be tempted to: an item-to-answer key added later would have to be built from the refused items too, and that is where it would leak.

**`isError` is true when *any* item was refused.** The alternative readings were *all refused* and *never*, and both lose the thing the flag is for: the specification makes a tool execution error *actionable feedback a model can self-correct on*, and a mixed batch has something to act on. It invites a retry of the whole call, and per-item idempotency is exactly what ADR-0002 promises makes that harmless — so the flag that provokes the retry and the mechanism that survives it are the same design, stated in two places.

**A handler that decides more than one item must settle the call before its first item.** This is the obligation the fold produced. A caller-level refusal is a `-31010`, a JSON-RPC error is the *response* rather than a line inside one, and a handler reaching `role_missing` once per item would hand layer 1 N answers it has no rendering for. So `decide_call` runs once ahead of the loop and `decide_item` runs per item — which is ADR-0002's *caller-level refusals are whole-call; item-level refusals are per-item* arriving as a structural obligation on handlers rather than as a description of two kinds of refusal. Layer 1 refuses a non-`tool_result` denial class inside a fold loudly, on the same terms as the challenge class it already refuses: rendering it would turn a refusal a client must act on into one a model would try to route around.

**Zero outcomes is refused, not folded into an empty list.** A call answered with nothing is what a batch that dropped every item it was given looks like, and *outcomes equal items requested* is the rule that distinction is the whole of. Layer 1 answering an empty fold would be layer 1 inventing an answer on a handler's behalf.

**The declared `outputSchema` carries the cost, and it is the right cost.** A tool that can be called with one item or with several publishes both bodies under a `oneOf`, because layer 1 renders on cardinality and cardinality alone — a one-item batch is indistinguishable there from `get_requisition`. The alternative is layer 1 learning which tool it is folding for, which is the coupling this document exists to refuse. It describes the **permitted** body only, as every `outputSchema` here has since the first refusal shipped: a refused item is a result marked in error, and having layer 3 declare the refusal's shape would put layer 1's rendering in a layer-3 document.

### Handlers in layer 3, adapters in layer 1

A handler takes a `Principal` and parsed arguments, calls `load` and the chain, and returns a domain outcome or a refused `Decision` — never anything protocol-shaped. Layer 1 holds the three adapters ADR-0002 specified and renders what comes back, keyed on `denial_class`.

**Layers 1 and 3 import nothing from each other**; the composition root registers handlers with the protocol package. This is #5's handoff — *the refusal decision and the refusal shape are different concerns* — made physical.

**Layer 1 learns the shape of a refusal, never its grounds.** It sees `denial_class` and cardinality; it never sees which rule fired, against which attribute, on which row. That is the precise form of the title's claim.

*Amended 2026-08-19 by [#39](https://github.com/marcosfsousa/mcp-erp/issues/39), which built the first tools taking arguments.* **A handler has a third thing to say, and it is not a refusal.**

The sentence above gives a handler two answers: a domain outcome, or a refused `Decision`. A tool that takes arguments has a third case — an argument its own declaration forbids, like a vendor absent from the `enum` [ADR-0002](0002-refusal-shape-follows-the-remedy.md) put in `submit_requisition`'s schema. Nothing on this stack validates arguments against a declared `inputSchema`, so the case arrives at the handler rather than being refused ahead of it.

**It answers `-32602`, and it carries no `Reason`.** Nothing was authorized or denied, so giving it one would amend [ADR-0002](0002-refusal-shape-follows-the-remedy.md)'s closed vocabulary for a spelling mistake — and would tell a model to route around a wall that is not there, which is the same collapse the three denial classes exist to prevent, arriving through a fourth door. The three shapes are unchanged and this is not a fourth one.

**The signal is `ValueError`**, the standard library's name for exactly this, so a handler raises it without importing anything layer 1 owns and layer 1 catches it around the handler's own iteration and nowhere else. The alternative — layer 1 validating arguments against the declared schema itself — would put a JSON Schema implementation in the layer that must not learn what a tool is, for a rule the declaration already states. The negative guarantee holds: the message is the handler's, and layer 1 never inspects it.

*Amended 2026-08-19 by [#40](https://github.com/marcosfsousa/mcp-erp/issues/40), which built the first tool with a state to be in.* **A handler answers domain preconditions as well as decisions, and it answers them last.**

`already_decided` is not a decision about the caller. Every principal gets it on a decided requisition, and no role, scope or person changes that — so the chain, which decides about callers, is the wrong place for it, and `Action.rules` is the wrong field: `CONTEXT.md` defines a relationship rule as one *"decided by the identities and amounts involved"*, which names segregation of duties and the threshold and does not name this.

So the handler constructs a refused `Decision` of its own. That is inside the letter of *a domain outcome or a refused `Decision`* above, and it is worth stating because the record now arrives from two places: layer 2's chain, and layer 3 answering for the row's state. Layer 1 is unaffected — it keys on `denial_class` and cannot tell which produced it, which is the negative guarantee holding under a case it was not written for.

**Two orderings fall out, and both are load-bearing.** It is answered *after* the chain permits, so a caller who may not decide a row learns nothing about whether it has been decided — the same non-disclosure `not_found` keeps, applied to state instead of existence. And it is answered *at* the write rather than against the row `load` returned: a check against a row read a moment ago is a check against what was true then, and two callers deciding at once both pass it. The predicate rides in the `UPDATE`, so exactly one wins and the loser is told.

### The gate chain sits in middleware, in two tiers

*Amended 2026-08-18 by [#32](https://github.com/marcosfsousa/mcp-erp/issues/32) — the two tiers and their order survived contact; the carrier under them did not. `Mount` becomes `Route`, and the accepted cost below is withdrawn.*

**A FastAPI dependency cannot gate the tool endpoint at all.** ADR-0008 settled that layer 1 is the official Python `mcp` 2.0.0 package, which supplies its own ASGI application. Under Starlette a mounted ASGI app is not a route — `mount()` takes a path, an app and a name, with no `dependencies` argument — and dependency solving happens inside a route handler a mount never enters. Middleware is the mechanism that reaches it. ~~*Verified from documentation, not execution; it belongs with ADR-0009's first-run assertions.*~~ **Executed, 2026-08-18 (#32):** a `FastAPI(dependencies=[...])` global fires for an `APIRoute` and does not fire for either a `Mount` or a plain `Route` holding an ASGI app. The claim is now a finding rather than an assumption, and no longer needs to wait for a first run.

```python
app = FastAPI(routes=[
  Route("/.well-known/oauth-protected-resource/mcp", metadata),  # no token gate
  Route("/mcp", endpoint=mcp_asgi_app, middleware=[
      Middleware(ShapeGate),   # gate 2
      Middleware(TokenGate),   # gates 3, 4, then directory resolution
  ]),
])
app.add_middleware(OriginGate)  # gate 1, every path
```

**`Mount` was the wrong carrier, and would have failed on the first `curl`.** Starlette compiles `Mount("/mcp", …)` to `^/mcp/(?P<path>.*)$`, which never matches the bare `/mcp` an MCP client posts to. The outer router falls through to `redirect_slashes` and answers **307 to `/mcp/` without running a single mount-level middleware** — the gate chain is not bypassed, because a redirect processes nothing, but the endpoint is wrong and every call pays a round trip. `Route` compiles to `^/mcp$`, takes the same `middleware=` sequence, and is what the `mcp` package itself uses internally to hang its ASGI app off a path.

Two constraints ride along, both load-bearing and neither obvious:

- **`mcp_asgi_app` is `StreamableHTTPASGIApp(server.session_manager)`, not the `Starlette` that `streamable_http_app()` returns.** That wrapper carries its own inner `Route(streamable_http_path)` — defaulting to `/mcp`, so nesting it under `/mcp` serves `/mcp/mcp` — and its own router's redirect. A `Route` endpoint must also be a non-function callable: Starlette wraps an `async def` endpoint as a request/response handler and calls it with a `Request`, so a bare ASGI function `500`s where a class instance works.
- **The composition root runs `server.session_manager.run()` in its own lifespan.** A nested app's lifespan is never run by its parent, and there is no quiet degradation to catch later — every request answers `500` until it is wired.

The unauthenticated endpoints sit outside the token gate **structurally** rather than by a path allow-list — preferring an attack to be impossible over defended-against, the move ADR-0006 already made once. ~~Gates 5 and 6 are the chain, at dispatch, where the `Action` is known.~~

*Amended 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which built it.* **Gate 5 is a third route-level middleware; gate 6 is at dispatch.** The sentence above split them by where the `Action` is known, and that turned out not to be the thing that decides it.

The `Action` is known in middleware too. Gate 2 has already proved the `Mcp-Name` header equal to the body's `name` parameter, and layer 1 holds the registry that maps a tool name to its declaration — so a middleware can reach the same `Action` dispatch would, through a header the ordering has already made safe.

**What decides it is the wire shape.** ADR-0002 specifies the scope refusal as a `403` carrying `WWW-Authenticate: Bearer error="insufficient_scope", scope=…, resource_metadata=…`. By the time dispatch runs, the response is a JSON-RPC envelope at `200`, and nothing inside it can set a status code or a header. Gate 6's two shapes — the `-31010` protocol error and the tool result marked in error — both fit inside that envelope, which is why they stay where they were.

```python
Route("/mcp", endpoint=mcp_asgi_app, middleware=[
    Middleware(ShapeGate),   # gate 2
    Middleware(TokenGate),   # gates 3, 4, then directory resolution
    Middleware(ScopeGate),   # gate 5
])
```

**The scope rule still has one implementation.** `ScopeGate` and the handler's `decide_call` both call `permits_scope`, which is the same deliberate N+1 the chain already pays inside a batch — and it is what keeps *listing is a strict prefix of the call gate* true rather than nearly true. A tool name nothing is registered under is left alone: dispatch owns *no such tool*, and answering it at gate 5 would make an unknown name and an unpermitted one distinguishable in the wrong direction.

**Route-level middleware reaches everything the two tiers need.** Confirmed by execution at #32: the chain runs `OriginGate → ShapeGate → TokenGate → mcp_asgi_app`, exactly as drawn; `ShapeGate` reads the `Mcp-Method` header and the parsed body together and sees ADR-0006's own attack payload disagree; and a value written to the ASGI scope's `state` by `TokenGate` is readable at dispatch as `ctx.request.state.<name>`, which is where the `Principal` goes.

**`ShapeGate` must hand the body back, not consume it.** Reading the body means draining the ASGI `receive` channel, and the mounted application drains it again. The replacement channel replays the buffered body once and then **delegates to the original**; returning `http.disconnect` after the body instead makes the application abandon its response mid-flight (`ASGI callable returned without starting response`). This is a correctness constraint on gate 2, not a detail of it.

~~Accepted cost: mount-level middleware is not wrapped by Starlette's exception-handling middleware, so challenges render themselves. They are `WWW-Authenticate` responses rather than exceptions, so this is arguably right anyway.~~ **Void, 2026-08-18 (#32):** there is no such cost on this stack. Route- and mount-level middleware both sit **inside** the application's `ExceptionMiddleware`, and an `HTTPException` raised in either renders normally. Challenges may still build their own `Response` — a `WWW-Authenticate` body is easier written directly than routed through an exception — but that is now a choice rather than a constraint.

## Repository and continuous-integration shape

The title covers the layer contract. This section covers the repository, and is where a reader should look for module layout, test layout, enforcement and continuous integration.

### Three sibling packages, one composition root

```
src/mcp_erp/
  transport/        # layer 1
  authorization/    # layer 2
  purchase_to_pay/  # layer 3
  app.py            # composition root — the only module importing all three
```

Ejection is one `rm -rf` plus editing one file. ADR-0004 option 3 already rejected extracting layer 2 as a separate installable distribution, and nothing here reopens it.

*Amended 2026-08-19 by [#39](https://github.com/marcosfsousa/mcp-erp/issues/39), which built the second and third tools.* **Inside layer 3, a tool's declaration is one module per tool.**

A tool declares five module-level names — `NAME`, `TITLE`, `DESCRIPTION`, `INPUT_SCHEMA`, `OUTPUT_SCHEMA` — plus its `Action`. One module holding three tools has to prefix all six, which is the flattening layer 3's `__init__` already refuses at the package level, arriving one level down. So `purchase_to_pay/` holds `requisition.py` for the entity and the row shape its readers share, and `list_requisitions.py`, `get_requisition.py` and `submit_requisition.py` for the declarations, each naming its `Action` `ACTION` — the tool's identity is the module's and is never repeated inside it. The handlers stay together in `handlers.py`, which is what makes the three entry points visible in one file.

The composition root pairs them by hand, three times, rather than looping: the three declaration modules have no common type, and giving them one means a protocol describing what a tool declaration holds — a fourth spelling of `ToolRegistration`, living in the layer that must not learn what a tool is.

### ~~Four~~ Test directories, named for artifacts

```
tests/
  authorization/   # in-process, layer 2 only, no Docker — the ejection target
  matrix/          # wire; plus the one union mapping test
  attack_suite/    # wire; 33 rows including ADR-0009's 3 basis:seam
  conformance/     # wire + outbound; the authorization code flow
```

**The ejection test is a command, not a file** — `rm -rf src/mcp_erp/purchase_to_pay && pytest tests/authorization` — so that directory imports nothing from layer 3, and this ticket's *"unit tests of the policy function"* are those same files. Layers 1 and 3 get no directory of their own; ADR-0008 routes every assertion about them over the wire.

*The count in this heading is struck 2026-08-20 by [#66](https://github.com/marcosfsousa/mcp-erp/issues/66), on the same reasoning it struck the one in* Continuous-integration jobs, one per seam: *there have been five directories since the amendment immediately below, and a derived number kept in a heading is what [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md) caught drifting. **Named for artifacts** was always the claim.*

*Amended 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which built the first slice through all three layers.* **A fifth directory, `tests/wire/`.**

```
tests/
  wire/            # wire; the server's own posture — endpoints, listing, replicas
```

Three assertions in that slice belong to none of the four. The **metadata route answering without a token, and every other path being gated** is ADR-0006's discovery decision, defending nothing named in `scenarios.yaml` and expecting no `(principal × tool × resource)` row. **Two replicas, round-robin, nothing remembered** is map constraint `#5`, a property of the deployment rather than of a caller. The **tool listing's filter** ~~and its freshness hint~~ ~~becomes~~ **became** ~~four~~ **five** rows of `matrix.yaml` when #43 wrote it — one per scope set, enumerated in *Continuous-integration jobs, one per seam*; `tests/matrix/` is generated in its entirety.

*Amended 2026-08-20 by [#66](https://github.com/marcosfsousa/mcp-erp/issues/66).* **The freshness hint stays, and so do the declarations beside it.** `cacheScope`, the `ttlMs` cap, the declared schemas and `listChanged: false` are things the server states identically to every caller, so they are not expressible as a `(principal × tool × resource)` row and never had a destination in `matrix.yaml`. The dividing line is the one the ninth job is named for: what varies with the caller is the matrix's, what the server declares regardless is this directory's. See *Continuous-integration jobs, one per seam*.

The alternative was to mint scenario rows for the first two, and it was declined: membership is ADR-0010's rule — one row per distinct clause this project *enforces*, each recording the exact removal that makes it pass — and the row count is a derived artifact under map constraint `#12`. Inventing two rows to house three tests would move a number three documents track, to record something that is not an attack.

**The prohibition above is untouched.** It bars a directory named for a layer collecting in-process unit tests of that layer; `tests/wire/` is named for the altitude every assertion in it shares, and every one of them drives real HTTP against Compose like the three suites beside it. The count of directories was never the claim — *named for artifacts* was, and this one is named for the only thing its contents have in common.

*Amended 2026-08-20 by [#41](https://github.com/marcosfsousa/mcp-erp/issues/41).* **One assertion in `tests/wire/` is not over HTTP, and it could not be.**

*Layer 1 contains no reference to the tool name, nor to which argument is the batch* is the negative guarantee the fold had to be built without breaking, and it is not reachable at this altitude: a name absent from a module is absent, and no request can show it. So it is read off layer 1's own source, with docstrings stripped first — the guarantee is *stated* in two of those modules, and a check that read prose would fail on the sentence describing what it asserts. It sits beside the fold's three behavioural assertions in `test_the_fold.py`, because the alternative was a sixth directory holding one file.

The precedent is `tests/authorization/test_purity.py`, which reads layer 2's source for the same class of reason: a property that is true by *absence* has no behaviour to drive. The sentence above is therefore narrowed rather than kept — the directory is named for the altitude its assertions share, and one of them belongs to a claim that has no altitude.

### Both generators, split by the vocabulary each speaks

The **identity generator** lives in `authorization/`: it reads the seed's authored cast and renders directory rows and the authorization server's user import. The **fixture generator** lives in `purchase_to_pay/`: it reads the matrix definition and emits one requisition per row. Each is deleted with the layer whose words it uses, so ejection correctly removes the fixture generator while provisioning survives — ADR-0004's criterion 4 read literally rather than approximately.

They do not collide: ADR-0003 already splits the seed into *"the organisation is authored; the test data is generated"*, so each touches one half. ADR-0003's seam sentence — *"the seed generator reads the matrix, and the policy function reads neither"* — gains a successor: **each generator speaks one layer's vocabulary and is deleted with it; the policy function reads neither, and neither reads the other.**

*Amended 2026-08-18 by [#35](https://github.com/marcosfsousa/mcp-erp/issues/35), which built them.* **Two generators becomes three**, and the rule above is what produces the third rather than being bent by it.

This section named two generators while the seed has three renderings, and the one it left unaccounted for is the ERP's own rows — the fixture generator renders none of the three, since it reads `matrix.yaml` rather than the seed. Those rows speak cost centres, vendors and people, which are layer 3's words, so their renderer lands in `purchase_to_pay/` beside the fixture generator and is deleted with them. The count is therefore **three generators**: layer 2's identity generator, which renders two of the three renderings, and layer 3's two, which render the third and the fixtures. Which is the same rule read carefully rather than a new one: *the vocabulary decides the layer, and the layer decides what the deletion takes.*

The two layer-3 generators stay separate rather than merging into one command, because they read different sources for different reasons — the organisation renderer reads the authored half of the seed, the fixture generator reads `matrix.yaml` — and merging them would put the stable half of the seed and the disposable half behind one entry point, which is the distinction ADR-0003 spends a section drawing.

**The `Seed renders clean` job carries the consequence.** Layers 1 and 3 get no test directory, so the ERP rendering has no unit test to hold it — its cover is the job re-rendering all three and refusing any diff, which is the mechanism ADR-0003 already specified for exactly this. Layer 2's renderer additionally carries invariant tests, and they live in `tests/authorization/` because provisioning survives ejection, so the ejection job runs them too. The overlap is accepted: a broken generator invariant genuinely breaks both claims, and neither job can cover the other's half.

Because the fixture generator ships in `src/`, the matrix definition cannot live under `tests/`. It is a committed data file at **`docs/decision-matrix/matrix.yaml`**, sibling to `docs/attack-suite/scenarios.yaml`. The two are disjoint and neither arbitrates the other: `scenarios.yaml` is canonical for named attacks, `matrix.yaml` for `(principal × tool × resource → expected)`. They share no rows. The one thing they touch is ADR-0002's reason-to-shape mapping, whose union test lives in `tests/matrix/`.

*Amended 2026-08-20 by [#43](https://github.com/marcosfsousa/mcp-erp/issues/43), which built the third generator and the file it reads.* **Three generators, four renderings**, and the arithmetic above holds because the fixture generator was never counted as rendering one of the seed's three: it emits its own, `src/mcp_erp/purchase_to_pay/data/fixtures.json`, from `matrix.yaml`.

**`tests/matrix/` is ~~generated~~ *driven* in its entirety**, which is one word and not a reversal. What that phrase was for — no expectation in that directory is hand-authored, so adding a matrix row adds a test with nothing edited — holds exactly, through parametrisation rather than through emission. Nothing writes those files. Saying *generated* would enrol them in `Seed renders clean`, which compares a rendering against what its source produces and would have nothing to compare against here.

**Two consequences that were not visible until it was built.**

*The drift job's diagnosis widens by one word.* `Seed renders clean` re-renders four artifacts now, and one of them has no seed behind it — so what it refuses is *a rendering its source does not produce*, and its two sources are the seed and the matrix. The job name is untouched: renaming a job detaches every ruleset rule pointing at the old string, and the seam is the same one either way.

*The two files do share the fixtures, and that is not a shared row.* `tests/attack_suite/` reads the same generated rows `tests/matrix/` drives against, because ADR-0003 gave the seed's disposable half **one author**. A scenario consuming that data is consuming data; a row is `(principal × tool × resource → expected)`, and no scenario declares one. What makes the sharing safe in practice is that nothing outside the matrix names a fixture by identifier — every other suite asks for one by the property it needs, so the generator renumbering on an insertion moves no assertion.

**The seed renders three ways** — ERP rows, directory rows, and the realm import — and ADR-0007's third column means the seed carries **two independent role columns**, with layer 2's generator treating issuer-side role names as opaque strings it never interprets. Rendering the realm import from directory roles would erase Priya's divergence, which ADR-0007 calls load-bearing.

**The renderer must be byte-stable or the drift job is flaky**: sorted keys, no generated identifiers, no timestamps. Keycloak realm exports produce all three by default. A flaky required job is the one that would earn an exemption the ruleset does not offer, so this is a constraint on the renderer rather than a tolerance in the check.

### Both enforcement mechanisms, divided

The ticket asked *"mechanical enforcement or review?"*, and that framing does not survive the test layout: **the ejection job is already a mechanical enforcer.** Review was never the alternative. The question was whether a second mechanism earns its place, and it does, because they cover different claims.

| | Ejection job | import-linter |
| --- | --- | --- |
| Layer 2 importing layer 3 | only in modules those tests reach | whole static graph |
| Layers 1 and 3 independence | not covered | covered |
| Layer 2 *runs* standalone | proved | not addressed |
| Dynamic / string-based imports | caught | missed |

```ini
# .importlinter
[importlinter]
root_package = mcp_erp

[importlinter:contract:1]
name = Layer 2 knows nothing above it
type = forbidden
source_modules = mcp_erp.authorization
forbidden_modules = mcp_erp.transport
                    mcp_erp.purchase_to_pay

[importlinter:contract:2]
name = Transport and domain never meet
type = independence
modules = mcp_erp.transport
          mcp_erp.purchase_to_pay
```

Because `app.py` sits at the package root rather than inside any sub-package, these contracts **need no exception clause for the composition root** — it is out of scope by construction rather than by a carve-out someone has to justify. The contract file is also a readable statement of the architecture, which for an exhibit whose product is legibility is a deliverable rather than overhead.

### ~~Eight~~ Continuous-integration jobs, one per seam

| Job `name:` | A red check means | Compose |
| --- | --- | --- |
| Lint and types | ordinary Python defect | no |
| Layer boundaries | someone crossed a layer boundary | no |
| Layer 2 ejects clean | layer 2 no longer stands alone | no |
| Seed renders clean | a rendering diverged from the seed or the matrix | no |
| Required checks match the ruleset | the workflow and the ruleset disagree | no |
| Published documents are immutable | someone rewrote or removed a published client identity | no |
| Server posture | the server exposes, declares or deploys something other than what it should, with no caller's authorization involved | yes |
| Decision matrix (wire) | an authorization expectation is wrong | yes |
| Attack suite (wire) | a defence regressed | yes |
| Authorization code flow | the flow broke (preflight names external causes first) | yes + network |

**~~All eight~~ Every context gates `main`.** Set equality holds in both directions, there is no exemption list to justify, and ADR-0008's *"a check that can never block becomes noise"* applies uniformly. ADR-0008 already committed the conformance job as the repository's first required status check.

*Seed renders clean* is the widened form of what was scoped as matrix-fixture drift: it now covers seed-to-directory and seed-to-realm as well, including the realm-versus-directory subject-set equality above. All three break for one reason — a rendering changed without the seed — so it is one seam and one diagnosis.

*Required checks match the ruleset* holds job names and required contexts equal in both directions. It is its own job because it must not sit on a cut path: cutting the decision matrix, third on cut order `#9`, removes *Decision matrix (wire)* and *Seed renders clean* together, and a name-contract test inside either would be cut in silence, taking the argument for required checks with it. *Lint and types* would hold it uncuttably but would then mean two unrelated things, against this table's own rule.

*Amended 2026-08-20 by [#66](https://github.com/marcosfsousa/mcp-erp/issues/66), which found the table and `ci.yml` disagreeing in both directions.*

**The count was never a cap, and this document never said it was.** `tests/wire/README.md` claims *"ADR-0013 fixes the job set at eight"* and #66's body inherited the claim, but nothing here fixes anything at eight — the heading named a count, the paragraph above requires set equality, and *one per seam* is the only rule. The number is derived from the seam enumeration, so it is struck rather than incremented. A derived number kept in a heading is the artifact ADR-0011 caught drifting from individually-correct sources four times in one month; this is the fifth.

***Server posture* is the ninth seam.** `tests/wire/` arrived with the fifth-directory amendment above and no row was added beside it, so from 2026-08-19 until this commit four discharged acceptance criteria were guarded by review and a single recorded run. Its diagnosis is one thing: **what the server exposes, declares and deploys, identically to every caller.** The endpoints that answer without a token and the ones that do not; the listing's freshness hint, its declared schemas and `listChanged: false`; two replicas behind no sticky routing. None of them reads a `Principal`, and that clause is what keeps this row out of *Decision matrix (wire)*'s territory rather than beside it.

**It carries no `(wire)` suffix.** That suffix distinguishes a job from the `CONTEXT.md` proof artifact it shares a name with — *Decision matrix* and *Attack suite* are both defined there as artifacts, so *(wire)* reads *the wire test of the decision matrix*. *Server posture* names no artifact, which is why *Authorization code flow* carries none either.

**It sits off every live cut path.** Cut order `#9`'s live entries are *conformance traceability*, still undefined, and *decision matrix* at rank 3. Cutting the matrix removes *Decision matrix (wire)* and *Seed renders clean* together and leaves this job whole, because nothing in it reads `matrix.yaml`. Stated rather than derived: the argument for *Required checks match the ruleset* being its own job turns on cut-path exposure, and the next reader will ask the same question here.

**What `tests/wire/` hands to #43, and what it keeps,** is the same line the seam is named for. An assertion whose expected value changes with the caller is decision-matrix business; an assertion the server makes identically to every caller stays. ~~Four~~ **Five** of `test_tool_listing.py`'s assertions move — one per scope set the listing filters on: `erp.read`, `erp.write`, both, `erp.decide`, and the token carrying no capability scope at all. *(Corrected in the same commit, before the count could be handed on: the number was written against the file as #37 left it, and #39 and #42 added a scope set to it. It is replaced by the enumeration rather than re-derived, on this document's own reasoning about counts.)* What does **not** move is `cacheScope`, the `ttlMs` cap, the declared schemas, `listChanged: false`, and *the listing is a function of the token and not of the person* — that last one asserts an invariance **across** callers rather than a value that varies with one, which is the same rule reading in the other direction. **The handoff is priced in the map rather than left implicit:** cutting the decision matrix now also takes the tool listing's scope filter with it, which was not true before this commit and is a cost the taker of that cut must be able to see.

The unlisted-tool refusal stays too, on a narrower ground. `scenarios.yaml`'s `insufficient_scope` row already defends the challenge's shape and is marked `asserted`. What the wire assertion adds is the **agreement between the listing and the call** — a tool the listing omits, called anyway, is refused naming the scope that would have reached it. Nothing in the attack suite consults the listing, so handing this assertion away would drop the linkage rather than relocate it.

***Published documents are immutable* is the tenth row**, and it was in `ci.yml` before it was here. Its seam is its own — a red check means someone rewrote or removed a published client identity, which is neither a Python defect nor a crossed layer boundary — and it installs no environment, so it stands when the jobs beside it fall over. **What a green tick does not assert:** with no comparable base commit it warns and passes, having checked nothing. A pull request always carries a base and a push to `main` always carries a real predecessor, so the only reachable path is a force push to `main` — which is why #47 should block force pushes in the same ruleset that requires these contexts, closing the gap without touching the job.

**The first Compose bring-up in continuous integration lands with this job**, ahead of the three tickets expected to bring it. #66 writes it plainly inside *Server posture* — bring the stack up, wait on healthchecks, and settle the `keycloak` hostname the token helper's issuer requires — and #43, #44 and #46 inherit the pattern. It is deliberately **not** factored into a shared action yet: *Authorization code flow* is `yes + network` in the table above and is already known to differ, so a shared seam designed against one real consumer and three imagined ones would be built on the wrong example.

*Amended 2026-08-20 by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46), which built the third bring-up and found the count above spent.* **Two of the three imagined consumers are real now, and what they show is the decision standing rather than falling.** [#43](https://github.com/marcosfsousa/mcp-erp/issues/43) landed *Decision matrix (wire)*, which repeats *Server posture* step for step; this ticket lands *Authorization code flow*, which differs exactly where the `yes + network` row above predicted — a preflight *before* Compose, so an unreachable GitHub Pages fails a named step instead of presenting as the flow failing, and a bring-up that builds in the same command rather than in a step of its own. So a seam would now be designed against two consumers that agree and one that does not, which is the example this paragraph asked for instead of the wrong one. It is **still not factored**: neither ticket was going to ship a refactor of somebody else's job in place of its own subject, and #44 is the last of the three and is what would settle the shape. Where an editor of `ci.yml` meets the argument is unchanged — the `server-posture` header comment, which is now the only place it is argued rather than pointed at. `tests/wire/README.md` and `tests/matrix/README.md` both point at it and neither restates it, because the count had drifted in three places by the time #46 rebased onto #43.

**A required context must be produced unconditionally by every run of the workflow** — **map constraint `#13`**, which carries the conditional forms it covers, the reasoning, and the one escape hatch. It binds every future edit to `ci.yml`, not just this design, which is why it lands there rather than here.

The consequence this ADR owns: **the ruleset change cannot precede the jobs it requires.** Adding ~~eight~~ required contexts before ~~eight~~ jobs exist leaves every pull request pending indefinitely, including the one that would add them — which is why the enforcement scaffolding is deferred rather than merely sequenced.

~~Three~~ **Four** Compose bring-ups per pull request is the accepted cost; the ~~five~~ **six** Docker-free jobs run in parallel in under a minute, so wall time is set by the Compose jobs regardless.

## Options considered

1. **One `decide` with a defaulted resource.** One signature to learn, and it is what the ticket's own sketch implied. Rejected: silent truncation on argument absence, in a design whose other half is a fail-closed chain.
2. **A sentinel for the absent resource.** Keeps one entry point. Rejected: a handler can pass the sentinel as easily as it can omit an argument, and it creates an importable value whose only meaning is *skip two steps*.
3. **The resource judging itself.** Rejected: the policy function becomes a shell, and the action gets threaded in anyway.
4. **Layer 2 owning parameterised rule mechanisms.** Rejected: close to the domain-specific language map constraint `#4` refuses, with one instantiation each.
5. **A reason table with rows registered by layer 3 at composition.** Rejected: a mutable module-level registry, where a missing row fails at request time rather than import time.
6. **A per-tool batch flag on the `Action`.** Rejected on granularity — wrong on every single-item call — and on placing a transport concern on a record the policy function never reads.
7. **Splitting this into two ADRs**, layer contract and repository shape. Rejected: map constraint `#7` is one ADR per ticket, and ADR-0010 faced the same pressure and answered it without amending the constraint. Reopen on evidence — this document running past ADR-0010's length — rather than on anticipation.
8. **A fourth layer-2 reason for the directory miss.** Rejected: its record would be identical to `role_missing`'s, so it amends ADR-0002's closed vocabulary and ADR-0004's coupling table for a distinction carrying no different remedy.
9. **A realm user with no directory row, plus an attack-suite row.** Rejected: the seed would grow a row rendering into the realm but into neither the ERP nor the directory — a new shape in a flat literal file whose legibility is the point.
10. **Generators outside `src/`, in a top-level `provisioning/`.** Rejected: it guts the ejection proof, since provisioning would survive by sitting outside the blast radius rather than inside it; and import-linter's root package would not see the directory at all.
11. **A layer-2 directory table in Postgres.** Rejected: layer 2's only shipped implementation would be one the ejection test cannot run.

## Consequences

**ADR-0004 is discharged.** All five acceptance criteria and all four tabled couplings are closed here. Of the two *lesser* couplings it noted rather than tabled, the fixture generator's knowledge of domain field names is confirmed as a deliberate layer-3 instance rather than changed.

**Cost, taken deliberately.** Naming indirection between layers 2 and 3 that a reader must hold in their head, in a repository whose product *is* being readable. An abstraction with exactly one implementation, which is a known smell and will look like one. Three entry points where the ticket imagined one. And a residual fail-open that no signature closes, whose falsifier is two wire tests rather than a type.

**A `Decision`'s grounds never leave layer 2.** Layer 1 receives shape. The audit trail, which is not yet designed, is the artifact that will need grounds, and it should take them from the `Decision` rather than from the wire.

**The attack suite grows to 33 rows**, `basis: adr` 10 → 11, with `list_partition_scoped` added. Floor stays 11 and the retitle threshold is untouched; the soft ceiling of 35 is not crossed.

**Map constraint `#13` is added** — a required context must be produced unconditionally by every run of the workflow.

**Map constraint `#10` is answered**, and constraint `#12`'s walk date moves.

**Deferred to the build ticket, per this commit's documentation-only scope:** `src/mcp_erp/`, `.importlinter`, the ~~eight~~ jobs, `test_required_checks.py`, the `main` ruleset change, and ~~`docs/decision-matrix/matrix.yaml` itself~~ *(written 2026-08-20 by [#43](https://github.com/marcosfsousa/mcp-erp/issues/43), with the fixture generator that reads it and the `Decision matrix (wire)` job that drives it)*. The ruleset **cannot** land first: a required context whose job does not exist leaves every pull request pending indefinitely, including the one that would add the jobs.

**Input to other tickets.**

- **The build ticket** inherits the module layout, the two contracts, the ~~eight~~ jobs and the ruleset change, in that order.
- **The audit-trail work** inherits that grounds exist only inside layer 2, and that no entity carries a timestamp.
- **The write-up** inherits four lines recorded in [`docs/write-up-notes.md`](../write-up-notes.md).

# ADR-0013: Layer 3 declares what layer 2 decides, and layer 1 never learns why

- **Status:** Accepted
- **Date:** 2026-08-18
- **Ticket:** [#12 Settle module boundaries](https://github.com/marcosfsousa/mcp-erp/issues/12)
- **Evidence:** map constraints `#1`, `#4`, `#6`, `#7`, `#10`, `#12`; [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md), [ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md) (which handed this ticket five acceptance criteria and four tabled couplings), [ADR-0006](0006-fail-closed-in-a-fixed-order.md), [ADR-0007](0007-the-realm-is-the-exhibit.md), [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md), [ADR-0009](0009-not-built-is-not-unreachable.md), [ADR-0010](0010-the-clause-decides-the-row-the-removal-decides-the-split.md), [ADR-0012](0012-the-token-names-a-capability-never-a-role.md)

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

**Outcomes equal items requested.** A batch yields one outcome per item named in the request — permit or refusal, never a silent drop. This is what makes response mode a function of the request rather than of the data, and it is the invariant a future handler would break by filtering a batch instead of refusing its members.

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

The restatement is structural, not prose. Handlers **yield** outcomes; layer 1 consumes and keys the response mode on **cardinality** — one outcome answers `application/json`, more than one opens the stream. Layer 1 never learns which argument is the batch, nor that the tool is called `approve_requisition`. This is the idiom layer 1 already uses for refusals, keying on `denial_class` rather than on which rule fired.

**A per-tool flag on the `Action` is the wrong granularity.** ADR-0002: *"A single-item call answers with `application/json` instead, so one tool exercises both response modes."* The mode is a property of the call. A flag would also put a transport concern on a record the policy function never reads.

**Result rows are not outcomes.** A list returning three requisitions is one outcome containing three rows, so list tools never reach this decision. Determinism comes from *outcomes equal items requested* plus matrix rows fixing the request, and each matrix row carries its expected response mode.

### Handlers in layer 3, adapters in layer 1

A handler takes a `Principal` and parsed arguments, calls `load` and the chain, and returns a domain outcome or a refused `Decision` — never anything protocol-shaped. Layer 1 holds the three adapters ADR-0002 specified and renders what comes back, keyed on `denial_class`.

**Layers 1 and 3 import nothing from each other**; the composition root registers handlers with the protocol package. This is #5's handoff — *the refusal decision and the refusal shape are different concerns* — made physical.

**Layer 1 learns the shape of a refusal, never its grounds.** It sees `denial_class` and cardinality; it never sees which rule fired, against which attribute, on which row. That is the precise form of the title's claim.

### The gate chain sits in middleware, in two tiers

**A FastAPI dependency cannot gate the tool endpoint at all.** ADR-0008 settled that layer 1 is the official Python `mcp` 2.0.0 package, which supplies its own ASGI application. Under Starlette a mounted ASGI app is not a route — `mount()` takes a path, an app and a name, with no `dependencies` argument — and dependency solving happens inside a route handler a mount never enters. Middleware is the mechanism that reaches it. *Verified from documentation, not execution; it belongs with ADR-0009's first-run assertions.*

```python
app = FastAPI(routes=[
  Route("/.well-known/oauth-protected-resource/mcp", metadata),  # no token gate
  Mount("/mcp", mcp_asgi_app, middleware=[
      Middleware(ShapeGate),   # gate 2
      Middleware(TokenGate),   # gates 3, 4, then directory resolution
  ]),
])
app.add_middleware(OriginGate)  # gate 1, every path
```

The unauthenticated endpoints sit outside the token gate **structurally** rather than by a path allow-list — preferring an attack to be impossible over defended-against, the move ADR-0006 already made once. Gates 5 and 6 are the chain, at dispatch, where the `Action` is known.

**This closes ADR-0009's open condition from our side.** Its falsification case was *"if token verification lives inside the modern request path, the legacy leg is unauthenticated."* Validation now sits **above** era routing by construction, whatever the package does internally. The three seam assertions still run; they now confirm rather than discover.

Accepted cost: mount-level middleware is not wrapped by Starlette's exception-handling middleware, so challenges render themselves. They are `WWW-Authenticate` responses rather than exceptions, so this is arguably right anyway.

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

### Four test directories, named for artifacts

```
tests/
  authorization/   # in-process, layer 2 only, no Docker — the ejection target
  matrix/          # wire; plus the one union mapping test
  attack_suite/    # wire; 33 rows including ADR-0009's 3 basis:seam
  conformance/     # wire + outbound; the authorization code flow
```

**The ejection test is a command, not a file** — `rm -rf src/mcp_erp/purchase_to_pay && pytest tests/authorization` — so that directory imports nothing from layer 3, and this ticket's *"unit tests of the policy function"* are those same files. Layers 1 and 3 get no directory of their own; ADR-0008 routes every assertion about them over the wire.

### Both generators, split by the vocabulary each speaks

The **identity generator** lives in `authorization/`: it reads the seed's authored cast and renders directory rows and the authorization server's user import. The **fixture generator** lives in `purchase_to_pay/`: it reads the matrix definition and emits one requisition per row. Each is deleted with the layer whose words it uses, so ejection correctly removes the fixture generator while provisioning survives — ADR-0004's criterion 4 read literally rather than approximately.

They do not collide: ADR-0003 already splits the seed into *"the organisation is authored; the test data is generated"*, so each touches one half. ADR-0003's seam sentence — *"the seed generator reads the matrix, and the policy function reads neither"* — gains a successor: **each generator speaks one layer's vocabulary and is deleted with it; the policy function reads neither, and neither reads the other.**

Because the fixture generator ships in `src/`, the matrix definition cannot live under `tests/`. It is a committed data file at **`docs/decision-matrix/matrix.yaml`**, sibling to `docs/attack-suite/scenarios.yaml`. The two are disjoint and neither arbitrates the other: `scenarios.yaml` is canonical for named attacks, `matrix.yaml` for `(principal × tool × resource → expected)`. They share no rows. The one thing they touch is ADR-0002's reason-to-shape mapping, whose union test lives in `tests/matrix/`.

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

### Eight continuous-integration jobs, one per seam

| Job `name:` | A red check means | Compose |
| --- | --- | --- |
| Lint and types | ordinary Python defect | no |
| Layer boundaries | someone crossed a layer boundary | no |
| Layer 2 ejects clean | layer 2 no longer stands alone | no |
| Seed renders clean | a rendering diverged from the seed or the matrix | no |
| Required checks match the ruleset | the workflow and the ruleset disagree | no |
| Decision matrix (wire) | an authorization expectation is wrong | yes |
| Attack suite (wire) | a defence regressed | yes |
| Authorization code flow | the flow broke (preflight names external causes first) | yes + network |

**All eight contexts gate `main`.** Set equality holds in both directions, there is no exemption list to justify, and ADR-0008's *"a check that can never block becomes noise"* applies uniformly. ADR-0008 already committed the conformance job as the repository's first required status check.

*Seed renders clean* is the widened form of what was scoped as matrix-fixture drift: it now covers seed-to-directory and seed-to-realm as well, including the realm-versus-directory subject-set equality above. All three break for one reason — a rendering changed without the seed — so it is one seam and one diagnosis.

*Required checks match the ruleset* holds job names and required contexts equal in both directions. It is its own job because it must not sit on a cut path: cutting the decision matrix, third on cut order `#9`, removes *Decision matrix (wire)* and *Seed renders clean* together, and a name-contract test inside either would be cut in silence, taking the argument for required checks with it. *Lint and types* would hold it uncuttably but would then mean two unrelated things, against this table's own rule.

**A required context must be produced unconditionally by every run of the workflow.** This binds every future workflow edit, not just this design, so it lands as **map constraint `#13`** rather than as a sentence in an ADR about layers. It covers `paths:`, `paths-ignore:`, job-level `if:` and conditional matrix legs alike: each produces a context that never reports, and a rule waiting on one is indistinguishable from a rule that has not run — the pull request sits pending, reading as *still working* at exactly the moment it matters. The escape hatch, if measured wall time ever justifies it, is a step-level early exit inside a job that always runs; the condition is measured wall time, not anticipated.

Three Compose bring-ups per pull request is the accepted cost; the five Docker-free jobs run in parallel in under a minute, so wall time is set by the Compose jobs regardless.

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

**Deferred to the build ticket, per this commit's documentation-only scope:** `src/mcp_erp/`, `.importlinter`, the eight jobs, `test_required_checks.py`, the `main` ruleset change, and `docs/decision-matrix/matrix.yaml` itself. The ruleset **cannot** land first: a required context whose job does not exist leaves every pull request pending indefinitely, including the one that would add the jobs.

**Input to other tickets.**

- **The build ticket** inherits the module layout, the two contracts, the eight jobs and the ruleset change, in that order.
- **The audit-trail work** inherits that grounds exist only inside layer 2, and that no entity carries a timestamp.
- **The write-up** inherits four lines recorded in [`docs/write-up-notes.md`](../write-up-notes.md).

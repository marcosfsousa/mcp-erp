# ADR-0004: Layer 2 is a portable pattern; layer 3 is ejectable

- **Status:** Proposed — to be decided on the pull request that introduces it
- **Date:** 2026-08-06
- **Ticket:** none. A standing constraint, deliberately not raised through the map, so it is argued on its own merits rather than absorbed as a settled premise.
- **Evidence:** [ADR-0001](0001-off-the-shelf-clients-cannot-run-a-modern-only-server.md), [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md); map constraints #2, #3, #4, #6

## Question

The exhibit has three layers:

1. **Transport and protocol conformance** — Streamable HTTP, statelessness, response modes, the era split.
2. **Authorization** — token validation, the scope ∩ role intersection, row scoping, relationship rules, refusal shapes.
3. **Domain** — purchase-to-pay, its four entities, its roles, its cast.

Should the design *require* that layer 2 survives as a portable pattern and layer 3 detaches cleanly — so that cloning this repository for a different purpose means deleting layer 3 rather than untangling it? And if so, what makes that requirement falsifiable rather than aspirational?

Nothing decided so far forbids either property. Nothing enforces them either, and #12 as currently scoped could produce a defensible module layout that satisfies its own brief while failing this one.

## Decision (proposed)

Adopt both as standing constraints, and hand #12 the acceptance criteria below rather than leaving it to infer them.

### What already holds, and why this is cheap to adopt now

Every rule discovered so far that generalises was stated as a principle rather than as a fact about purchasing — a discipline ADR-0002's format imposed before anyone framed it as portability:

- Refusal shape follows the remedy.
- Caller-level refusals are whole-call; item-level refusals are per-item.
- Disclose the shape of the API; never the contents of the database.
- The scoping attribute is server-derived from the principal, never client-supplied — so out-of-scope writes are inexpressible rather than refused.
- Breadth is a role, not a wider membership.
- A remedy names a class of action, not an available human.
- `tools/list` filters on granted scope alone, making the listing a pure function of the token.

Not one of those mentions a requisition. That set *is* the layer-2 pattern, and it is already portable. The work below is not discovery; it is preventing erosion.

### The four couplings that would tear on ejection

| Coupling | What breaks |
| --- | --- |
| **The closed reason vocabulary** | A single enum mixing layers. `insufficient_scope`, `role_missing` and `not_found` are layer 2; `segregation_of_duties`, `over_threshold`, `already_decided` and `already_invoiced` are layer 3. Ejecting the domain means editing the vocabulary rather than deleting a module. `remedy` and both retry booleans stay portable — only the reason names do not. |
| **Row scoping written in domain vocabulary** | Specified throughout as "by cost centre". The mechanism — one equality check on a single-valued principal attribute plus one bypass role — is fully portable and simply is not named portably anywhere. |
| **The identity provisioning pipeline** | One seed file rendering into both ERP rows and the authorization server's user import is a layer-3-shaped artifact doing a layer-2 job. Eject the domain and user provisioning goes with it. |
| **Server-sent events on batch approval** | A layer-1 decision justified by a layer-3 fact, skipping layer 2 entirely: streaming is earned because a batch is N independent decisions with N outcomes. Eject purchasing and the demonstration needs another batch-shaped tool, or map constraint #6 loses the argument that makes its refusal of a standalone stream a position rather than an absence. |

Two lesser ones, noted rather than tabled: the fixture generator knows domain field names, and tool schemas are partly data-derived. Both are sound as patterns and currently exist only as domain-specific instances.

### Acceptance criteria for #12

1. **The policy function's signature is domain-free.** This is the load-bearing artifact and nothing has written it down. Something of the shape `decide(principal, action, resource) -> Decision`, with domain types behind an interface, makes layer 2 portable by construction and reduces everything else here to naming. A signature taking a requisition makes the principles above decorative.
2. **The reason vocabulary splits.** Layer 2 owns a fixed set plus an extension point; layer 3 contributes its own values. `remedy` and the retry booleans stay wholly in layer 2, since they describe client behaviour rather than domain facts.
3. **Row scoping is named after a principal attribute at the boundary**, with "cost centre" appearing only on the layer-3 side of it.
4. **A principal directory is a layer-2 seam** — layer 2 defines the shape mapping an issuer-and-subject pair to roles and a scoping attribute; layer 3 supplies the rows. Provisioning then survives ejection.
5. **The streaming justification is restated in layer-2 terms** — a tool whose call yields N independent outcomes — so the argument survives a different domain.

### The falsifiable form

The constraint is met when **deleting the layer-3 module leaves layer 2 building and its own tests passing**, with only the extension points unfilled. That is checkable, and it is the only version of this that cannot quietly rot.

## Options considered

1. **Leave it as an intention.** Costs nothing today. Every subsequent ticket is then free to erode it without noticing, and the erosion is invisible until someone actually tries to clone the repository — the one moment the property is expensive to add.
2. **Record it in the map's *Already settled* section.** The natural home for a standing constraint, and rejected on purpose: absorbed there it becomes a premise nobody argued, whereas here it arrives with a diff, a rationale and a place to disagree. If accepted, a pointer can be added afterwards.
3. **Extract layer 2 as its own package now.** The strongest possible proof, and premature: there is no second consumer, and a package with one consumer tends to acquire exactly the abstractions its single consumer needs.
4. **Enforce mechanically** — an import-linter rule failing continuous integration when layer 2 imports layer 3. Cheap, and genuinely falsifiable rather than reviewer-dependent. Left open below rather than decided here, because it is a build-tooling choice #12 is better placed to make.

## Consequences

**Cost.** Naming indirection between layers 2 and 3 that a reader must hold in their head, in a repository whose product *is* being readable. An abstraction with exactly one implementation, which is a known smell and will look like one. And a fifth thing every subsequent ticket has to be checked against.

**What it buys.** The layer-2 pattern is the part of this exhibit with reuse value beyond the portfolio, and the ejection test is the only thing that keeps that claim honest rather than asserted.

**Input to other tickets.**

- **#12 (module boundaries)** inherits the five acceptance criteria and the ejection test, and should decide whether to enforce them mechanically.
- **#11 (scope granularity)** should say whether the scope *scheme* is a pattern or merely a naming convention — scope strings are inevitably domain-shaped, so the portable part is the scheme.
- **#9 (attack suite)** is unaffected: every scenario cites a specification clause, which is layer 1 or 2 by construction.

**If rejected**, ADR-0003's identity pipeline and ADR-0002's reason vocabulary stand exactly as written, and the couplings above should be recorded as accepted rather than left undocumented.

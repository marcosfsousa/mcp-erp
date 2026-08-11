# ADR-0009: Not built is not unreachable

- **Status:** Accepted
- **Date:** 2026-08-11
- **Ticket:** [#8 Decide what performs the run](https://github.com/marcosfsousa/mcp-erp/issues/8)
- **Evidence:** [ADR-0006](0006-fail-closed-in-a-fixed-order.md) (the gate order), [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) (the substrate this follows from), [ADR-0001](0001-off-the-shelf-clients-cannot-run-a-modern-only-server.md); [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md); map constraints #4, #8, and the standing *legacy: discussable, not built*; official Python `mcp` 2.0.0 documentation, read 2026-08-11

## Question

The map has always said one thing about the legacy era: **discussable, explicitly not built.** That sentence was written when not building it meant it would not be there.

[ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) chose a substrate on which both eras are always on and neither can be disabled, with routing on `MCP-Protocol-Version` happening before any handler is reached and an absent header routing as legacy. So the era is now in a third state the map never named: **not built, and reachable.**

For an exhibit whose entire subject is authorization, that is the question a technical reader would go looking for. Is the legacy era inside the threat model, and what does the server do with it?

## Decision

**The legacy era is inside the threat model, and it is authorized identically.** Nothing is built for it. What is added is proof that it does not bypass.

### Refusing it at the edge was genuinely available, and was not taken

The protocol package offers no switch, but that is a statement about the package, not about what is possible. Middleware ahead of the application can read `MCP-Protocol-Version` and reject before routing ever happens, and ADR-0001 already specified the refusal's shape — *return a helpful error naming supported versions*, which the specification notes may be the only diagnostic a legacy client can surface.

It was rejected because it undoes the argument that decided the substrate. Serving both eras is what lets a reader point their own client at this server and have it work, which is what turned research 0004's dominant failure mode — *auth succeeds, protocol fails* — from a caveat into a non-event, and what upgraded the witnessed third-party leg from a partial success to a full one. Buying back a clean modern-only story at that price is buying the wrong thing.

### The gate chain is not uniform across the two legs, and the shape gate is where it breaks

ADR-0006's order is the security property:

```
1. Origin invalid                        -> 403
2. required headers missing / mismatched -> 400 + -32020
3. method is server/discover?            -> skip 4
4. token absent or invalid               -> 401 + challenge
5. scope insufficient                    -> 403 + insufficient_scope
6. domain rule                           -> -31010 or tool result
```

Step 2 exists to make step 3 safe. Granting the `server/discover` exemption on a caller-controlled header before proving header and body agree is an authentication bypass, and ADR-0006 fixed the order so the attack is structurally impossible rather than defended against.

A legacy-era request carries **none of those headers** — no `MCP-Protocol-Version`, no `Mcp-Method`, no `Mcp-Name`. On that leg step 2 has nothing to check and step 3 has nothing to key on. **The shape gate is a structural no-op there**, and what carries the leg is steps 4, 5 and 6 — token, scope, domain.

That is a different chain, not the same chain with a fast path, and the amendment to ADR-0006 says so plainly rather than describing one order that holds everywhere.

### Three assertions, and they exist to falsify rather than to sample

Three scenarios, at the seam:

1. An unauthenticated legacy-era call is refused.
2. An under-scoped legacy-era call produces the **same denial class** as its modern twin.
3. A legacy-era request cannot claim `server/discover`'s exemption.

**These are not spot-checks on coverage, and reading them that way would understate what they are for.** The open question underneath this whole decision is *where the protocol package applies token verification relative to era routing* — and that cannot be settled from documentation. If verification is middleware wrapping the whole application, both legs are covered and all three pass on the first run. If it lives inside the modern request path, the legacy leg is unauthenticated and this ADR is wrong.

So the assertions are written to fail loudly in the second case. Their value is concentrated entirely in the first run, and the design deliberately front-loads them rather than deferring them behind the matrix.

The third assertion earns its place separately from the first two. *Cannot claim the exemption* is a claim about **why**: the exemption is keyed on a header the legacy leg does not carry, so the refusal should follow from absence rather than from a default that could be changed without anyone noticing.

### If they falsify, this decision reopens

If token verification turns out not to sit ahead of era routing, the answer changes rather than the wording. Refusing the era at the edge becomes the live option again, and the cost accounting above — which trades a clean modern-only story for third-party reach — has to be redone against a leg that is genuinely open rather than merely undescribed.

That is recorded here as a condition, not a risk to be managed, so that whoever runs the assertions first knows what a red one means.

## Options considered

1. **Refuse the legacy era at the edge**, with ADR-0001's helpful error. Restores modern-only as a real property and makes ADR-0006's order the whole story; reverses the argument that decided the substrate, and puts every off-the-shelf client back outside the door.
2. **Re-run every decision-matrix row and every attack scenario once per era.** The strongest possible coverage claim; roughly doubles the wire suite, needs a legacy-era client in the suites, and makes the era genuinely *built* — which the map forbids.
3. **Re-run the attack suite alone on the legacy leg**, leaving the matrix modern-only. The intermediate; still a legacy-era client to build and maintain, for scenarios that overwhelmingly assert on header rules the leg does not have.
4. **Document it as an inherited surface and assert nothing.** Cheapest, and honest as far as it goes; leaves an always-on, unproven authorization surface in a project whose entire point is authorization.

## Consequences

**Cost.** Three scenarios asserting on a protocol era the exhibit otherwise refuses to design against, which needs a paragraph of explanation or it reads as scope creep. A second request shape in the suites that exists only to be refused. And an authorization story that takes two sentences instead of one, because the honest version has a branch in it.

**An amendment to ADR-0006, and a correction inside it.** That document's *Input to other tickets* passes #12 a refinement: *"a legacy client's `initialize` carries none of the required headers, so under this order it receives `400` + `-32020` rather than the more informative `-32022` with a supported-version list."* On this substrate that is **void**. Era routing precedes the gate chain entirely, so a legacy `initialize` is routed to the legacy transport and never reaches step 2 at all. The observation was correct for the modern-only server it was written against; it describes a request path that no longer exists.

**The write-up gains its sharpest available paragraph on inheritance.** *Not built* and *not present* came apart the moment a dependency decided the second one. The general form — that choosing a dependency can silently enlarge your threat model, and that the enlargement is invisible precisely because you wrote no code for it — is more transferable than anything else in this ticket, and it is worth the space.

**Input to other tickets.**

- **#9 (attack suite)** owns where these three live. They are protocol-era scenarios rather than clause-citing refusals, so they may sit beside the suite rather than inside it — but the suite's protection from cuts should follow them wherever they land, since the whole point is that they run early and keep running.
- **#12 (module boundaries)** inherits the amended pipeline, and should note that the two legs converge at token validation rather than at the front door.

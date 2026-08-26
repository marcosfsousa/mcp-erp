# ADR-0006: Fail closed, in a fixed order

- **Status:** Accepted
- **Date:** 2026-08-11
- **Ticket:** [#7 Choose the authorization server](https://github.com/marcosfsousa/mcp-erp/issues/7)
- **Evidence:** [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md) (fifteen-clause list, §2.2 path insertion, §2.4 challenge parameters), [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md); RFC 9728 §3.1, RFC 6750 §3, RFC 9700 §4.14.2; [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md)
- **Amended:** 2026-08-11 — substantive, by [#8](https://github.com/marcosfsousa/mcp-erp/issues/8). The chain below is **not uniform across both protocol eras**, and one refinement passed to #12 is void. See *The order describes the modern leg* and *Input to other tickets*. No decision here is reversed.
- **Amended:** 2026-08-18 — additive, by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12). A **resolution step** sits between gates 4 and 5, and the chain runs in mount-level middleware rather than in a route dependency. See *The gate order is a security property, not a style choice*. No decision here is reversed.
- **Amended:** 2026-08-19 — additive, by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which built the validator. The rejection vocabulary gains a **seventh** value, `issuer_mismatch`. See *Refusals disclose the caller's own token, and nothing else*. No decision here is reversed.
- **Amended:** 2026-08-19 — additive, by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which deployed it. One resource identifier means **one published address**, which is why two replicas answer behind a gateway. The derivation was argued only in `gateway/README.md`. See *Discovery is published both ways, at one address*. No decision here is reversed.
- **Amended:** 2026-08-26 — substantive, by [#93](https://github.com/marcosfsousa/mcp-erp/issues/93), which ran MCP Inspector against this server rather than reading its source. **A third-party client does send an `Origin`**, and gate 1 refuses it. Inspector 2.1.0's web interface connects from the browser, not through its proxy, so the *no client in this exhibit ever sends an `Origin`* limit below is withdrawn and the hop table gains a row. The gate, the empty allow-list and the order are unchanged; what changes is that the check now has a demonstrated positive case instead of only a negative scenario. See *`Origin`: absent passes, present must prove itself* and *An honest limit*. No decision here is reversed.
- **Amended:** 2026-08-21 — additive, by [#82](https://github.com/marcosfsousa/mcp-erp/issues/82), which found two refusals naming a cause this server had not established. **The issuer step is two questions**: an absent `iss` is `malformed` and a wrong one is `issuer_mismatch`, where a single comparison had answered `issuer_mismatch` to both. And **the key-set refetch suppresses every failure rather than four named ones** — the hand-written list did not cover what `PyJWKSet.from_dict` raises, so an unreadable key set left the token gate as a `500` carrying our own infrastructure, which is the one outcome that suppression exists to prevent. See *Refusals disclose the caller's own token, and nothing else*. The vocabulary and the gate order are unchanged and no decision here is reversed.

## Question

ADR-0005 put the hard `MUST`s on the resource server. This is the ADR that says what it actually does with a request: what it validates, what it publishes, what it discloses when it refuses, and — the part that turned out to carry a security property rather than a style preference — **in what order**.

## Decision

### Tokens are validated locally, and every failure closes

Signature, issuer, expiry and audience are checked **in our own code**, against the key set published by the authorization server. Introspection was rejected: it moves signature and expiry checking inside Keycloak, deleting the very code this exhibit exists to display, and it would reduce the audience check to a field comparison on someone else's answer rather than the fail-closed validator #3 committed to.

The conceded cost is stated plainly: **revocation is bounded only by token lifetime** (five minutes — see [ADR-0007](0007-the-realm-is-the-exhibit.md)).

### The key set is refetched on a miss, not on a timer

Rotation is not theoretical here. ADR-0007's realm boots from an empty in-memory database, so **Keycloak mints new signing keys on every restart** and the resource server routinely meets a key identifier it has never seen.

```
token names an unknown key identifier?
  cooldown elapsed  -> fetch the key set once, retry the lookup
  cooldown active   -> reject
fetch fails         -> reject
```

A fixed refresh interval alone would mean every Keycloak restart produces a window of blanket failure — with an empty database that is not an edge case, it is every boot. The cooldown is what stops the same mechanism becoming an amplifier: without it, anyone can force outbound fetches by sending tokens with random key identifiers.

### Clock skew is asymmetric, because the two directions are not the same risk

Zero leeway on expiry. Thirty seconds on the not-yet-valid claims.

Rejecting a token that appears to start slightly in the future is a liveness bug and costs nothing to forgive. Accepting one that has expired is a security window — the same window revocation already concedes. Keeping expiry exact also keeps ADR-0007's ten-second probe client honest: with the conventional 60-second leeway, a ten-second token stays valid for seventy, and the expiry scenario would either become a seventy-second wait or assert something untrue.

### Discovery is published both ways, at one address

Both mechanisms the specification offers: the `WWW-Authenticate` challenge carries `resource_metadata`, **and** the document is served at a well-known address. The server need only implement one; clients must support both, and implementing both costs little once the document exists.

The address is **path-inserted, and only path-inserted**. RFC 9728 §3.1 requires the well-known segment between host and path, not appended — research 0003 calls it *"the single most commonly mis-implemented line in the whole discovery chain"*.

```
resource identifier: http://localhost:8080/mcp

GET /.well-known/oauth-protected-resource/mcp   -> 200
GET /.well-known/oauth-protected-resource       -> 404, deliberately
GET /mcp/.well-known/oauth-protected-resource   -> 404, wrong shape
```

The bare root is refused rather than offered as a convenience: that address describes a resource identifier with no path component, which is a *different resource* from ours. Serving our document there would be a conformance error dressed as helpfulness.

The document declares the two required fields plus three that earn their place:

```json
{
  "resource": "http://localhost:8080/mcp",
  "authorization_servers": ["http://keycloak:8081/realms/mcp-erp"],
  "scopes_supported": ["..."],
  "bearer_methods_supported": ["header"],
  "resource_documentation": "..."
}
```

`scopes_supported` publishes the scope vocabulary. `bearer_methods_supported: ["header"]` turns attack-suite clause #5 — a token in the query string — from a behaviour we merely exhibit into a **published contract we then keep**. `resource_documentation` is where a reviewer goes next. `offline_access` is deliberately absent: the specification says a protected resource **SHOULD NOT** list it, since refresh tokens are not a resource requirement.

#### One identifier, therefore one published address

*Added 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which deployed the server. This section already fixed the identifier and the document; what it did not say is what the identifier costs at deployment time.*

`http://localhost:8080/mcp` above is not only a name. It is the value [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md) puts in every token's `aud` via the realm's audience mapper, and the value this server compares that `aud` against — so a caller who reaches the server at any other address is holding a token whose audience names an address they did not use. The identifier is therefore **one URL in the deployment sense**, not merely one string in a document.

Two replicas follow from map constraint `#5`, which wants statelessness falsifiable rather than asserted. **One identifier plus two replicas forces something in front of them**, because Compose publishes a host port to one container. So the exhibit runs a gateway, and the two replicas publish no port of their own.

The alternative was two replicas on two host ports. It fails on this section's own terms: the audience would name a port no caller used, and the audience check is the load-bearing control — the normative register's *Resource indicators unhonoured* deviation records that Keycloak does not honour RFC 8707's `resource` parameter, so the resource server's own comparison is all there is. Making that comparison pass against an address the caller did not reach would hollow it out while leaving it green.

**The consequence is a deployment fact, not a protocol one**, which is why it lands here as a corollary rather than as a decision of its own: nothing about the wire changes, and a reader who deploys this behind any single-address load balancer has satisfied it. `gateway/README.md` holds the nginx mechanics — why two upstreams are named individually rather than scaled, and why one worker makes the rotation observable — and points here for why there is one address at all.

### Refusals disclose the caller's own token, and nothing else

RFC 6750 draws a line worth honouring: a request carrying **no credentials at all** gets a challenge with no error code — nothing is wrong with the token, there simply isn't one. An error code belongs only where a token was presented and rejected.

```
no token:
  WWW-Authenticate: Bearer resource_metadata="...", scope="..."

token rejected:
  WWW-Authenticate: Bearer error="invalid_token",
                    error_description="<one of>", resource_metadata="..."

  token_expired | audience_mismatch | audience_missing
  | signature_invalid | unknown_key | malformed
  | issuer_mismatch
```

The vocabulary is closed, for the same reason ADR-0002 closed its refusal reasons: the attack suite asserts on a fixed identifier rather than on prose someone will later reword. ~~Four of those six are named scenarios~~ **every value here is reached by a named scenario** *(count restated 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37), which added the seventh; a stored count in a list that grows is the defect this trail keeps finding in itself)*, and without distinguishable descriptions they would all assert the same `401`.

Nothing here discloses anything ADR-0002's rule protects. Every fact in play is a property of the caller's own token, which they already hold.

*Amended 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37) — a seventh value, `issuer_mismatch`, added while building the validator this section specifies.*

**The six above have no member for a token from another issuer, and without one the `iss` check is unobservable.** `foreign_issuer_token`'s recorded removal is *"skip the `iss` check against the configured issuer"*, and the neighbour realm signs with its own keys — so a server that had deleted the comparison would still refuse that token, as `unknown_key`, and the row would stay green on its own removal. Every row records the exact deletion that makes it pass; a deletion nothing can see is not one.

So the check runs **before** the key lookup, against the token's unverified payload, and refuses with its own word. Reading an unverified claim there is safe for the same reason reading the unverified key identifier is: it selects *which* key must have signed this token, and lying about it only brings a caller to a signature check they cannot pass. The order is structure, then issuer, then key, then signature and the remaining claims.

This is an addition to a closed vocabulary rather than a reversal of the closure. The rule the closure exists for is unchanged — the set is fixed, declared in one place, and every member is a property of the caller's own token. **One member is deliberately absent even so**: there is no value for *not yet valid*, because the thirty-second leeway above is what that clause is about and no client of this realm can produce a token beyond it. The residual is refused as `malformed`, and a member nothing can reach would weaken the claim that this vocabulary is observable rather than strengthen it.

*Amended 2026-08-21 by [#82](https://github.com/marcosfsousa/mcp-erp/issues/82).* **The issuer step is two questions, and only one of them is a comparison.**

The step above was built as `unverified.get("iss") != issuer`, which is true of a token carrying no `iss` at all — so an absent claim was refused `issuer_mismatch`, naming a comparison this server never made. `iss` is in the required claims, so the honest word is `malformed`: nothing was mismatched, something was missing. The check for absence runs first and answers `malformed`; the comparison runs second and answers `issuer_mismatch`.

**The vocabulary is untouched and so is the order** — no member is added, none is retired, and structure-then-issuer-then-key still holds. It is also why the absent case is answered *here* rather than left to the decode's own required-claims list, which would reach the same word one gate too late: the key lookup and the signature check run in between, so a token with no `iss` and an unpublished `kid` would have been refused `unknown_key` — a third cause, and no truer than the other two. Both halves are asserted together, because `foreign_issuer_token`'s recorded removal stays observable only while the two words differ.

### `server/discover` answers without a token, and says nothing about purchasing

Whether a server may require a token for `server/discover` is explicitly unresolved by the specification. We answer without one, because **era detection happens before authorization**: Claude Code's modern path works by probing `server/discover`, and tier 3 is the only evidence ADR-0001 has for its central claim. Putting that probe behind a `401` would rest the exhibit's third-party evidence on recovery behaviour nobody has tested.

Because it is the one endpoint that answers strangers, its `instructions` describe the protocol and authorization surface only. Constraint #10's deletion test applies hardest exactly where the unauthenticated public can read it: a portable layer-2 pattern whose public face narrates requisitions is not portable.

### The gate order is a security property, not a style choice

```
1. Origin invalid                        -> 403
2. required headers missing / mismatched -> 400 + -32020
3. method is server/discover?            -> skip 4
4. token absent or invalid               -> 401 + challenge
5. scope insufficient                    -> 403 + insufficient_scope
6. domain rule                           -> -31010 or tool result
```

*Amended 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12) — one step is added to the list above, and it is not a gate.*

**Between 4 and 5 the server resolves a `Principal`.** [ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md) makes the principal directory a layer-2 seam, and its lookup runs inside the token middleware immediately after gate 4, putting the resolved `Principal` in request state for gates 5 and 6 to read. This ADR orders *gates* — refusals keyed on what would fix them — and this is a **resolution step**, which is why it carries no number.

It is placed here rather than at dispatch because it is conditional on nothing dispatch knows, and because `tools/list` and `tools/call` share one scope check precisely so that one rule has one implementation; resolving at dispatch would give it two.

**A directory miss is an explicit refusal, not an empty principal.** A principal with no roles would clear gate 5 and then clear a role check demanding nothing — map note `#6` makes submitting scope-only and note `#11` leaves `erp.write` ungated — so an unknown subject holding `erp.write` would write a requisition charged to a null cost centre. That is a fail-open in a chain named for failing closed. `Principal.partition` is therefore non-optional, making a miss structurally unable to produce a `Principal`, and the refusal reuses `role_missing`, whose record it shares exactly.

The chain also runs in **mount-level middleware** rather than a route dependency: ADR-0008's substrate supplies its own ASGI application, and a mounted application is not a route, so dependency solving never reaches it. The unauthenticated endpoints sit outside the token gate structurally rather than by a path allow-list — the same preference for impossible over defended-against that produced the ordering argument below.

The specification says *"MCP servers **MUST** validate access tokens before processing the request"*, which reads as *token first*. The exemption above cuts across it: something must establish **which method this is** before the token check can decide whether to run, and the method arrives in a caller-controlled header.

**Taken naively that is an authentication bypass.** Send `Mcp-Method: server/discover` with `tools/call` in the body; if the exemption is granted on the header and header/body consistency is checked afterwards, the token check never runs on a tool call. The fix is ordering rather than a special case: prove header and body agree **first**, and the attack becomes structurally impossible rather than defended against. We therefore read the `MUST` as *"do not act on the request"*, not *"do not parse it"* — and parsing is unavoidable regardless, since `-32020` is itself a mandated response to an unauthenticated caller.

### The order describes the modern leg

*Amended 2026-08-11 by [#8](https://github.com/marcosfsousa/mcp-erp/issues/8).*

This ADR was written against a modern-only server. [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) chose a substrate that serves **both protocol eras from one endpoint**, routing on `MCP-Protocol-Version` before any handler is reached, with no way to disable an era. The chain above is therefore the **modern leg's** chain, and stating it as though it held everywhere would be the more comfortable description rather than the true one.

A legacy-era request carries none of the headers steps 2 and 3 read — no `MCP-Protocol-Version`, no `Mcp-Method`, no `Mcp-Name`. **Step 2 is a structural no-op on that leg**, and step 3 has nothing to key on. What carries the legacy leg is steps 4, 5 and 6: token, scope, domain. The two legs converge at token validation, not at the front door.

Nothing above is reversed. The ordering argument still holds exactly where the exemption exists, which is the modern leg — the exemption is what step 2 was protecting, and the leg without the exemption does not need the protection. [ADR-0009](0009-not-built-is-not-unreachable.md) owns the consequence, and carries the three assertions that establish whether token validation genuinely spans both legs, which cannot be settled from documentation.

### `Origin`: absent passes, present must prove itself

A browser attaches `Origin` to cross-origin requests automatically and a page cannot forge it. Non-browser clients send none. The rebinding threat is specifically a malicious page in a victim's browser reaching a server on their machine — the case that *does* carry the header.

So: absent passes; present is checked against an allow-list that **ships empty**. Every real client is unaffected and every browser-originated request gets a `403`. The emptiness is the position, not an unfinished configuration.

**Verified rather than assumed, because it lands on the witnessed demo.** MCP Inspector's browser never reaches our server. `clients/web/src/lib/environmentFactory.ts` routes *"transport / fetch / logger all through the in-process Hono backend at `window.location.origin`"*; code search finds no browser-direct transport and no direct-connection mode. The outbound leg is `core/mcp/node/transport.ts`, whose only header source is the user's own Settings → Headers list, and Node's fetch — unlike a browser's — adds no `Origin`. The `ALLOWED_ORIGINS` machinery in that repository is Inspector protecting *its own* backend from the browser hop, the opposite direction. Claude Code is likewise a Node process.

| Hop | Made by | Carries `Origin`? |
| --- | --- | --- |
| Browser UI → Inspector backend | browser fetch | yes |
| Inspector backend → our server | Node in `createTransportNode` | **no** |
| Inspector 2.1.0 web UI → our server | browser fetch, direct | **yes** |

**The verification above was read, not run, and 2.1.0 does not behave that way.** *Added 2026-08-26 by [#93](https://github.com/marcosfsousa/mcp-erp/issues/93), which executed it.* Inspector 2.1.0's web interface connects to the target server **from the browser** rather than through its own backend — the gateway log records a Firefox user agent arriving at `/mcp` directly. So the third row above exists, and gate 1 refuses it:

```
curl -X OPTIONS http://localhost:8080/mcp -H 'Origin: http://localhost:6274'
→ 403 Forbidden    "Origin not allowed"
```

`app.py:226` adds the gate with no `allowed_origins`, so the preflight is refused, no CORS headers are emitted, and the interface sits at *connecting…* with no error. **The gate is working.** A shipped third-party browser client reaching a server on the operator's machine is precisely the rebinding shape the empty allow-list is the position on, and it is now demonstrated rather than only asserted.

What it costs is one route into this exhibit: Inspector's **command line** is the written path in [the walkthrough](../walkthrough.md), and its web interface cannot be used against this server without adding an origin to a list whose emptiness is the decision. Claude Code is unaffected and remains a Node process.

## Options considered

1. **Token introspection on every request.** Authoritative and immediately revocation-aware. Rejected for a round trip, a hard per-request dependency on the authorization server, and the deletion of the centrepiece.
2. **Local validation on reads, introspection on writes.** A defensible real-world trade, and two validation paths to write, test and explain — with the attack suite forced to assert which path each scenario exercises.
3. **A fixed key-set refresh interval**, with no miss-driven fetch. Trivially simple and inherently rate-limited; it also fails every request for the length of the interval after each Keycloak restart.
4. **Conventional 60-second leeway both ways.** Nobody would question it, and it would break the ten-second expiry probe and widen the conceded revocation window for a clock disagreement this deployment cannot have.
5. **Serving the metadata document at the root address too.** Maximises the chance a client finds it, at the cost of publishing a document that describes a resource identifier we do not have.
6. **A uniform `invalid_token` with no description.** Concedes nothing to a prober, and leaves four named scenarios asserting one indistinguishable response.
7. **Authenticating `server/discover` like everything else.** The purest posture, and an attack scenario in its own right — rejected because it puts era detection behind authorization and the exhibit's only third-party evidence on unverified recovery behaviour.
8. **Token check before shape validation**, the most literal reading of the `MUST`. Rejected because the exemption would then rest on an unvalidated caller-controlled header, needing a dedicated guard that the chosen order gets for free.
9. **Requiring an `Origin` header on every request.** The strictest reading, and it rejects all three proof tiers at the first gate.

## Consequences

**A correction to ADR-0002.** It justifies the "unlisted tool called anyway → `403` naming the tool and the scope" rule with *"tool names and scope names are already published unauthenticated in the protected-resource metadata."* **RFC 9728 has no field that publishes tool names**, and `tools/list` requires a token. The reasoning survives; the stated evidence does not. The repaired claim: the refusal names a **scope** that is genuinely published in `scopes_supported`, and confirms a **tool name the caller themselves supplied**. Neither is a fact only the database holds.

**~~An honest limit.~~ Withdrawn 2026-08-26 by [#93](https://github.com/marcosfsousa/mcp-erp/issues/93).** This read: *No client in this exhibit ever sends an `Origin`, so the check is exercised **only** by the negative scenario. No positive path covers it, and the write-up says so rather than implying otherwise.* MCP Inspector 2.1.0's web interface is a real, shipped, third-party client that sends one and is refused — see the table above. The limit was true of the clients this exhibit **drives** and false of one it **documents**, which is a distinction the sentence did not make.

**Cost.** A rate limiter, a cooldown and a negative path to test on a mechanism that fires once per Keycloak restart. A seventh closed vocabulary to keep honest. A deliberate `404` that reads as an oversight unless explained. And an asymmetry in clock handling that a reviewer will assume is sloppiness until told it is a position.

**Input to other tickets.**

- **#9 (attack suite)** gains `auth_bypass_via_method_header_mismatch` — the ordering hazard above, which is worth a scenario whichever order had been chosen.
- **#11 (scope granularity)** owns `scopes_supported`, which the metadata document publishes and must not misrepresent.
- **#12 (module boundaries)** inherits the pipeline as a seam. ~~One refinement: a legacy client's `initialize` carries none of the required headers, so under this order it receives `400` + `-32020` rather than the more informative `-32022` with a supported-version list.~~ **Void, 2026-08-11 ([#8](https://github.com/marcosfsousa/mcp-erp/issues/8)):** era routing precedes this chain entirely, so a legacy `initialize` reaches the legacy transport and never arrives at step 2. The observation was correct for the modern-only server it was written against, and describes a request path that no longer exists.

**Not contradicted:** ADR-0001 (era detection stays reachable), ADR-0004 (`server/discover`'s public face is domain-free by construction).

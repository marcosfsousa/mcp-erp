# ADR-0006: Fail closed, in a fixed order

- **Status:** Accepted
- **Date:** 2026-08-11
- **Ticket:** [#7 Choose the authorization server](https://github.com/marcosfsousa/mcp-erp/issues/7)
- **Evidence:** [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md) (fifteen-clause list, §2.2 path insertion, §2.4 challenge parameters), [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md); RFC 9728 §3.1, RFC 6750 §3, RFC 9700 §4.14.2; [ADR-0002](0002-refusal-shape-follows-the-remedy.md), [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md)

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
```

The vocabulary is closed, for the same reason ADR-0002 closed its refusal reasons: the attack suite asserts on a fixed identifier rather than on prose someone will later reword. Four of those six are named scenarios, and without distinguishable descriptions they would all assert the same `401`.

Nothing here discloses anything ADR-0002's rule protects. Every fact in play is a property of the caller's own token, which they already hold.

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

The specification says *"MCP servers **MUST** validate access tokens before processing the request"*, which reads as *token first*. The exemption above cuts across it: something must establish **which method this is** before the token check can decide whether to run, and the method arrives in a caller-controlled header.

**Taken naively that is an authentication bypass.** Send `Mcp-Method: server/discover` with `tools/call` in the body; if the exemption is granted on the header and header/body consistency is checked afterwards, the token check never runs on a tool call. The fix is ordering rather than a special case: prove header and body agree **first**, and the attack becomes structurally impossible rather than defended against. We therefore read the `MUST` as *"do not act on the request"*, not *"do not parse it"* — and parsing is unavoidable regardless, since `-32020` is itself a mandated response to an unauthenticated caller.

### `Origin`: absent passes, present must prove itself

A browser attaches `Origin` to cross-origin requests automatically and a page cannot forge it. Non-browser clients send none. The rebinding threat is specifically a malicious page in a victim's browser reaching a server on their machine — the case that *does* carry the header.

So: absent passes; present is checked against an allow-list that **ships empty**. Every real client is unaffected and every browser-originated request gets a `403`. The emptiness is the position, not an unfinished configuration.

**Verified rather than assumed, because it lands on the witnessed demo.** MCP Inspector's browser never reaches our server. `clients/web/src/lib/environmentFactory.ts` routes *"transport / fetch / logger all through the in-process Hono backend at `window.location.origin`"*; code search finds no browser-direct transport and no direct-connection mode. The outbound leg is `core/mcp/node/transport.ts`, whose only header source is the user's own Settings → Headers list, and Node's fetch — unlike a browser's — adds no `Origin`. The `ALLOWED_ORIGINS` machinery in that repository is Inspector protecting *its own* backend from the browser hop, the opposite direction. Claude Code is likewise a Node process.

| Hop | Made by | Carries `Origin`? |
| --- | --- | --- |
| Browser UI → Inspector backend | browser fetch | yes |
| Inspector backend → our server | Node in `createTransportNode` | **no** |

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

**An honest limit.** No client in this exhibit ever sends an `Origin`, so the check is exercised **only** by the negative scenario. No positive path covers it, and the write-up says so rather than implying otherwise.

**Cost.** A rate limiter, a cooldown and a negative path to test on a mechanism that fires once per Keycloak restart. A seventh closed vocabulary to keep honest. A deliberate `404` that reads as an oversight unless explained. And an asymmetry in clock handling that a reviewer will assume is sloppiness until told it is a position.

**Input to other tickets.**

- **#9 (attack suite)** gains `auth_bypass_via_method_header_mismatch` — the ordering hazard above, which is worth a scenario whichever order had been chosen.
- **#11 (scope granularity)** owns `scopes_supported`, which the metadata document publishes and must not misrepresent.
- **#12 (module boundaries)** inherits the pipeline as a seam, and one refinement: a legacy client's `initialize` carries none of the required headers, so under this order it receives `400` + `-32020` rather than the more informative `-32022` with a supported-version list. That is a protocol-layer improvement, not an authorization one.

**Not contradicted:** ADR-0001 (era detection stays reachable), ADR-0004 (`server/discover`'s public face is domain-free by construction).

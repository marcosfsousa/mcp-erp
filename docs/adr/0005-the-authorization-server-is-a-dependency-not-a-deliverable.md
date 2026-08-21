# ADR-0005: The authorization server is a dependency, not a deliverable

- **Status:** Accepted
- **Date:** 2026-08-11
- **Ticket:** [#7 Choose the authorization server](https://github.com/marcosfsousa/mcp-erp/issues/7)
- **Evidence:** [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md), [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md); [ADR-0001](0001-off-the-shelf-clients-cannot-run-a-modern-only-server.md); map constraints #1, #5, #8, #9; live verification against Keycloak 26.7.1, 2026-08-11
- **Amended:** 2026-08-15 — substantive, by [#10](https://github.com/marcosfsousa/mcp-erp/issues/10). Deviation 2's *"property of the local harness, not of the design"* framing is **withdrawn** and replaced with *not closed here*, with the route that would close it named; one *Input to other tickets* entry is void. See *Deviations 2* and *Consequences*. No decision here is reversed.
- **Amended:** 2026-08-19 — cosmetic, by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37). One cross-reference: this ADR says the audience is the resource's own URL without fixing that URL, and [ADR-0006](0006-fail-closed-in-a-fixed-order.md) is what fixes it — including what it costs at deployment time. See *Audience binding, and the gap underneath it*. No decision here is changed.

## Question

An external identity provider with the MCP server as a strict resource server, or a self-authored authorization server? And if external — which one, and what exactly does the resource server then owe?

The map ruled out the monolith on the spot: an MCP server that is also its own authorization server is the shape the specification moved away from, and it makes confused-deputy and token-passthrough worse. That leaves an external server against a self-authored one, with #3's research as the decider.

## Decision

**An external authorization server — Keycloak — with the MCP server as a strict resource server.** This ADR discharges the decision #3 deferred here as well as #7's own.

### Why not author one

#3 established that a self-authored server is **not forced**: Client ID Metadata Documents are a `SHOULD` for both sides, dynamic client registration is a `MAY` and deprecated, and an authorization server supporting only pre-registration is conformant. There is no required client-identity mechanism to be locked out of.

Meanwhile the **hard `MUST`s land on the resource server** — RFC 9728 protected resource metadata, and audience validation. That is the half nobody skips and most exhibits do shallowly, and it is the half that survives the authorization server being swapped. Authoring one would drag in a user store, login and consent screens, refresh and key rotation, and client registration — plausibly the majority of the build — to demonstrate the half that is a commodity.

The reputational read matters too, in front of this specific audience: *"integrated an identity provider and got the resource-server obligations exactly right"* is the sentence a hiring reader believes. *"Wrote my own OAuth server"* is one they interrogate.

### Keycloak, and what it costs

Keycloak ≥ 26.7.0 with `--features=cimd`, self-hostable, so the offline-reproducible property constraint #5 protects survives. A hosted provider would have broken it.

The feature is **preview quality and says so at runtime**. Verified on 26.7.1, at both build and boot:

```
WARN [org.keycloak.common.Profile] Experimental features enabled: cimd:v1
```

The exhibit owns that line rather than hiding it.

### The resource server is configured with the issuer, and nothing else

It names that issuer in its own RFC 9728 document and **discovers everything else** from `/.well-known/oauth-authorization-server/{path}`. Two properties follow. Swapping Keycloak for a self-authored server later changes **exactly one string** — which is what makes authorship a clean cut in the map's cut order rather than a half-finished dependency. And the issuer is *already* a required input, because our own protected resource metadata has to name it, so discovery gives one input feeding two outputs, which therefore cannot drift apart.

Verified live against 26.7.1:

| Probe | Result |
| --- | --- |
| `/.well-known/oauth-authorization-server/realms/{realm}` | `200` |
| `/.well-known/openid-configuration/realms/{realm}` | `404` — working as intended, not a defect |

The second is restricted by an allow-list in Keycloak's own `ServerMetadataResource`, on the grounds that OpenID Connect Discovery §4 mandates concatenation rather than path insertion. We therefore discover through `oauth-authorization-server`, which is also what the MCP specification tells clients to try first, and the minimum a phase-two self-authored server would have to implement.

### Client identity: pre-registration and metadata documents; registration policy refuses the rest

Dynamic client registration is dropped. **Verified: that cannot mean the endpoint is absent** — Keycloak advertises it regardless, even with `cimd` enabled:

```
registration_endpoint: http://keycloak:8081/realms/{realm}/clients-registrations/openid-connect
```

*Corrected 2026-08-21 by [#80](https://github.com/marcosfsousa/mcp-erp/issues/80) — the host, and nothing else.* The line above was transcribed with `localhost:8081`. `KC_HOSTNAME` is `http://keycloak:8081` and the issuer is `http://keycloak:8081/realms/mcp-erp`, so `keycloak:8081` is the authority Keycloak advertises every endpoint on, this one included. The decision is untouched; a quoted probe that names an authority the server never returns is a stale claim rather than a record of what was decided.

So "dropped" means *the client-registration policy refuses anonymous registration*. The endpoint exists and says no.

Also verified, and it de-risks the online proof: Claude selects the metadata-document path only when the server advertises **both** `client_id_metadata_document_supported: true` **and** `none` among its token endpoint authentication methods — a real interop requirement that broke Keycloak once and is derivable from no specification text. On 26.7.1 both are present out of the box.

### Audience binding, and the gap underneath it

The audience arrives via an **Audience mapper on a *default* client scope per resource server**, so the audience is a property of the resource rather than of the request. The value is the **resource's own URL in the environment it is running in**, injected through Keycloak's `${VAR}` placeholder — resolved from operating-system environment variables only, textually, before the realm JSON is parsed.

Deliberately *not* the scope-selected variant, which would mix "what I may do" with "who this token is for" in one vocabulary — a cost #11 and constraint #10 would then have to absorb. And deliberately not a stable abstract identifier: blessed by RFC 8707 §2, but `aud` would stop equalling the `resource` a client sends, which breaks the moment we move to a server that honours it — precisely the phase-two direction.

*Cross-reference added 2026-08-19 by [#37](https://github.com/marcosfsousa/mcp-erp/issues/37).* **This section says which URL the audience is without saying what that URL is; [ADR-0006](0006-fail-closed-in-a-fixed-order.md) §Discovery is published both ways, at one address is what fixes it** — the identifier, the path-inserted metadata address derived from it, and, since #37 deployed the server, **what having exactly one identifier costs at deployment time**: one published address, and therefore a gateway in front of the two replicas map constraint `#5` asks for. The audience check named above is why that matters rather than being a hosting detail — it is the load-bearing control, per deviation 1 below, and an audience naming an address no caller reached would pass while proving nothing.

### How the exhibit is proved

Three tiers with three distinct jobs, not a ranking:

1. **Automated offline run — load-bearing, gates continuous integration.** The conformance client runs inside the Compose network on pre-registration, driving the authorization code flow with Proof Key for Code Exchange plus the attack suite, exiting non-zero on failure. No browser, no hosts-file entry, no internet.
2. **Online run over a Client ID Metadata Document** — proves the modern registration path the revision is built around. The document is **hosted by us on GitHub Pages**, so the same client runs the same flow under either registration path, one flag apart, and any reader with an internet connection reproduces it without an account.
3. **MCP Inspector — the witnessed third-party demo**, and the only available evidence for ADR-0001's claim that a real off-the-shelf client can reach a modern-only server.

Two facts separated these more sharply than they first looked. A metadata document **cannot** be part of an offline proof — the client identifier *is* an HTTPS URL the authorization server fetches — so the offline proof runs on pre-registration by construction. And a programmatic client exists regardless, because constraint #4's attack suite is protected from cuts and something has to drive it and assert on the wire.

The circularity objection to tier 1 stands and is answered rather than dismissed: it asserts against cited specification clauses rather than against itself, and **the write-up says so out loud.**

## Deviations

Two, both deliberate, both named here so a reader finds them acknowledged rather than missed. This section is the point of the ADR as much as the decision is.

**1. RFC 8707 resource indicators — Keycloak does not honour the `resource` parameter.** Its own MCP guide states it verbatim; [keycloak#41526](https://github.com/keycloak/keycloak/issues/41526) was closed 2026-06-23 as *superseded, not implemented*, replaced by [#47117](https://github.com/keycloak/keycloak/issues/47117), which is open, `status/triage`, milestone 26.8.0 due 2026-09-30 — after the build window, and explicitly experimental. [keycloak#14355](https://github.com/keycloak/keycloak/issues/14355) has been open since 2022 and the community pull request was closed unmerged.

This is a genuine spec-versus-implementation gap and the exhibit carries it as a dated, citable finding. It is survivable because the two specifications do not meet in our favour by accident: RFC 8707 §2 makes audience restriction only a **SHOULD** on the authorization server, while the MCP resource server is under a hard **MUST** to reject anything not issued for it. **The resource-server audience check is therefore the load-bearing control, not the `resource` parameter** — and our clients send `resource` anyway, because the specification requires it regardless of server support.

**2. Plain HTTP issuers and resource identifiers.** RFC 8414 §2 requires an issuer identifier to be *"a URL that uses the 'https' scheme"*, and §3 adds that the well-known path *"MUST use the 'https' scheme"*. RFC 9728 §1.2 requires a resource identifier to be *"a URL that uses the https scheme"*. Under Compose we use `http://` for both — the issuer `http://keycloak:8081/realms/{realm}` and the resource identifier `http://localhost:8080/mcp`. No carve-out for localhost, loopback or development exists in either document.

The reason is offline reproducibility: no certificate authority issues a certificate for `keycloak:8081`, and a self-signed authority makes certificate trust a setup step for every third-party client, against constraint #5 and ship line #8.

*Amended 2026-08-15 by [#10](https://github.com/marcosfsousa/mcp-erp/issues/10).* The sentence that stood here is **withdrawn**:

> ~~The deviation is a property of the local harness, not of the design — a Cloud Run deployment (#10) is genuinely HTTPS and symmetric, and demonstrates the conformant form with no trick.~~

[ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md) declined the deployment, so no environment this exhibit ships erases this deviation, and a claim resting on an environment we do not build is a claim we cannot make.

**The deviation is not closed here** — which is a smaller claim than *owned permanently*, and the true one. Declining the deployment removed one route; it did not exhaust them. The surviving route is **option 6 below, as a non-default opt-in profile**: the certificate-trust objection recorded against it is against it as the *default* configuration, and does not reach an opt-in that leaves the zero-setup default untouched. It was put to #10 in that form and **declined for v1 on setup cost, not on impossibility** — a different kind of reason from the ones that killed options 3, 6-as-default and 7, and recorded separately so it is not mistaken for one.

## Options considered

1. **Self-author the authorization server** (map option C). Maximally differentiating and spec-honest, and it makes the user store, login, consent and rotation questions ours. Rejected because #3 removed the forcing function: no client-identity mechanism requires it, the hard MUSTs are on the other side, and the build capacity it consumes comes out of exactly the resource-server depth a reader judges. It survives in the cut order as a deferrable phase two, made clean by the single-string swap above.
2. **The monolith** (map option B). Ruled out while charting and not revisited: it is the shape the specification moved away from, and choosing it would demonstrate not having read it.
3. **A hosted identity provider.** Nothing to run, real HTTPS, and both scheme deviations disappear. Rejected because it breaks offline reproducibility — the property constraint #5 exists to protect, and the one that makes `docker compose up` a complete proof.
4. **Ory Hydra, Microsoft Entra ID, Okta.** Hydra's metadata-document support is an open, unimplemented request; Entra supports neither mechanism; Okta has dynamic registration but no metadata documents. Any of the three would have forced authorship after all.
5. **A stable abstract audience identifier** rather than the deployment URL. Explicitly blessed by RFC 8707 §2, and it would decouple the audience from the deployment. Rejected: `aud` would stop equalling the `resource` clients send, breaking the moment an authorization server honours the parameter.
6. **Terminating TLS at a fixed hostname in Compose**, removing deviation 2. Rejected: certificate trust becomes a setup step for every client.
7. **A public wildcard-DNS hostname** such as `sslip.io` for the issuer. Zero setup and robust, and it fails in exactly the demo conditions you cannot control — resolution would depend on the internet, undoing the offline property.
8. **Claude Code with Anthropic's published metadata document** as tier 2. A genuinely well-known third-party client with nothing for us to host — but it needs an Anthropic account and the undocumented `MCP_PROTOCOL_NEGOTIATION=auto`, making it a recording rather than a reproducible run.

## Consequences

**Corrections banked.**

- *"Keep `registration_endpoint` — a metadata-document-only posture locks out most of the ecosystem, Inspector included"* is **wrong on the Inspector point**. Inspector supports pre-registration and metadata documents directly. The true statement is narrower: **Inspector does not publish its own metadata document** ([inspector#1150](https://github.com/modelcontextprotocol/inspector/issues/1150), open since 2026-03-16, triaged Medium and not approved for work) — which is why it could not have been tier 2 in any case.
- *"Confirm RFC 8707 support before committing to Keycloak"* is no longer an open risk. It is **resolved negative** and absorbed as deviation 1.

**Cost.** A preview-quality feature flag in the critical path. A permanent commitment to a GitHub Pages URL, since a metadata document's identifier *is* its URL. Two named deviations the write-up must own rather than mention. And a compose-only artifact: the issuer must be identical inside and outside the container network, so the browser-driven demo needs one documented `127.0.0.1 keycloak` line in the host's hosts file — acceptable only because the primary proof runs *inside* the network, so `docker compose up` still produces a complete passing run with zero setup.

**Input to other tickets.**

- **#8 (what performs the run)** inherits the three tiers and the fact that a programmatic client exists regardless.
- **#9 (attack suite)** inherits deviation 1 as the reason clause #1 is testable at all, and the citation for it.
- ~~**#10 (Cloud Run)** inherits a stronger reason to exist: it is where deviation 2 disappears.~~ **Void, 2026-08-15 ([#10](https://github.com/marcosfsousa/mcp-erp/issues/10)):** the deployment was declined, so deviation 2 stays open and is carried rather than erased. The route that would close it is option 6 as an opt-in profile, recorded in *Deviations 2* above and in [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md).
- **#11 (scope granularity)** must keep `scopes_supported` in the protected resource metadata honest.

**Not contradicted:** ADR-0001. Tier 3 depends on its finding that Inspector can reach a modern-only server, and nothing here binds context at connection time.

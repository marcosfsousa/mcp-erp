# ADR-0007: The realm is the exhibit

- **Status:** Accepted
- **Date:** 2026-08-11
- **Ticket:** [#7 Choose the authorization server](https://github.com/marcosfsousa/mcp-erp/issues/7)
- **Evidence:** [ADR-0002](0002-refusal-shape-follows-the-remedy.md) (three denial classes), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md) (the cast, the `sub` join), [ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md), [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md); RFC 9700 §4.14.2; map constraints #3, #4, #5, #8, #10; live verification against Keycloak 26.7.1, 2026-08-11
- **Amended:** 2026-08-11 — additive, by [#8](https://github.com/marcosfsousa/mcp-erp/issues/8). This ADR put Keycloak behind a Dockerfile without saying how its version is held still, and `--features=cimd` is a preview flag. See *The base image is pinned by digest*. No decision here is changed.
- **Amended:** 2026-08-15 — cosmetic, by [#10](https://github.com/marcosfsousa/mcp-erp/issues/10). One clause anticipating a Cloud Run decision is withdrawn; the reasons around it are untouched. See *How it runs, and where the file lives*. *(Header added 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12); the in-body marker has stood since 2026-08-15.)*
- **Amended:** 2026-08-16 — substantive, by [#11](https://github.com/marcosfsousa/mcp-erp/issues/11). Only `erp.decide` carries a role scope mapping, and it lists two roles. See *Scopes are gated by roles that mirror the ERP's*. *(Header added 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12).)*
- **Amended:** 2026-08-18 — substantive, by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12). The seed renders **three** ways and carries **two independent role columns**; realm and directory membership is held equal by a test, with Priya's divergence declared as a role-column exception. See *Hand-authored, with only the users generated* and *Scopes are gated by roles that mirror the ERP's*. No decision here is reversed.

## Question

ADR-0005 chose an authorization server we do not write. So what is left to design is its **configuration** — and the configuration is not plumbing here. A reader opens the realm file to see the audience mapper, the decoy client and the deliberate role drift. It is evidence, and it has to read like it.

How is it produced, what is in it, and how does it run?

## Decision

### Hand-authored, with only the users generated

The clients, redirect URIs, client scopes and audience mappers are **hand-written JSON**. That section *is* the exhibit; a generated blob is worse evidence than authored intent. A generator fills the `users` array from #6's seed file, which is exactly the `sub` join ADR-0003 already owes — one seed file rendered twice, into ERP rows and into the realm import. One committed realm file, drift-checked the way #6 drift-checks its per-row fixtures.

*Amended 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12).* **Rendered twice becomes rendered three times**, and the generator moves.

[ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md) adds a layer-2 principal directory as a third rendering, and gives layer 2 the generator that produces both it and this realm import. The seed carries **two independent role columns** — server-side roles and issuer-side realm roles — and the generator treats the **issuer-side names as opaque strings it never interprets**, so only the identity half (subject, username, credentials) is shared between renderings. Rendering this import from directory roles would erase the divergence *Scopes are gated by roles that mirror the ERP's* calls load-bearing.

**Realm and directory membership is held equal by a test**, not by the assumption that the seed is the only writer: realm subject set equals directory subject set, with Priya Raman declared as an exception on the **role columns only, never on membership**. The renderer must be byte-stable — sorted keys, no generated identifiers, no timestamps, all three of which a Keycloak export emits by default — or the drift job flakes and a required check gets disabled.

### Keycloak is a pure function of that file

`KC_DB=dev-mem`, plain `start --import-realm`. An empty in-memory database, no volume, unconditional re-import on every boot.

This is chosen for what it makes **unreachable**. Keycloak's startup import *skips* when the realm already exists — *"the import operation is skipped… to avoid re-creating realms and potentially lose state"* — with no strategy knob on the flag, and the legacy `OVERWRITE_EXISTING` property cannot rescue it in 26.x because `ExportImportManager` sets `IGNORE_EXISTING` itself before the providers are constructed. With an empty database the realm never "already exists", so the trap is **structurally unreachable rather than documented around**, and the claim that Keycloak is a pure function of the committed file is provable rather than asserted.

**Verified live on 26.7.1**, because the documentation is alarming and the code is not. The database guide says `dev-file` *"is not suitable for production use-cases"* and the 26.1 upgrading guide says it *"has never been supported in the production mode"* — but that is a support statement plus a deprecation of *relying on the default*, whose prescribed remedy is supplying a value explicitly. No code path rejects it: `Start.java`'s only pre-run check rejects the dev **profile**, and `isDevModeDatabase` has exactly one use in the repository, setting the connection pool minimum to 1. Booting the real image:

```
Keycloak 26.7.1 ... started in 8.342s. Listening on: http://0.0.0.0:8081
Profile prod activated.
Installed features: [agroal, cdi, hibernate-orm, jdbc-h2, keycloak, ...]
```

Production profile, H2 installed, **no database warning of any kind**.

The accepted cost is an asset: an empty database means **fresh signing keys on every boot**, so the resource server must handle a key identifier it has never seen. That converts key rotation from asserted to exercised — [ADR-0006](0006-fail-closed-in-a-fixed-order.md) owns the mechanism.

### How it runs, and where the file lives

Keycloak runs in **production mode from a pre-built image**: a Dockerfile runs `kc.sh build --features=cimd --db=dev-mem`, and the container runs `start --optimized --import-realm`. This is forced more than chosen — the metadata-document feature is a **build-time** option, so either a Dockerfile pays that cost once or every boot, including every continuous-integration run, pays it. Once the Dockerfile exists, production mode costs three more words.

### The base image is pinned by digest

*Amended 2026-08-11 by [#8](https://github.com/marcosfsousa/mcp-erp/issues/8).*

The Dockerfile's `FROM` names an **exact tag and its digest** — `quay.io/keycloak/keycloak:26.7.1@sha256:…` — and moves only in a pull request that does nothing else.

`--features=cimd` is a **preview** flag. Preview features carry no compatibility guarantee and move between minor versions, which is the whole of the risk: a floating tag turns that into a suite going red one morning for a reason nothing in the repository changed. Pinned, a regression can only arrive inside the pull request that bumped the version, which is where it should be met and where a blocking check is doing its job rather than being a liability.

This is the reason [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) could accept a merge-gating job that depends on this container at all. The general rule outgrew both documents and became a standing map constraint, covering Postgres, the Python runtime and every future image on the same terms.

The realm file is **baked into the image and bind-mounted over it in Compose**, from the same committed path. The mount wins locally, so editing the file and restarting shows the change immediately — which is what makes the pure-function claim something a reader can *try*. The baked copy keeps the image runnable on its own, wherever it is run. The two cannot drift: they are the same file in the repository.

*Amended 2026-08-15 by [#10](https://github.com/marcosfsousa/mcp-erp/issues/10) — cosmetic.* This passage read *"so #10 stays free to say yes to Cloud Run without reopening this."* That ticket said no ([ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md)), and the clause was a bonus rather than the justification: the baked copy exists so the image is self-contained and the mount exists so editing the realm and restarting shows the change. Both reasons are untouched.

### Four clients, one stated job each

| Client | Audience | Exists for |
| --- | --- | --- |
| `mcp-conformance` | ours | every normal run |
| `mcp-conformance-decoy` | `http://localhost:9090/hr` | `audience_confusion` — a token legitimately issued for another resource, replayed at us |
| `mcp-conformance-bare` | none | the fail-closed check on audience-less tokens |
| `mcp-expiry-probe` | ours, ten-second lifespan | `token_expired` |

Plus a **second realm**, `mcp-erp-neighbour`, with one client. It is a genuinely different issuer with its own signing keys and its own real flow, which is what lets the suite reject a token that is **perfect in every respect except who issued it** — clauses #2 (`token_passthrough`) and #3 (`foreign_issuer_token`). Minting those in the test instead would have exercised the same branch while asserting against a token we invented.

### Every client is public, and the weak challenge method is refused

All clients are **public**, authenticating with Proof Key for Code Exchange, with the challenge method **pinned to SHA-256 at the server**. No secret exists anywhere in the repository.

This matches the shape of every real client the exhibit targets — Inspector and Claude Code both run on a user's machine and neither can hold a secret — so tier 1 drives the same flow as tier 3. A confidential conformance client would have made the load-bearing offline proof exercise a flow no real client uses.

**Note for #9:** the realm advertises `code_challenge_methods_supported: ['plain', 'S256']`, verified on 26.7.1. The pin is **per client** and the discovery document does not reflect per-client policy. So `pkce_downgrade_plain` must assert that the server *refuses a plain challenge for our client* — not that the metadata omits `plain`, which it will not.

**Direct Access Grants are disabled on every client**, and the refusal is asserted. That flow — username and password straight to the token endpoint — would make the conformance client trivial, and it is the flow OAuth 2.1 removed. Turning it off and *testing that it is off* converts a thing we did not use into a thing the realm refuses.

### Consent is required on every client

*Added 2026-08-16 by [#11](https://github.com/marcosfsousa/mcp-erp/issues/11); see [ADR-0012](0012-the-token-names-a-capability-never-a-role.md).* This ADR left consent undecided, and it belongs to the realm.

All four clients set **Consent required**. Each capability scope carries consent screen text; the audience-bearing default client scope sets *Display on consent screen* off, because it is infrastructure rather than a permission. The screen therefore shows exactly three lines, one per capability, and no plumbing.

The screen is the only place a human meets the delegation ceiling as a choice rather than as a claim in a write-up. The cost is one more form post in a headless client that already posts the login form, since direct access grants are off above. Fresh state on every boot means continuous integration always takes the first-consent path, which makes it deterministic rather than sometimes-remembered.

**A limitation, stated rather than discovered.** Keycloak's consent screen is grant-or-deny for the whole request; it does not offer per-scope deselection. The screen *displays* the ceiling and does not let the person narrow it — narrowing happens in the client's `scope` parameter. Flagged for assertion at build time rather than trust.

### Token lifetimes, and rotation as a requirement rather than a nicety

Five minutes realm-wide with refresh tokens issued; `mcp-expiry-probe` overrides its own lifespan to ten seconds. Five minutes keeps ADR-0002's published `ttlMs = min(5 min, remaining token lifetime)` meaningful — sixty seconds would degenerate it to always picking the token, an hour would make the cap decoration — and the override makes expiry a ten-second wait rather than a fake clock.

**Refresh tokens rotate, with zero reuse.** Verified verbatim, RFC 9700 §4.14.2:

> Authorization servers **MUST** utilize one of these methods to detect refresh token replay by malicious actors **for public clients**: *sender-constrained refresh tokens* … *refresh token rotation*.

Every client here is public, so this binds. Sender-constraining needs mutual TLS or proof-of-possession, neither in scope, which leaves rotation. A replayed refresh token revokes the grant, and the attack suite asserts it.

*(A precision note for anyone citing this later: the OAuth 2.1 draft itself does **not** carry this rule. RFC 9700 is the citation.)*

### Scopes are gated by roles that mirror the ERP's — and one person deliberately does not match

Every scope is an optional client scope. The gate is a **role scope mapping**, which is Keycloak's one native, no-code, per-user gate: *"when a client scope has role scope mappings defined, the user must be a member of at least one of the roles… If a user is not permitted to use the client scope, no protocol mappers or role scope mappings will be used when generating tokens."*

*Amended 2026-08-16 by [#11](https://github.com/marcosfsousa/mcp-erp/issues/11).* This passage read *"Each scope is an optional client scope carrying a role scope mapping."* It was written while scope strings were assumed to mirror role names, which [ADR-0012](0012-the-token-names-a-capability-never-a-role.md) ended. Under three coarse capabilities, **only `erp.decide` carries a mapping, and that mapping lists both `approver` and `unlimited_approver`.**

- `erp.write` cannot be gated: ADR-0003 gates submitting by **scope alone, no role**, so a mapping there would lock every submitter out of a scope they are entitled to. Ungated is also what makes the intersection visible on `record_invoice` — the scope is handed out freely and `invoice_clerk` decides whether it achieves anything.
- `erp.read` has no role behind it either; `auditor` widens which rows are returned, it does not grant reading.
- The mapping lists **two** roles because Ingrid Holm holds `unlimited_approver`, not `approver`. Gating on `approver` alone would leave her token without `erp.decide`, unlist `approve_requisition` for her, and make the above-threshold branch she exists for unreachable. Listing both uses the *"at least one of these roles"* semantics quoted above exactly as designed, and invents no realm state.

The two-role mapping **strengthens** the separation this section is about: `erp.decide` now maps from two roles that differ on the threshold, which no scope can express, so the scope twins no role name at all.

**Priya Raman holds `approver` in Keycloak and no role in the ERP.**

That single row is load-bearing. ADR-0002's middle denial class needs the *scope-without-role* state reachable through a real flow: a token carrying `approve` while the ERP says the caller is not an approver, producing the `-31010` refusal that a `403` would lie about. Gating every scope by a role that mirrors the ERP exactly would make that state unreachable except by hand-minting tokens — **decision-by-decision, role gating would have silently deleted the one branch ADR-0003 says Priya exists for.** The drift is not an accident to be tidied later; it is the reason the intersection exists, and the most ordinary thing in enterprise identity: the directory was updated, the downstream system never was.

The opposite drift is not modelled, and that is deliberate: an ERP role with no Keycloak role produces `insufficient_scope`, which the matrix already reaches by varying the requested scope set, since its principal is *person × scope set*.

### The access token names nothing in the domain

It carries `sub`, `aud` and `scope`. The realm roles are an **issuance-time gate only** and never appear on the wire.

Constraint #10 decides this: `unlimited_approver` is unambiguously layer-3 vocabulary, and putting it in the token would make the *token contract itself* domain-shaped — clone the repository for another purpose and the wire format still talks about purchasing. Suppression also converts constraint #3's separation from a discipline into a structural impossibility: you cannot accidentally read a role from a token that has none.

Note this is **not a removal**. A hand-authored `clientScopes` array suppresses every built-in default scope, including `roles`. Suppression is the default outcome; inclusion would have been the deliberate act.

### Users log in with one conspicuously fake password

All seven share a single non-temporary password committed in the seed file, with no required actions. Per-person passwords would be seven equally committed, equally fake secrets buying no behaviour.

## Options considered

1. **Generate the whole realm.** Maximum consistency with the seed file, and the audience mapper stops being readable as a decision.
2. **Hand-author the users too**, with pasted identifiers. Fewest moving parts; contradicts ADR-0003's one-seed-file-rendered-twice and puts the `sub` join at the mercy of copy-paste.
3. **Entrypoint `kc.sh import --override` then `exec kc.sh start`** over a persisted database. Realm edits always land and runtime state survives — at the cost of a custom entrypoint, two JVM launches per boot, and a volume to explain. This is the fallback if the in-memory database ever stops being viable.
4. **Plain `start --import-realm` over a volume.** Simplest Compose file, worst failure mode: edit the realm, restart, nothing changes, no error.
5. **Baking the realm into the image only.** One artifact, identical everywhere, and every edit costs a rebuild on the single file the design most expects to be read and tinkered with.
6. **No role gating at all.** Cheapest, and every denial class arises naturally — but every token becomes maximally privileged and "delegation ceiling" stops being true of the person.
7. **Realm roles named for delegation capability** (`may-request-approve`), keeping the two vocabularies distinct. Rejected in favour of the more realistic two-stores-of-the-same-truth story, which is what makes the drift legible.
8. **Including `realm_access.roles` and visibly ignoring it.** The two stores disagreeing becomes legible on the wire and would make a strong matrix row — and it tears under ADR-0004's deletion test. Putting it in the ID token only is textbook separation, and inert: neither Inspector nor Claude Code reads the ID token.
9. **The expiry probe doubling as the audience-less client.** One client fewer, and a failure that cannot be attributed to expiry or to the missing audience.
10. **Enabling Direct Access Grants for the conformance client.** Far less client code, and the primary proof would stop exercising the authorization code flow at all.

## Consequences

**Three traps banked, each of which would have failed at runtime rather than at import.**

1. **A hand-authored `clientScopes` array suppresses Keycloak's built-in defaults — including `basic`, which is where `sub` comes from.** Since Keycloak 25 the access token's `sub` is written by the `oidc-sub-mapper` on the built-in `basic` client scope, and `RealmManager.isCreateDefaultClientScopes()` returns `rep.getClientScopes() == null || …` — so a realm JSON containing that array never gets the defaults created ([keycloak#31082](https://github.com/keycloak/keycloak/issues/31082)). We hit this **by construction**, because the audience mapper lives on a hand-authored scope. The ID token is unaffected, so it would have failed exactly where we read it: the `sub` join to ERP rows. **The realm must carry `basic`, or an equivalent subject mapper, explicitly.**
2. **Imported passwords are temporary by default**, which triggers an update-password action on first login and hangs a headless flow on a form it does not expect. The credential must be non-temporary with `requiredActions` empty.
3. **`${VAR}` placeholders resolve from operating-system environment variables only** — not from `-D` properties — and an **unresolved placeholder is left literally in place rather than erroring**, silently installing the string `${MCP_RESOURCE_URL}` as an audience value. Every placeholder we use carries a default: `${VAR:default}`. (Values containing a colon parse as `key:default`.)

**A correction banked.** *"Partial import through the admin API regenerates user ids"* is out of date and the conclusion drawn from it is void — true only through Keycloak 22.x, fixed by [keycloak#22568](https://github.com/keycloak/keycloak/pull/22568) (merged 2023-11-02, shipped 23.0.0). `kcadm.sh` and `keycloak-config-cli` are therefore **not** disqualified on `sub`-join grounds. They remain a heavier path; the argument that pruned them was wrong and must not be reused.

**Cost.** Fresh signing keys and a fresh admin user on every boot, so nothing survives a restart by design. Two realm files. Four clients plus a neighbour to explain. A committed password that needs one line of write-up so nobody reads it as a leaked secret. And a `code_challenge_methods_supported` list that advertises a method our clients refuse — accurate, since it is realm-level, and confusing without the note above.

**Input to other tickets.**

- **#6 (data model)** — the seed file owes a **third column** for Keycloak realm roles, and a password field. Priya's row is the one that must diverge.
- **#9 (attack suite)** inherits `pkce_downgrade_plain` (with the per-client caveat), `token_expired`, `audience_missing`, `password_grant_refused` and `refresh_token_replay`.
- **#11 (scope granularity)** inherited the optional-client-scope-plus-role-scope-mapping shape as the mechanism its naming has to fit. *Closed 2026-08-16 by [ADR-0012](0012-the-token-names-a-capability-never-a-role.md)*, which fitted it and amended two passages above — the role scope mapping, and consent.
- **#15 (walkthrough)** gets the drift as its most explainable moment, and should use it.

**A known limitation of the gate.** A role scope mapping can express only "holds at least one of these roles" — no conjunction, no negation, no attribute conditions. It is also **overloaded**: a mapping added to narrow which *roles* appear in a token silently restricts which *users* get that scope at all. And error semantics diverge — a scope not linked to the client at all is a hard `invalid_scope` at the authorization endpoint, while a scope linked but not permitted is **silently omitted** and the flow succeeds. The matrix's *person × scope set* principal will feel that difference.

The silent omission is **conformant, not a quirk**: RFC 6749 §3.3 says the authorization server *"MAY fully or partially ignore the scope requested by the client, based on the authorization server policy or the resource owner's instructions."* The same section then binds Keycloak to a `MUST` — returning the `scope` response parameter whenever the granted scope differs from the requested one — which [ADR-0012](0012-the-token-names-a-capability-never-a-role.md) leaves as an open verification item rather than an assumed gap.

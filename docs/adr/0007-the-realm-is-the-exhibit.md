# ADR-0007: The realm is the exhibit

- **Status:** Accepted
- **Date:** 2026-08-11
- **Ticket:** [#7 Choose the authorization server](https://github.com/marcosfsousa/mcp-erp/issues/7)
- **Evidence:** [ADR-0002](0002-refusal-shape-follows-the-remedy.md) (three denial classes), [ADR-0003](0003-the-schema-is-the-policy-functions-argument-list.md) (the cast, the `sub` join), [ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md), [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md); RFC 9700 §4.14.2; map constraints #3, #4, #5, #8, #10; live verification against Keycloak 26.7.1, 2026-08-11
- **Amended:** 2026-08-11 — additive, by [#8](https://github.com/marcosfsousa/mcp-erp/issues/8). This ADR put Keycloak behind a Dockerfile without saying how its version is held still, and `--features=cimd` is a preview flag. See *The base image is pinned by digest*. No decision here is changed.
- **Amended:** 2026-08-15 — cosmetic, by [#10](https://github.com/marcosfsousa/mcp-erp/issues/10). One clause anticipating a Cloud Run decision is withdrawn; the reasons around it are untouched. See *How it runs, and where the file lives*. *(Header added 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12); the in-body marker has stood since 2026-08-15.)*
- **Amended:** 2026-08-16 — substantive, by [#11](https://github.com/marcosfsousa/mcp-erp/issues/11). Only `erp.decide` carries a role scope mapping, and it lists two roles. See *Scopes are gated by roles that mirror the ERP's*. *(Header added 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12).)*
- **Amended:** 2026-08-18 — substantive, by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12). The seed renders **three** ways and carries **two independent role columns**; realm and directory membership is held equal by a test, with Priya's divergence declared as a role-column exception. See *Hand-authored, with only the users generated* and *Scopes are gated by roles that mirror the ERP's*. No decision here is reversed.
- **Amended:** 2026-08-18 — substantive, by [#35](https://github.com/marcosfsousa/mcp-erp/issues/35). The generated users land in a **second file beside** the hand-authored realm rather than in an array inside it. See *Hand-authored, with only the users generated*. No decision here is reversed; the split is what makes this section's own rule structural.
- **Amended:** 2026-08-18 — additive, by [#36](https://github.com/marcosfsousa/mcp-erp/issues/36), which built it. The two-file directory import is **verified against a running container**, and execution banked **three further traps** plus one consequence of register deviation 2 that this document did not anticipate. See *Hand-authored, with only the users generated* and *Consequences*. No decision here is reversed.
- **Amended:** 2026-08-20 — substantive, by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46), which built the conformance client. Four clients is what the file *contains*; a **fifth exists at run time**, provisioned from a hosted document, and the realm had to gain a client policy and realm-level default client scopes before it would. See *Four clients, one stated job each*. No decision here is reversed, and none of the four changes.
- **Amended:** 2026-08-20 — substantive, by [#44](https://github.com/marcosfsousa/mcp-erp/issues/44), which built the attack suite and found `scope_exact_match` unfalsifiable over the wire. A **fifth declared client**, `mcp-scope-lookalike`, and the `ERP.READ` client scope it exists to mint — so the run-time client the line above records is a sixth. The table's own rule is what admits it: one client, one refusal it makes reachable. See *Five clients, one stated job each*. No decision here is reversed, and none of the four above changes.
- **Amended:** 2026-08-24 — substantive, by [#93](https://github.com/marcosfsousa/mcp-erp/issues/93), which ran the client the recording is of. **One Person holds `offline_access`** — Priya Raman, and only her — because Claude Code requests that scope unconditionally and Keycloak refuses the token outright without it. See *Token lifetimes, and rotation as a requirement rather than a nicety*. Rotation, zero reuse and the five-minute access token are unchanged; this is a concession stated where the story it cuts against is told, and it takes no normative-register row.
- **Amended:** 2026-08-24 — substantive, by [#93](https://github.com/marcosfsousa/mcp-erp/issues/93). **The trust decision names two domains, not one.** `claude.ai` joins `marcosfsousa.github.io` in the policy's condition *and* in the executor's permitted domains; naming it in one alone answers *client not found* for a client that was never looked for. See *Five clients, one stated job each*. This corrects a sentence that read *"and nothing else"* and reverses no decision — the condition is still an allow-list of `https` origins and still the whole of the trust decision.

## Question

ADR-0005 chose an authorization server we do not write. So what is left to design is its **configuration** — and the configuration is not plumbing here. A reader opens the realm file to see the audience mapper, the decoy client and the deliberate role drift. It is evidence, and it has to read like it.

How is it produced, what is in it, and how does it run?

## Decision

### Hand-authored, with only the users generated

The clients, redirect URIs, client scopes and audience mappers are **hand-written JSON**. That section *is* the exhibit; a generated blob is worse evidence than authored intent. A generator fills the `users` array from #6's seed file, which is exactly the `sub` join ADR-0003 already owes — one seed file rendered twice, into ERP rows and into the realm import. One committed realm file, drift-checked the way #6 drift-checks its per-row fixtures.

*Amended 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12).* **Rendered twice becomes rendered three times**, and the generator moves.

[ADR-0013](0013-layer-3-declares-what-layer-2-decides-and-layer-1-never-learns-why.md) adds a layer-2 principal directory as a third rendering, and gives layer 2 the generator that produces both it and this realm import. The seed carries **two independent role columns** — server-side roles and issuer-side realm roles — and the generator treats the **issuer-side names as opaque strings it never interprets**, so only the identity half (subject, username, credentials) is shared between renderings. Rendering this import from directory roles would erase the divergence *Scopes are gated by roles that mirror the ERP's* calls load-bearing.

**Realm and directory membership is held equal by a test**, not by the assumption that the seed is the only writer: realm subject set equals directory subject set, with Priya Raman declared as an exception on the **role columns only, never on membership**. The renderer must be byte-stable — sorted keys, no generated identifiers, no timestamps, all three of which a Keycloak export emits by default — or the drift job flakes and a required check gets disabled.

*Amended 2026-08-18 by [#35](https://github.com/marcosfsousa/mcp-erp/issues/35), which built it.* **One committed realm file becomes two committed files**, and this section's own rule is what forces it.

*Hand-written clients, generated users* is a rule about one file that nothing enforces: an array spliced into the authored realm leaves the generated half sitting in the file a reader is invited to edit, one hand-edit away from being overwritten without warning. Two files make the split structural instead. `keycloak/import/mcp-erp-users-0.json` is rendered and never edited; the realm file beside it is authored and holds no `users` key to edit. Neither can quietly become the other, and the drift check has a whole file to compare rather than one key inside a file it must otherwise leave alone.

It is also **Keycloak's own shape**: exporting a realm with its users in separate files produces `<realm>-realm.json` alongside `<realm>-users-N.json`, and importing a directory reads both. So this buys the split at the cost of nothing invented — the naming and the index are the export format's, not ours.

~~**Unverified against a running container, and deliberately so.**~~ [#36](https://github.com/marcosfsousa/mcp-erp/issues/36) is the ticket that stands Keycloak up and is where a directory import is first executed; it inherits the check, and the fallback if the two-file read disappoints is one line of rendering — splice the same `users` array into the realm file — which is why this was not worth blocking a Docker-free ticket on.

*Amended 2026-08-18 by [#36](https://github.com/marcosfsousa/mcp-erp/issues/36), which executed it.* **Verified**, on 26.7.1:

```
Importing from directory /opt/keycloak/bin/../data/import
Realm 'mcp-erp-neighbour' imported
Imported users from /opt/keycloak/bin/../data/import/mcp-erp-users-0.json
Realm 'mcp-erp' imported
```

A directory import reads `<realm>-realm.json` and the `<realm>-users-N.json` beside it exactly as the export format promises, and it pairs them by name rather than by order — the neighbour realm's own file sits in the same directory and takes no users. **The fallback is not needed and is not taken.**

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

### ~~Four~~ Five clients, one stated job each

| Client | Audience | Exists for |
| --- | --- | --- |
| `mcp-conformance` | ours | every normal run |
| `mcp-conformance-decoy` | `http://localhost:9090/hr` | `audience_confusion` — a token legitimately issued for another resource, replayed at us |
| `mcp-conformance-bare` | none | the fail-closed check on audience-less tokens |
| `mcp-expiry-probe` | ours, ten-second lifespan | `token_expired` |
| `mcp-scope-lookalike` | ours | `scope_exact_match` — a token that reaches the scope gate carrying strings which resemble a capability scope and are not one |

***Amended 2026-08-20 by [#44](https://github.com/marcosfsousa/mcp-erp/issues/44), which built the suite and found one row unfalsifiable.*** The rule this table states is what admits the fifth client rather than what resists it: **one client, one refusal it makes reachable.** `scope_exact_match` asserts that `ERP.READ` does not satisfy `erp.read` and that `hr.read` does not either, and `scenarios.yaml` claimed it needed no new realm state because the decoy already holds another resource's scope. Run against the stack, it does not: the decoy's token carries somebody else's audience **by construction** — that is precisely what makes it `audience_confusion`'s instrument — so it is refused at gate 4 and never reaches the comparison. Nor can `mcp-conformance` ask for a lookalike: Keycloak validates requested scopes against the client's own assignments and answers `invalid_scope`.

So the realm gains one client and one client scope, `ERP.READ`, which is `erp.read`'s letters in the other case and is a permission over nothing. Its consent text says so. [ADR-0012](0012-the-token-names-a-capability-never-a-role.md) §*Unrecognised scopes are inert* is the rule being asserted, and it named `ERP.READ` and `hr.read` as its two examples before either was mintable.

*A fifth client was considered and refused once before*, in ADR-0012's option 10 — as a way to make the consent ceiling legible — and refused because *"the walkthrough exercises a client the attack suite never does, in a realm whose ADR gives each of four clients one stated job."* This one is the other case: the attack suite is the only thing that uses it, and it has a stated job.

*Amended 2026-08-20 by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46), which built the conformance client and found this by running it.* **A client exists at run time that this file does not contain, and the realm has to invite it.** *(This read "a fifth client" and was written against a four-row table; #44 landed the fifth **declared** client in the same session, so the run-time one is a sixth and the ordinal is dropped rather than incremented — the claim was never about which number it is.)*

The clients above are what this file *contains*. The client the conformance run drives is not one of them and is registered nowhere: it identifies itself by a document GitHub Pages serves, and Keycloak provisions a client from that document on the authorization request. Two realm-level statements were needed before it would, and neither is plumbing — both are decisions this section is the right place for.

**The feature is a client policy, not a switch.** `--features=cimd` in the Dockerfile makes the discovery document advertise `client_id_metadata_document_supported`, and the realm still answers *Client not found* until a policy says which identifiers it will dereference. So the realm carries a profile whose executor is `client-id-metadata-document` and a policy whose condition, `client-id-uri`, admits `https` identifiers from ~~`marcosfsousa.github.io` and nothing else~~ **two named domains and nothing else**. That condition is the whole of the trust decision, and it reads as one.

*Amended 2026-08-24 by [#93](https://github.com/marcosfsousa/mcp-erp/issues/93), which found this by running the client the recording is of.* **The second domain is `claude.ai`**, and it is named in both lists — the policy's condition, which decides whether a stranger's document is looked at, and the executor's `cimd-allow-permitted-domains`, which decides whether the identifier and its redirect URIs are admitted. Naming it in one and not the other fails silently in the more confusing direction: the condition does not match, so the profile never runs, so the identifier is never dereferenced, and Keycloak logs `not trusted domain` and then `client_not_found` — a *no such client* answer to a client that was never looked for.

The domain is Anthropic's, and the document at `https://claude.ai/oauth/claude-code-client-metadata` is Anthropic's own. That is the point of admitting it rather than a cost of doing so: [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) calls the recorded session *"the only evidence a reader cannot call circular"* precisely because nothing in the chain is ours except the thing under test, and a client identified by a document **we** host would put us back at both ends of it.

**What the trust decision now says, and it still reads as one:** two origins, both `https`, both publishing a document at a fixed URL — the exhibit's own, and the vendor whose shipped product is recorded driving it. What did not change is the shape: the list is an allow-list of origins rather than a switch, `cimd-restrict-same-domain` stays off for the same reason it always was, and every other client in the realm is still one this file contains.

Two settings inside it are findings rather than configuration. `cimd-allow-http-scheme` stays **off** — the production setting — and the document's loopback callbacks still work, because that flag governs the identifier and the URL-valued metadata properties and `redirect_uris` is not among them; [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md)'s *only the document must be HTTPS, never the redirect URI* therefore survives contact with an implementation. `cimd-allow-permitted-domains` has to list `localhost` and `127.0.0.1` beside the publishing origins, because the executor checks the redirect URI against the same list.

**A provisioned client inherits realm defaults, and this realm had never needed any.** Every client above names its own scopes, so the realm-level lists were empty — and a client the executor creates gets exactly those. It arrived with no `sub` claim, no audience and none of the three capability scopes. The realm now declares `defaultDefaultClientScopes` of `basic` and `mcp-erp-audience` and `defaultOptionalClientScopes` of the three capability scopes: the same pair `mcp-conformance` names for itself, which is the point. The client that earns its identity and the client that was handed one differ by **how they are known** and by nothing else, so the flow is the same flow.

Nothing above changes for it. Each declared client states its own lists, and the decoy still carries somebody else's audience.

Plus a **second realm**, `mcp-erp-neighbour`, with one client. It is a genuinely different issuer with its own signing keys and its own real flow, which is what lets the suite reject a token that is **perfect in every respect except who issued it** — clauses #2 (`token_passthrough`) and #3 (`foreign_issuer_token`). Minting those in the test instead would have exercised the same branch while asserting against a token we invented.

### Every client is public, and the weak challenge method is refused

All clients are **public**, authenticating with Proof Key for Code Exchange, with the challenge method **pinned to SHA-256 at the server**. No secret exists anywhere in the repository.

*Amended 2026-08-20 by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46).* **The pin is a realm policy, because a per-client attribute cannot reach a client this file does not contain.** *All clients* acquired a fifth member above, and the sentence stopped being true of it: the four here pin the method as a client attribute, and a client the executor provisions carries no attributes, so it accepted `plain` — and accepted no challenge at all. The pin is therefore a client policy conditioned on `client-access-type: public`, which is the one thing every client here has in common and the fifth inherits by being one. Binding it to the metadata-document policy instead does nothing, for a reason `keycloak/README.md` records: that policy's condition votes only on `PRE_AUTHORIZATION_REQUEST` and the PKCE executor acts on ~~`AUTHORIZATION_REQUEST`~~ **`REGISTER`, `UPDATE`, `AUTHORIZATION_REQUEST` and `TOKEN_REQUEST`** *(corrected 2026-09-02 by [#149](https://github.com/marcosfsousa/mcp-erp/issues/149))*, so an executor placed there is inert while looking exactly like enforcement.

This matches the shape of every real client the exhibit targets — Inspector and Claude Code both run on a user's machine and neither can hold a secret — so tier 1 drives the same flow as tier 3. A confidential conformance client would have made the load-bearing offline proof exercise a flow no real client uses.

**Note for #9:** the realm advertises `code_challenge_methods_supported: ['plain', 'S256']`, verified on 26.7.1. The pin is **per client** and the discovery document does not reflect per-client policy. So `pkce_downgrade_plain` must assert that the server *refuses a plain challenge for our client* — not that the metadata omits `plain`, which it will not.

**Direct Access Grants are disabled on every client**, and the refusal is asserted. That flow — username and password straight to the token endpoint — would make the conformance client trivial, and it is the flow OAuth 2.1 removed. Turning it off and *testing that it is off* converts a thing we did not use into a thing the realm refuses.

### Consent is required on every client

*Added 2026-08-16 by [#11](https://github.com/marcosfsousa/mcp-erp/issues/11); see [ADR-0012](0012-the-token-names-a-capability-never-a-role.md).* This ADR left consent undecided, and it belongs to the realm.

~~All four clients~~ **Every client** sets **Consent required**. Each capability scope carries consent screen text; the audience-bearing default client scope sets *Display on consent screen* off, because it is infrastructure rather than a permission. The screen therefore shows exactly three lines, one per capability, and no plumbing.

*The count is struck rather than incremented, 2026-08-20 by [#44](https://github.com/marcosfsousa/mcp-erp/issues/44).* The claim is *every*, `tests/authorization/test_realm.py` asserts it over whatever the file declares, and a number here would be a derived count kept where it can only go stale — the artifact [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md) caught drifting four times in one month. The three-line screen is unchanged: the fifth client's two scopes are optional and are requested by one test, so no ordinary mint's consent screen moves.

The screen is the only place a human meets the delegation ceiling as a choice rather than as a claim in a write-up. The cost is one more form post in a headless client that already posts the login form, since direct access grants are off above. Fresh state on every boot means continuous integration always takes the first-consent path, which makes it deterministic rather than sometimes-remembered.

**A limitation, stated rather than discovered.** Keycloak's consent screen is grant-or-deny for the whole request; it does not offer per-scope deselection. The screen *displays* the ceiling and does not let the person narrow it — narrowing happens in the client's `scope` parameter. Flagged for assertion at build time rather than trust.

### Token lifetimes, and rotation as a requirement rather than a nicety

Five minutes realm-wide with refresh tokens issued; `mcp-expiry-probe` overrides its own lifespan to ten seconds. Five minutes keeps ADR-0002's published `ttlMs = min(5 min, remaining token lifetime)` meaningful — sixty seconds would degenerate it to always picking the token, an hour would make the cap decoration — and the override makes expiry a ten-second wait rather than a fake clock.

**Refresh tokens rotate, with zero reuse.** Verified verbatim, RFC 9700 §4.14.2:

> Authorization servers **MUST** utilize one of these methods to detect refresh token replay by malicious actors **for public clients**: *sender-constrained refresh tokens* … *refresh token rotation*.

Every client here is public, so this binds. Sender-constraining needs mutual TLS or proof-of-possession, neither in scope, which leaves rotation. A replayed refresh token revokes the grant, and the attack suite asserts it.

*(A precision note for anyone citing this later: the OAuth 2.1 draft itself does **not** carry this rule. RFC 9700 is the citation.)*

**One Person holds `offline_access`, and it is the one concession this section makes.** *Added 2026-08-24 by [#93](https://github.com/marcosfsousa/mcp-erp/issues/93).* Claude Code's authorization request carries `offline_access` unconditionally, alongside `prompt=consent` and `resource`, and there is no way to suppress it: `claude mcp add` exposes no OAuth scope option, and `--client-id` would replace the hosted identifier that is the entire argument for recording that client. Keycloak does not narrow an unentitled `offline_access` away the way a role scope mapping narrows `erp.decide` — it refuses the token request outright, `not_allowed: Offline tokens not allowed for the user or client` — so the choice is a realm role or no recording.

Priya Raman holds it, and no one else does. Granting it to one Person rather than to all seven keeps it a visible, argued exception rather than a realm-wide default nobody reads. An offline token is long-lived by design and that cuts against the five minutes above; what survives untouched is the part the attack suite asserts — rotation, `refreshTokenMaxReuse: 0`, a replayed refresh token revoking the grant — and the realm is an in-memory database that dies with the container, so nothing issued here outlives a `docker compose down`.

**No register row.** [`docs/normative-register.md`](../normative-register.md) is scoped to normative statements, and its own rule sends departures from this project's constraints back to where the constraint lives. This departs from the paragraph above it, not from a `MUST` or a `SHOULD`, so this is where it is recorded.

**The client half of the realm is unchanged.** `defaultOptionalClientScopes` still names the three capability scopes and not `offline_access`, because [`keycloak/README.md`](../../keycloak/README.md) §*A provisioned client inherits the realm's defaults* records what #46 read off the created client: a client the CIMD executor provisions carries `offline_access` in its own `optionalClientScopes` whatever the realm defaults name. The realm role was the only thing missing.

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

**Three more traps, banked by execution rather than by reading.** *Added 2026-08-18 by [#36](https://github.com/marcosfsousa/mcp-erp/issues/36).* The three above were found by reading the source and the issue tracker; these three were found by a boot failing and a flow stopping, which is the difference the build ticket exists to make.

4. **A Keycloak user id is unique across the whole database, not per realm.** `USER_ENTITY.ID` is a primary key, so the neighbour realm cannot hold a user whose id is one of the Cast's subjects — the import dies with `Duplicate resource error`, reported by Compose as a container that started and then stopped. The subject a foreign token asserts therefore comes from a **hardcoded claim mapper**, over a user whose generated id nothing reads. It has to match a directory row: skip the `iss` check with a *foreign* subject and the call still fails, at the principal directory, on `role_missing` — so `foreign_issuer_token` would go red on its own removal while proving nothing about the issuer.
5. **`VERIFY_PROFILE` fires even with `requiredActions: []` on the user.** Trap 2 above covers the credential; this is a second required action from a different source — Keycloak's declarative user profile, which marks email, first name and last name required. The Cast carries none of the three, and that is the governing rule holding rather than an omission: no field of a profile changes an authorization decision, and this ADR's evidence already has ADR-0003 rejecting `email` as a directory key. Both realms disable the action. Without it the flow reaches `login-actions/required-action?execution=VERIFY_PROFILE` instead of a code.
6. **A `description` over 255 characters fails the import**, as `Value too long for column "DESCRIPTION CHARACTER VARYING(255)"`. Worth recording because the pressure is structural: realm JSON has no comments, so the reasoning a reader wants keeps trying to move into the nearest `description`. It belongs in `keycloak/README.md`.

**A consequence of register deviation 2 that nothing had priced.** *Added 2026-08-18 by [#36](https://github.com/marcosfsousa/mcp-erp/issues/36).*

Keycloak sets `AUTH_SESSION_ID`, `KC_RESTART` and `KC_AUTH_SESSION_HASH` with **`Secure; SameSite=None`** — measured on 26.7.1 under an `http://keycloak:8081` hostname *and* under an `http://localhost:18081` one, so it does not follow from which name the issuer carries. `SameSite=None` requires `Secure`, Keycloak needs the former for its cross-origin form post, and it emits both whatever the scheme is. It says so at boot: *"the server is running in an insecure context. Secure contexts are required for full functionality, including cross-origin cookies."*

**So a conforming cookie jar cannot complete this flow over plain HTTP.** It declines to send those cookies back, and Keycloak answers the login post with *Restart login cookie not found* — which reads like a rejected password. The token helper clears the flag as it stores them, and states that it is doing so; the concession is confined to the client that mints fixtures and nothing the exhibit ships makes it.

**The half that is not ours to fix is the browser's.** A browser stores `Secure` cookies for `http://localhost` and `http://127.0.0.1` because it treats them as trustworthy origins — and it decides that on the **name**, so a host that merely *resolves* to a loopback address gets no such pass. This ADR's *Cost* accepts *"one documented `127.0.0.1 keycloak` line in the host's hosts file"* for the browser-driven demo. That line fixes resolution and does not reach this: it is a claim about DNS, and the rule is about the name. **The disposition is open and belongs with [#46](https://github.com/marcosfsousa/mcp-erp/issues/46) and [#15](https://github.com/marcosfsousa/mcp-erp/issues/15)**, whose tiers are the ones that meet it — and it is **filed on both as a stated inheritance**, with the measurements and the citations, rather than left in this document for them to find. That is the difference between a finding and a hand-off: an ADR amendment is where a reader checks a decision, not where a ticket learns what it inherited.

The route is not new. [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md) already named ADR-0005's option 6 — terminating TLS at a fixed hostname inside Compose, as a **non-default opt-in profile** — as what closes deviation 2, *"declined for v1 on setup cost, not on impossibility"*. It closes this at the root as well, because `https` is a secure context by scheme and no host list applies. **This is a second and sharper reason for an identified route, not a new proposal**, and the two requirements it reconciles are otherwise unsatisfiable together: the issuer must be a name Docker's own resolver owns, and a name the Secure Contexts list names, and over plain HTTP no string is both.

**A correction banked.** *"Partial import through the admin API regenerates user ids"* is out of date and the conclusion drawn from it is void — true only through Keycloak 22.x, fixed by [keycloak#22568](https://github.com/keycloak/keycloak/pull/22568) (merged 2023-11-02, shipped 23.0.0). `kcadm.sh` and `keycloak-config-cli` are therefore **not** disqualified on `sub`-join grounds. They remain a heavier path; the argument that pruned them was wrong and must not be reused.

**Cost.** Fresh signing keys and a fresh admin user on every boot, so nothing survives a restart by design. Two realm files. Four clients plus a neighbour to explain. A committed password that needs one line of write-up so nobody reads it as a leaked secret. And a `code_challenge_methods_supported` list that advertises a method our clients refuse — accurate, since it is realm-level, and confusing without the note above.

**Input to other tickets.**

- **#6 (data model)** — the seed file owes a **third column** for Keycloak realm roles, and a password field. Priya's row is the one that must diverge.
- **#9 (attack suite)** inherits `pkce_downgrade_plain` (with the per-client caveat), `token_expired`, `audience_missing`, `password_grant_refused` and `refresh_token_replay`.
- **#11 (scope granularity)** inherited the optional-client-scope-plus-role-scope-mapping shape as the mechanism its naming has to fit. *Closed 2026-08-16 by [ADR-0012](0012-the-token-names-a-capability-never-a-role.md)*, which fitted it and amended two passages above — the role scope mapping, and consent.
- **#15 (walkthrough)** gets the drift as its most explainable moment, and should use it.

**A known limitation of the gate.** A role scope mapping can express only "holds at least one of these roles" — no conjunction, no negation, no attribute conditions. It is also **overloaded**: a mapping added to narrow which *roles* appear in a token silently restricts which *users* get that scope at all. And error semantics diverge — a scope not linked to the client at all is a hard `invalid_scope` at the authorization endpoint, while a scope linked but not permitted is **silently omitted** and the flow succeeds. The matrix's *person × scope set* principal will feel that difference.

The silent omission is **conformant, not a quirk**: RFC 6749 §3.3 says the authorization server *"MAY fully or partially ignore the scope requested by the client, based on the authorization server policy or the resource owner's instructions."* The same section then binds Keycloak to a `MUST` — returning the `scope` response parameter whenever the granted scope differs from the requested one — which [ADR-0012](0012-the-token-names-a-capability-never-a-role.md) leaves as an open verification item rather than an assumed gap.

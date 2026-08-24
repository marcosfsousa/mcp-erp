# ADR-0015: The second issuer is the first under another scheme

- **Status:** Accepted
- **Date:** 2026-08-24
- **Ticket:** [#111 A string where a list belongs, and an authority the realm check never looks at](https://github.com/marcosfsousa/mcp-erp/issues/111)
- **Evidence:** [ADR-0005](0005-the-authorization-server-is-a-dependency-not-a-deliverable.md) §Deviations 2 and its option 6, [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md) §*Deviation 2 is not closed here*, [ADR-0014](0014-the-walkthrough-is-the-write-up-and-the-image-is-never-the-proof.md) §(i) The TLS profile; [`tls.env`](../../tls.env), [`compose.yaml`](../../compose.yaml) §*One opt-in profile, and what it moves*; W3C Secure Contexts §3.1

## Question

`docs/organisation/seed.yaml` authors two issuers. What has to be true of the second one?

The parser has always refused *some* second issuers, and the refusal existed for a stated reason — nothing downstream rejects a wrong one. The directory is keyed by issuer and subject, so an identifier no token ever carries resolves nobody and every call under it is refused `role_missing`, several steps from the line of the seed that caused it. The user import is rendered for one realm name and the directory holds rows at whatever the second issuer says.

What the refusal actually compared was the issuer's **last path segment**. `https://elsewhere.invalid/realms/mcp-erp` passes that check and is served by nothing.

Three readings were on the table (#111 and its triage comment):

1. **The realm segment alone** — what the code did.
2. **Everything after the origin** — the ticket's recommendation. Scheme *and* authority may differ.
3. **Scheme only** — the two issuers differ in scheme and in nothing else.

## Decision

### Reading 3. The second issuer is the first with a different scheme, and nothing else moves.

**The profile already says so in three places, and the parser was the one that did not.** `tls.env` moves exactly one variable — `MCP_KEYCLOAK_ORIGIN` from `http://keycloak:8081` to `https://keycloak:8081` — and `compose.yaml` reads that one variable for every issuer string it builds, with the comment *"The scheme is the entire diff."* ADR-0014 bought the profile to make a browser login completable, which needs a secure context, which W3C Secure Contexts §3.1 grants on the scheme and the literal host string. The host string is what must **not** move: `keycloak` is what resolves identically inside the Compose network by Compose's own DNS and outside it by one `127.0.0.1 keycloak` line, which is the property ADR-0005 made the issuer carry.

So the rule the parser enforces is the rule the configuration already implements. Reading 3 does not decide a deployment shape; it writes down the one this exhibit ships.

**Reading 2 was recommended by the ticket and is not taken, because it does not close the case the ticket opened.** The symptom named in #111's own body is `https://elsewhere.invalid/realms/mcp-erp` against `http://keycloak:8081/realms/mcp-erp`. Those two have the same path. A whole-path comparison admits both of them, and admits every host and port on the internet with a `/realms/mcp-erp` on it. It closes a narrower class — a second issuer at a different path sharing its last segment, which is legacy Keycloak's `/auth/realms/…` shape — and leaves the seven-rows-at-an-address-nothing-serves case exactly where it was. A fix that leaves its own motivating example reachable is a fix that has to be made twice.

**What it costs is stated rather than discovered: a TLS profile served from another host or port is now a parse error.** No configuration this repository ships does that, and the one that might want to — terminating TLS at a different published port, or at `localhost` — would be a change to `compose.yaml`, `tls.env` and `keycloak/README.md` together. Moving the issuer's authority also breaks the property those files were written around, so the seed refusing it first is the cheap end of the same conversation. Reopening this is a seed change plus an amendment here, which is the deliberateness ADR-0011 asked of the profile in the first place.

### Two identifiers that differ in nothing are refused too

A `tls_issuer` equal to `issuer` is not one realm reached two ways. `IdentitySeed.issuers` would return the same string twice, `directory_entries` renders the cast once per issuer, and the directory would hold every person twice under one key. It reads as an authoring slip — a copied line whose scheme was never edited — and nothing downstream reports it, so it is refused where it is written. It falls out of the rule's own wording rather than being a separate policy: the second issuer differs from the first **in the scheme**, and an identical string differs in nothing.

### The realm name stays derived from the first issuer alone

`realm_of` is unchanged and keeps refusing an empty last path segment, but it is no longer what the second issuer is measured against, and it now runs on one issuer instead of two. The second needs no separate empty-segment guard: it either equals the first but for the scheme — whose segment was checked — or it does not, and is refused for that.

That is the defect in miniature. The realm name was doing two jobs: naming the realm for the user import, and standing in for *the same realm* when two identifiers were compared. It is adequate for the first and one segment wide for the second.

## Options considered

1. **Reading 1, the last path segment** — the status quo. Rejected: it is the defect. Any authority with a `/realms/mcp-erp` on it passes.
2. **Reading 2, everything after the origin** — #111's recommendation. Rejected above: it admits the example the ticket names as the symptom.
3. **Reading 3, scheme only** — taken.
4. **Compare against the one pair the profile can produce** — refuse anything but `http://` → `https://` on the same authority. Rejected as one specificity too far: it puts a scheme allow-list in a parser that has no opinion about schemes, and the seed is not the place that decides which two the profile uses.
5. **Refuse nothing in the parser and assert the pair in `tests/test_tls_profile.py` instead**, where the seed and `compose.yaml` are already held equal. Rejected: that file asserts the *committed* seed against the *committed* configuration, so it never sees a seed an author is in the middle of writing, which is the moment the refusal is for. It stays as the second altitude, unchanged.
6. **Allow a list of issuers rather than a second one**, with the constraint dropped. Rejected: a list is a shape for a question nobody has asked, and every member of it would need this same rule or none.

## Consequences

**One behaviour changes.** A seed whose `tls_issuer` moves the authority, the port, the path or nothing at all now fails at `read_identity_seed` with a message naming both issuers, where it previously rendered two files quietly. The committed seed is unaffected — `https://keycloak:8081/realms/mcp-erp` against `http://keycloak:8081/realms/mcp-erp` is exactly the admitted shape — so no rendering moves and `Seed renders clean` sees no diff.

**A future TLS profile at another authority is blocked on amending this ADR.** Stated as the cost, and it is the one reading 2 was preferred for avoiding. The counterweight is that such a profile is not merely unbuilt: it contradicts the resolves-identically-inside-and-outside property ADR-0005 gave the issuer, so the conversation it forces is one that has to happen anyway.

**No derived artifact moves, and the walk was performed.** Map constraint `#12` enrols four: the map's constraints — this ADR amends none, and adds no standing rule — [`docs/normative-register.md`](../normative-register.md), which records deviations from and interpretations of normative statements, and this is a constraint on our own seed file rather than a reading of anybody's specification; [`docs/attack-suite/scenarios.yaml`](../attack-suite/scenarios.yaml), whose membership rule is ADR-0010's one row per clause this project enforces, and nothing here is reachable by a caller — the seed is not an input any request touches; and the write-up, which is still unwritten and inherits nothing.

**Caveat.** The profile was not re-run under Docker for this decision. What was verified is that the committed seed parses, that every rendering is byte-identical, and that `tests/test_tls_profile.py` still holds the seed and `compose.yaml` equal — which is the claim the ADR rests on, since the strings it compares are the ones Compose interpolates.

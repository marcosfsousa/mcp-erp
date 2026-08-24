# ADR-0015: The second issuer is the first under another scheme

- **Status:** Accepted
- **Date:** 2026-08-24
- **Ticket:** [#111 A string where a list belongs, and an authority the realm check never looks at](https://github.com/marcosfsousa/mcp-erp/issues/111)
- **Amended:** 2026-08-24 — additive, by [#125](https://github.com/marcosfsousa/mcp-erp/issues/125). **The authored string is the canonical form of an issuer**, and the rule below is a comparison of authored strings rather than of parses. Three refusals are added, on *both* issuers rather than the second. See *The authored string is canonical, and the comparison above is of authored strings*. No decision here is reversed.
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

### The authored string is canonical, and the comparison above is of authored strings

*Added 2026-08-24 by [#125](https://github.com/marcosfsousa/mcp-erp/issues/125). Nothing above is reversed; this settles a question the decision above left implicit.*

The rule above compares two issuers. It did not say **which form of them** — and the implementation compared `urlsplit` parses while `IdentitySeed.issuers` and `directory_entries` rendered the strings the seed authored. Those are not the same string. `urlsplit` strips ASCII whitespace from both ends of a URL, deletes every tab, carriage return and newline wherever they sit — including inside a host name — and folds the scheme to lower case. So `HTTPS://keycloak:8081/realms/mcp-erp`, or the same with a leading space, passed the guard as *the first under another scheme* and then keyed seven directory rows at an address the authorization server never mints. A protocol-relative `//keycloak:8081/realms/mcp-erp` went further: `urlsplit` gives it an empty scheme, which differs from `http`, so it passed as a legitimate second issuer.

**The authored string is canonical. The loader never rewrites an issuer; it refuses one it would have to.**

The reason is that this string has a second author. The directory is keyed by issuer and subject, and the `iss` claim it is matched against is minted by Keycloak from the string Keycloak was configured with — which `compose.yaml` builds from `MCP_KEYCLOAK_ORIGIN`, the same source the seed is held equal to. A loader that normalised would be holding a second opinion about that string which nothing on the token side shares, and the first time the two opinions differed — a trailing slash, a percent-encoded segment — normalising would *cause* the address-nothing-serves failure rather than close it. Refusing cannot: a seed that loads is a seed whose issuers are exactly what the author wrote and exactly what the directory renders.

So `_refuse_an_issuer_the_parse_would_change` refuses three things, on **both** issuers, before the realm is taken from the first or the pair is compared:

1. **No scheme.** Not an address any token names.
2. **Any ASCII whitespace or ASCII control character, anywhere.** These are what the parse does not preserve.
3. **A scheme not already in lower case.** Same reason.

**The set stops exactly there, and the boundary is the criterion rather than taste.** A non-breaking space or a zero-width space in an issuer survives `urlsplit` untouched, so the guard and the renderings agree about it and nothing diverges — that issuer is simply wrong, which is a real defect but a different one, and it is not refused here. The rule is *what the parse would change*, which is why the list is three long and not four.

**Both issuers, not the second.** The finding arrived as a second-issuer bug because that is where the comparison is, but a damaged **first** issuer is worse: `realm_of` waves it through, since a leading space leaves the last path segment intact, and every directory row in the file is then keyed at an address nothing serves with no comparison anywhere to catch it.

**Ordering is part of the decision.** The canonical-form refusals run before `realm_of` and before the scheme comparison, so an author who writes `//keycloak:8081/realms/mcp-erp/` is told their issuer carries no scheme — the thing they typed — rather than that it names no realm in its last path segment, which is true, downstream, and about a different slip.

The comparison in the decision above is unchanged in substance. `_but_for_the_scheme` still parses, because a second hand-rolled URL parser in this package is how the metadata document ends up describing an address the endpoint is not served at. What changes is why that is safe: the parse is now **faithful**, because its argument was refused first — not a defence against a schemeless issuer, which no longer arrives.

## Options considered

1. **Reading 1, the last path segment** — the status quo. Rejected: it is the defect. Any authority with a `/realms/mcp-erp` on it passes.
2. **Reading 2, everything after the origin** — #111's recommendation. Rejected above: it admits the example the ticket names as the symptom.
3. **Reading 3, scheme only** — taken.
4. **Compare against the one pair the profile can produce** — refuse anything but `http://` → `https://` on the same authority. Rejected as one specificity too far: it puts a scheme allow-list in a parser that has no opinion about schemes, and the seed is not the place that decides which two the profile uses.
5. **Refuse nothing in the parser and assert the pair in `tests/test_tls_profile.py` instead**, where the seed and `compose.yaml` are already held equal. Rejected: that file asserts the *committed* seed against the *committed* configuration, so it never sees a seed an author is in the middle of writing, which is the moment the refusal is for. It stays as the second altitude, unchanged.
6. **Allow a list of issuers rather than a second one**, with the constraint dropped. Rejected: a list is a shape for a question nobody has asked, and every member of it would need this same rule or none.

*Added 2026-08-24 by [#125](https://github.com/marcosfsousa/mcp-erp/issues/125), against the canonical-form section.*

7. **Normalise instead of refusing** — take the `urlsplit` form as canonical, store it on `IdentitySeed`, and render it everywhere, so the guard and the renderings agree by construction. This is the symmetric fix and closes the divergence just as completely. Rejected: it makes the loader a second author of a string whose first author is Keycloak. The directory key has to be byte-equal to a claim minted from `MCP_KEYCLOAK_ORIGIN`, and normalising is only harmless while our normalisation and Keycloak's rendering agree on every input — which is an assumption with no test that could hold it, and whose first failure is silent. It would also put the committed seed and its renderings out of step for the first time, which is the property `Seed renders clean` exists to police. Refusing has neither cost: what loads is what was written.
8. **One round-trip test** — refuse an issuer where `urlunsplit(urlsplit(issuer)) != issuer`, in place of the three named refusals. One rule instead of three, catching the same whitespace, control-character and scheme-case shapes. Rejected on the message: a round-trip failure can only report *this is not the form it parses to* and print two strings that, in the case that matters most — a tab inside a host name — are visually identical. It also delegates the definition of *canonical* to a standard-library function whose whitespace handling has moved across Python releases. It does not catch the protocol-relative issuer either, which round-trips clean and needs its own check under any option here.

## Consequences

**One behaviour changes.** A seed whose `tls_issuer` moves the authority, the port, the path or nothing at all now fails at `read_identity_seed` with a message naming both issuers, where it previously rendered two files quietly. The committed seed is unaffected — `https://keycloak:8081/realms/mcp-erp` against `http://keycloak:8081/realms/mcp-erp` is exactly the admitted shape — so no rendering moves and `Seed renders clean` sees no diff.

**A future TLS profile at another authority is blocked on amending this ADR.** Stated as the cost, and it is the one reading 2 was preferred for avoiding. The counterweight is that such a profile is not merely unbuilt: it contradicts the resolves-identically-inside-and-outside property ADR-0005 gave the issuer, so the conversation it forces is one that has to happen anyway.

**No derived artifact moves, and the walk was performed.** Map constraint `#12` enrols four: the map's constraints — this ADR amends none, and adds no standing rule — [`docs/normative-register.md`](../normative-register.md), which records deviations from and interpretations of normative statements, and this is a constraint on our own seed file rather than a reading of anybody's specification; [`docs/attack-suite/scenarios.yaml`](../attack-suite/scenarios.yaml), whose membership rule is ADR-0010's one row per clause this project enforces, and nothing here is reachable by a caller — the seed is not an input any request touches; and the write-up, which is still unwritten and inherits nothing.

**Caveat.** The profile was not re-run under Docker for this decision. What was verified is that the committed seed parses, that every rendering is byte-identical, and that `tests/test_tls_profile.py` still holds the seed and `compose.yaml` equal — which is the claim the ADR rests on, since the strings it compares are the ones Compose interpolates.

---

*Consequences of the 2026-08-24 amendment by [#125](https://github.com/marcosfsousa/mcp-erp/issues/125).*

**Three more seeds now fail that previously rendered.** An issuer at either position carrying no scheme, ASCII whitespace or an ASCII control character, or an upper-case scheme, fails at `read_identity_seed` naming the issuer, the offending character where there is one, and what the parse would have done to it. The committed seed is again unaffected: both its issuers are already the form they parse to, so no rendering moves and `Seed renders clean` sees no diff.

**The first issuer gains refusals it never had.** Everything the decision above says about the second issuer was, until now, the *only* validation any issuer got beyond `realm_of`. A damaged first issuer had no comparison to fail against and no guard of its own.

**One narrowing that #121 introduced is closed.** Removing the `realm_of` check on the second issuer removed, incidentally, the only place a tab or line ending inside a second issuer would have been noticed — `realm_of` splits on the raw string, so damage after the last `/` changed the realm name it derived and the seed failed for the wrong reason but did fail. The refusals here close that on purpose and at both issuers, which is wider than what was lost. Restoring the `realm_of` check was considered and is not done: it caught this by accident, at one position, and only when the damage fell in the last path segment.

**What is deliberately still admitted.** An issuer carrying a query or a fragment, which **RFC 8414 §2** forbids of an issuer identifier; and non-ASCII whitespace or zero-width characters. Neither is a case where the guard and the renderings disagree, so neither is this defect. The first is a normative-register question if it is taken up at all, and taking it here would have put a specification reading inside a refusal set whose stated criterion is *what the parse would change*.

**No derived artifact moves, and the walk was performed again for the amendment.** Map constraint `#12` now enrols five. The map's constraints — this amendment amends none and adds no standing rule, and it generates no rows, so nothing here needs a ceiling or an index. [`docs/normative-register.md`](../normative-register.md) — unchanged: this is a constraint on our own seed file, not a reading of a normative statement, and the one adjacent normative statement it touches (RFC 8414 §2's *no query or fragment*) is named above as **not** taken, so there is no interpretation to record. [`docs/attack-suite/scenarios.yaml`](../attack-suite/scenarios.yaml) — unchanged: the seed is not an input any request touches, and ADR-0010's membership rule is one row per clause reachable by a caller. [`docs/decision-matrix/matrix.yaml`](../decision-matrix/matrix.yaml) — unchanged: it is canonical for `(principal × tool × resource → expected)` and nothing here alters a principal, a tool or an expectation. The write-up — still unwritten; `docs/write-up-notes.md` gains no line, on the same ground the decision above took, and its ADR counts are a snapshot explicitly dated *Verified 2026-08-18* with the commands to re-derive them, so they are not an index this commit is obliged to move.

**Caveat.** As above, the profile was not re-run under Docker. What was verified for the amendment is that the committed seed parses, that both renderings are byte-identical to the committed files, and that the refusals are red-capable — removing the guard fails thirteen cases in `tests/authorization/test_identity.py` and nothing else.

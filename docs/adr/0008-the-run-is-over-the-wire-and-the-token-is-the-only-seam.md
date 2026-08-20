# ADR-0008: The run is over the wire, and the token is the only seam

- **Status:** Accepted
- **Date:** 2026-08-11
- **Ticket:** [#8 Decide what performs the run](https://github.com/marcosfsousa/mcp-erp/issues/8)
- **Evidence:** [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md), [`docs/research/0003-2026-07-28-authorization-requirements.md`](../research/0003-2026-07-28-authorization-requirements.md); [ADR-0001](0001-off-the-shelf-clients-cannot-run-a-modern-only-server.md), [ADR-0004](0004-layer-2-is-a-portable-pattern-layer-3-is-ejectable.md), [ADR-0006](0006-fail-closed-in-a-fixed-order.md), [ADR-0007](0007-the-realm-is-the-exhibit.md); Client Identity Metadata Document draft `-00` §3 and §6.5; map constraints #1, #4, #5, #6, #8, #9, #10; official Python `mcp` 2.0.0 documentation, read 2026-08-11
- **Amended:** 2026-08-18 — additive, by [#53](https://github.com/marcosfsousa/mcp-erp/issues/53). This ADR made a document's path immutable without saying that its *origin* is the other half of the identifier and is held by nothing. See *The identifier's origin is held by an account name*. No decision here is changed.
- **Amended:** 2026-08-20 — additive, by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46), which built the conformance client, the preflight and the blocking job. The packaging claim is executed rather than read, and three things this ADR did not anticipate are recorded. See *Consequences*. No decision here is changed.

## Question

Map constraint #1 makes the run primary: the proof is a real authorization flow completing against a running server. The ticket asked what performs it, and framed a self-written conformance client as the expensive option that buys everything except the one thing that matters — contact with software we did not write.

ADR-0001 removed the false constraint. The server is demonstrable today, so the conformance client is not the only thing that can run it. What was left is the whole shape of the run: on what substrate, at what altitude, performed by what, packaged how, enforced where, and cuttable or not.

## Decision

### The ticket's premise was inverted by the package that ships the protocol

The official Python `mcp` package reached 2.0.0 on **2026-07-28, the same day as the revision**, and serves both protocol eras from one endpoint. The legacy era cannot be turned off: there is no `legacy=` option and no version allowlist — not on `streamable_http_app()`, not on `run()`, not on the session manager. Routing happens on `MCP-Protocol-Version` before any handler is reached, and a request carrying no header at all is routed as legacy, because that is how a pre-2026 client's `initialize` arrives.

So the ticket's option 2 — dual-era support, described there as *"exactly the scope that quietly doubles a build"* — is the **default**, and modern-only is what we would have to build. Dual-era stops being a feature built and becomes a fact documented. Not one line of it is written.

This is worth stating as a general shape rather than a lucky break: the map's *legacy: discussable, not built* survives as written, and acquires a third state it did not anticipate — **inherited**. [ADR-0009](0009-not-built-is-not-unreachable.md) owns what that costs.

`stateless_http=True` is set. It touches the **legacy leg alone** — requests are routed on the version header before the flag is read, so the modern path never sees it — and it gives legacy callers throwaway per-request sessions with no `Mcp-Session-Id` issued and nothing remembered between requests. Map constraint #5 therefore survives intact: two replicas, round-robin, no sticky routing. What the flag disables is server-to-client channels, which constraint #6 already refused. The coin was already spent.

The conceded cost, stated rather than buried: **sessions re-enter through a door we do not control**, and the statelessness claim carries an asterisk in the write-up rather than standing unqualified.

The gain is what decided it. A reader can point their own client at this server and have it *work*. Research 0004's dominant failure mode — *auth succeeds, protocol fails* — is gone, and it was the mode that made every third-party proof partial.

### Everything drives the wire

`docker compose up` brings two replicas and Keycloak. **Every decision-matrix row and every attack scenario drives real HTTP with real tokens.** One altitude, one report.

#9's own standard decides it: a test that passes for the wrong reason proves nothing — and a matrix row green in-process while the wire path goes unexercised is exactly that failure, in its least visible form. Driving the wire also makes *run primary* literal, rather than a claim resting on a single authorization flow with everything else asserted underneath it.

One suite stays in-process, deliberately: **ADR-0004's ejection test** drives `decide(principal, action, resource)` with no Docker and no domain vocabulary, so *cheap to execute* survives this decision unchanged. That is the exception, and it is the only one.

### Both legs perform the flow, and each is named for what it is

Tokens are minted directly for the suites, which means the authorization code flow still needs a performer. There are two, and neither substitutes for the other:

| Leg | What it is | What it buys |
| --- | --- | --- |
| **Conformance client**, headless, in continuous integration | Reproducible, asserts on the wire, exercises the Client Identity Metadata Document end to end | The gate, and the only automatable proof |
| **A recorded session with a real third-party client** | Not reproducible by a machine; a witnessed demonstration | Third-party contact, which no code we write can supply |

This was ADR-0001's hedge, and the substrate decision above upgraded it: with both eras served, the third-party leg is a **full success rather than a partial one**. It is also the only evidence in the exhibit a reader cannot accuse of circularity, which is precisely why it cannot be dropped in favour of the leg that runs itself.

### The Client Identity Metadata Document is hosted, and its path never changes

The document is published as a **static file on GitHub Pages**. Hosting it inside Compose over plain HTTP is not available: the draft is a hard `MUST` — *"Client identifier URLs MUST have an 'https' scheme, MUST contain a path component"* — and §6.5 adds that authorization servers *"SHOULD avoid fetching any URLs using private or loopback addresses."* That is the exact pattern attack-suite clause #16 (`cimd_ssrf_loopback`) exists to refuse. Exhibiting a behaviour and defending against it in one repository would be incoherent.

Pages supplies real HTTPS with a path component for free, and it **decouples "a public HTTPS document" from "a public deployment of the server"** — so research 0003's finding that deployment stays additive survives, and #10 stays genuinely open rather than being decided from inside this ticket.

**Documents are immutable once published. A change is a new path**, `/clients/conformance/1.json` then `/2.json`, never an edit in place.

The reason is a specification point, not a continuous-integration convenience, and it holds even if no automation existed: **the `client_id` *is* the URL.** Mutating the document at that URL silently changes a client's identity metadata under the authorization server — the same identifier now describing a different client. Draft `-01` added security considerations for exactly this, which research 0003 records. Immutability makes a change of identity visible as a change of identifier, which is what an identifier is for.

It also happens to close a gap. Pages serves from `main`, so a pull request cannot publish its own document, and a pull request that edited one in place would test against the version it was replacing. Under immutability the sequence has no such window: one pull request adds `/2.json` while the client still names `/1.json`, and a second points the client at `/2.json` once Pages is serving it. At every moment the run fetches exactly the document the client under test names.

#### The identifier's origin is held by an account name

*Added 2026-08-18 by [#53](https://github.com/marcosfsousa/mcp-erp/issues/53), after the document went live at `https://marcosfsousa.github.io/mcp-erp/clients/conformance/1.json`.*

Immutability above is a promise about a **path**, kept by a check over this repository's history. The identifier has two halves, and nothing holds the other one. `marcosfsousa.github.io` is derived from an account name, which GitHub releases for anyone to claim once it is changed.

So the failure this ADR spent its argument preventing has a second entrance. Rename the account and whoever claims the old name inherits every identifier this exhibit has published — free to serve a *different* document at the *same* `client_id`, which is the substitution the immutability rule exists to make impossible. The rule is not wrong; its scope was simply never stated, and an unstated scope reads as a guarantee.

**The two renames fail in opposite directions, and that is the useful part.**

| Rename | What the authorization server sees | Outcome |
| --- | --- | --- |
| The **repository** | The path 404s | **Fails closed.** Draft `-00` §4.3: the server *"SHOULD abort the authorization request"* |
| The **account** | HTTP 200, a well-formed document, a different client | **Fails open**, and silently |

A 404 is a bad afternoon. A 200 from a stranger is the thing the exhibit refuses in `cimd_id_url_mismatch` and would then be shipping.

**Consequence, stated rather than left to be rediscovered:** the account name and the repository name are load-bearing identifiers of this exhibit, on the same footing as the document's bytes. Not renaming them is a constraint, not a preference.

**The route that would close it, declined for v1.** A custom domain moves the trust anchor from GitHub's account namespace to DNS this project controls, so no third party can ever come to answer at the identifier. It costs a domain, its renewal, and a verification step — and it trades one permanent dependency for another, since a lapsed registration fails open in exactly the same way. Declined on cost, not on impossibility. It is the same shape as [ADR-0011](0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md)'s treatment of deviation 2: named, priced, and carried.

**Claim rejected, recorded so it is not re-litigated.** A vendor write-up states that Client Identity Metadata Documents reject `localhost` redirect URIs outright. This contradicts the draft, which prohibits no such thing, and contradicts research 0003's open ambiguity #7; Claude Code demonstrably pairs a hosted document with a `localhost` callback. **Only the document must be HTTPS, never the redirect URI.**

### The suites and the demonstrator differ by one object

The conformance client ships as **one package with two entry points**: a library surface the suites import, and a runnable entry point that performs the authorization code flow.

That is not a compromise between two designs; it is what the protocol package's own shape dictates. In `mcp` 2.0.0 the unified `Client` takes no authentication parameter. Authentication attaches to the HTTP client underneath the transport:

```python
async with httpx2.AsyncClient(auth=<auth object>) as http_client:
    transport = streamable_http_client(url, http_client=http_client)
    async with Client(transport) as client:
        ...
```

`OAuthClientProvider` — which performs the full flow, and takes `client_metadata_url=` for the hosted document above — is one such object. A pre-minted token is another, and a trivially small one. Connect, call, and assert-on-the-wire are **identical on both sides**. Mint-versus-earn is a constructor argument, not an architecture.

ADR-0001's live worry was co-evolution: written against the spec text, *"or it quietly co-evolves into a pair that only works with itself."* The substrate decision above already answers most of it — both sides speak the wire through the **same third-party implementation**, so neither is our own protocol code. What could still co-evolve is the **assertions**, and no packaging choice prevents that; only writing them from cited clauses does. Physical separation would buy the appearance of independence at real cost in a solo build, while the recorded third-party session is the evidence that is actually non-circular.

The token helper is built **once and deliberately** — minting per Person × scope set, cached within a run. Both proof artifacts depend on it, and it is the piece most likely to become slow and duplicated if it grows organically.

### The online run gates, and three mechanisms are what make that acceptable

The conformance client's leg is the only part of the suite that needs outbound network and a document it cannot publish for itself. It gets **its own job on pull requests**, network allowed, and it blocks.

`ci.yml` argues that *"a keyless run is a standing assertion that the suites are offline."* Q4's fetch needs no key — a public Pages URL is unauthenticated — so keylessness survives; what breaks is the implication *keyless therefore offline*. The assertion is restated **per job** in `ci.yml`, which is more honest than the repository-wide version it replaces.

Blocking on something outside our control is only defensible because three mechanisms take it back:

1. **Exact version pinning.** A preview-feature regression cannot spontaneously turn anything red if the image does not move. It moves when we move it, inside a version-bump pull request, which is where a blocking check is doing its job rather than being a liability. This generalised past this ticket and became a standing map constraint; [ADR-0007](0007-the-realm-is-the-exhibit.md) carries the Keycloak half.
2. **A preflight step.** Before Compose starts, fetch the document URL and assert HTTP 200 and that the body hashes to the committed copy. Without it, Pages being unreachable and our server rejecting a valid flow present identically as *the flow failed*. With it, an external cause fails a **named step before our server has run at all** — the skeleton's own rule, that a red check should name the layer without anyone opening logs.
3. **Immutable document paths**, above, which remove the one failure mode that would have been a genuine false green.

What remains is a Pages or egress outage landing inside a merge window. Rare, short, and already absorbed: the `main` ruleset grants Admin bypass on pull requests, so an outage costs one recorded override rather than the ability to ship.

### The capability is ship-line; the enforcement is not the claim

The conformance run joins map constraint #8, the v1 ship line, **as a capability**: *a headless run completing an authorization code flow with a hosted Client Identity Metadata Document and asserting on the wire.*

The wording matters and an earlier draft got it wrong by appending *"green in continuous integration."* The ship line has never spoken about enforcement — its items are capabilities and artifacts, and the attack suite's membership does not derive from being a required check. Ship-line membership and merge-gating are separable, and only the first is a claim about what the exhibit *is*.

They are decided the same way here, but for different reasons. The capability ships because it is the only automatable proof of the flow. The job gates because a ship-line capability whose check cannot fail the build is the one thing a reader most wants to see enforced and the one thing nothing enforces — and because the skeleton's warning inverts cleanly: a check that can never block becomes noise, so the first genuine regression would read exactly like the outage it was designed to tolerate.

## Options considered

1. **Target the current widely-supported revision** (the ticket's option 3). Cheapest and best interop; contradicts the premise the exhibit exists to demonstrate.
2. **Build modern-only and refuse the legacy era at the edge.** Available — middleware ahead of the application can reject on the version header even though the package offers no switch — and it would make ADR-0006's gate order the whole story. Rejected in [ADR-0009](0009-not-built-is-not-unreachable.md), where the argument belongs.
3. **Split altitudes:** decision matrix in-process, attack suite over the wire. Fast, and it reintroduces the invisible failure #9's standard exists to forbid.
4. **Host the identity document inside Compose over plain HTTP.** Fully offline and self-contained; refused by the draft's `MUST`, and incoherent beside clause #16.
5. **Two packages split at the token boundary.** A defensible seam, one object wide — two packaging manifests and a version relationship for a single constructor argument.
6. **The conformance client in its own repository.** The strongest anti-circularity signal available, at the cost of two repositories in a solo build, cross-repository checkout, version skew, and the document's hosting splitting off too.
7. **No shared code, deliberate duplication.** Maximum independence of the assertions; the wire path written twice and the two copies drifting silently, which is the failure the exhibit exists to make visible.
8. **The online job post-merge only.** Pull-request runs stay fully offline, and a job depending on the Pages deployment tests exactly the document that commit published — genuinely elegant. Rejected because it stops being a gate: a break is found after landing.
9. **The online job non-blocking**, with the claim resting on the run record. Separates enforcement from the ship-line claim, which was the right structural insight; rejected once pinning, preflight and immutability removed the reasons it was needed.
10. **Per-pull-request Pages previews.** No native support; synthesising them means a pull request's workflow writing to a published branch, which needs `contents: write` against the skeleton's least-privilege rule and is impossible from a fork.
11. **A single mutable document at a fixed path.** One URL forever, and a client identifier whose meaning changes underneath the authorization server without anything recording that it did.

## Consequences

**Cost.** An outbound fetch inside continuous integration, and with it the loss of a clean offline claim for one job. A preflight step that exists only to make a failure legible. A document-publishing sequence that costs two pull requests instead of one, on a file that will change perhaps twice. The repository's **first required status check**, which means adding a required-status-checks rule to the `main` ruleset — it currently has none — and adopting the name-contract test the skeleton ships. And a statelessness claim that now needs a qualifying sentence wherever it appears.

**A correction to ADR-0001.** Its consequences record that the conformance client *"survives the cut list on weaker grounds than load-bearing, so it is now a legitimate cut candidate."* That is no longer true, and for a reason that ADR could not have seen: packaging it as one library with two entry points means **cutting it removes the runnable entry point and the hosted document only**. The transport, the calls and the assertions all stay, because the suites import them. The saving fell from a deliberate to about a day, while the value rose. It is not on the cut list, and map note #9 is unchanged — it never named the conformance client, and adding it now would record a cut nobody would take.

**Not a contradiction of the vocabulary.** [`CONTEXT.md`](../../CONTEXT.md) defines the conformance client as *"a demonstrator, not a dependency."* That still holds: the server runs, and every other suite passes, without it. Ship-line membership makes it a shipped proof artifact, not a thing the server depends on.

**Two documents amended.** [ADR-0006](0006-fail-closed-in-a-fixed-order.md) described a gate chain that is not uniform across both legs, and says so now. [ADR-0007](0007-the-realm-is-the-exhibit.md) put Keycloak behind a Dockerfile without stating how its version is pinned, and says so now. The general rule was lifted out of both and into the map as a standing constraint, because it binds Postgres, the Python runtime and every future image equally — with `ci.yml`'s deliberate floating-major convention for actions preserved as a named exception.

**Input to other tickets.**

- **#9 (attack suite)** decides whether scenarios 17 (`as_metadata_issuer_spoof`) and 18 (`mixup_iss_mismatch`) are adopted. Both are marked *(client)* in research 0003 — they assert on a **client's** behaviour, so only a client we control can exercise them. Adopting them makes the conformance client a subject under test and hands it the attack suite's protection from cuts outright.
- **#12 (module boundaries)** inherits the one-package-two-entry-points shape, and the auth object as the seam between them.
- **#15 (walkthrough)** owns which Person the conformance client authenticates as. The demonstrator's script is the exhibit's narrative, and ADR-0007 has already nominated the moment worth using.
- **#10 (deployment)** is untouched by design: the hosted document decoupled a public HTTPS URL from a public deployment, so that ticket stays open on its own merits.


**Executed 2026-08-20 by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46), and the caveat above is discharged for this ADR's own leg.** The authentication attachment point is what this document read it to be: `mcp` 2.0.0's unified `Client` takes no authentication parameter, the auth object hangs on the HTTP client underneath the transport, and `connect(auth)` runs the identical protocol conversation with an `OAuthClientProvider` and with a pre-minted bearer. *Mint versus earn is a constructor argument* is now an assertion in `tests/conformance/` rather than a reading of documentation.

Three things this document did not anticipate, all found by running it:

1. **Keycloak's Client Identity Metadata Document support is a client policy, not a switch.** `--features=cimd` makes the discovery document advertise support and the realm still refuses the identifier until a policy admits it. [ADR-0007](0007-the-realm-is-the-exhibit.md) carries what the realm gained, including the realm-level default client scopes a provisioned client inherits.
2. **The `localhost` callback survives a conformant configuration.** The rejected vendor claim above is refuted twice over: the draft prohibits nothing, and Keycloak's own executor accepts the loopback redirect with its `http`-scheme allowance switched **off**, because that flag governs the identifier and the URL-valued metadata properties rather than `redirect_uris`.
3. **The scope selection is the resource server's, not the client's.** The protocol package derives what it requests from the `WWW-Authenticate` challenge, so the requested-versus-granted comparison this ADR handed to the conformance client turns out to be a statement about the authorization server rather than about a list the client held. [ADR-0012](0012-the-token-names-a-capability-never-a-role.md) records the answer: the `MUST` is honoured, and the normative register gains no row.

**Caveat, in the same terms ADR-0001 used.** Nothing here was executed. The protocol package's era routing, its authentication attachment point and the absence of a legacy switch all derive from its published documentation, read 2026-08-11, because there is no Python in this repository yet to run them against. ADR-0009's three assertions exist precisely to convert the load-bearing part of that reading into something executed.

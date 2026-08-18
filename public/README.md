# The published surface

Everything in this directory is served publicly over HTTPS at
<https://marcosfsousa.github.io/mcp-erp/>, by
[`.github/workflows/pages.yml`](https://github.com/marcosfsousa/mcp-erp/blob/main/.github/workflows/pages.yml) on every push to
`main`. Nothing else in the repository is published — the workflow uploads this
directory and no other.

Today it holds one artifact and this note, both served:

| Path | Served at |
| --- | --- |
| `clients/conformance/1.json` | <https://marcosfsousa.github.io/mcp-erp/clients/conformance/1.json> |
| `README.md` | <https://marcosfsousa.github.io/mcp-erp/README.md> |

The note ships with the artifact deliberately. Anyone who dereferences the
`client_id` and wonders why it looks the way it does can follow the reasoning
from what they already have, without an account or a clone.

**Every link below is absolute, and must stay that way.** Only this directory is
uploaded, so a relative path out of it — `../docs/adr/…` — resolves in a clone
and returns 404 on the site, which is the one place the link was added for. The
first version of this file made exactly that mistake.

**One-time setup, not yet done automatically anywhere:** the Pages site must
exist before the workflow can deploy to it. `configure-pages` will not create
it — enabling Pages needs a token the workflow deliberately does not have. See
the header of [`.github/workflows/pages.yml`](https://github.com/marcosfsousa/mcp-erp/blob/main/.github/workflows/pages.yml).

## A published document is never edited

**A change is a new path** — `2.json`, never a rewrite of `1.json`.

The reason is a specification point rather than a continuous-integration
convenience: the `client_id` *is* the URL. Mutating the document at that URL
silently changes a client's identity metadata under the authorization server —
the same identifier now describing a different client. Immutability makes a
change of identity visible as a change of identifier, which is what an
identifier is for. [ADR-0008](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md)
carries the full argument.

A job checks it rather than a reviewer. `Published documents are immutable` in
[`.github/workflows/ci.yml`](https://github.com/marcosfsousa/mcp-erp/blob/main/.github/workflows/ci.yml) fails on any change
that modifies, removes or retypes a `*.json` file under `clients/`, at any depth
— adding one is the only operation it permits.

**It reports; it does not yet block.** No ruleset requires its context, so a red
result is visible and ignorable. That is true of every job in `ci.yml` today —
the repository still has no required status check, and the test that holds job
names and required contexts equal in both directions arrives with #47. This job
belongs in that set when it lands. Saying so here is cheaper than discovering
later that the mechanism was assumed to be a gate.

It also decides the publishing sequence, because GitHub Pages serves from `main`
and a pull request therefore cannot publish the document it tests against. One
pull request adds `2.json` while the conformance client still names `1.json`; a
second points the client at `2.json` once Pages is serving it. At every moment
the run fetches exactly the document the client under test names.

`.gitattributes` pins these files to `-text` so no checkout rewrites their line
endings. The preflight step hashes the fetched body against the committed copy,
which only means anything if the committed copy has one set of bytes.

**What this does not cover: the origin.** The rule holds a *path* still. The
other half of the identifier is `marcosfsousa.github.io`, which is derived from
an account name that GitHub releases for anyone to claim once it changes — so
renaming the account would let a stranger answer at these identifiers, while
renaming the repository merely 404s them. The account name and the repository
name are therefore load-bearing, and not renaming them is a constraint rather
than a preference. [ADR-0008](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md)
has the asymmetry and the route that would close it.

## Why the document is hosted here at all

Hosting it inside Compose over plain HTTP is not available. The Client Identity
Metadata Document draft `-00` §3 is a hard `MUST` — *"Client identifier URLs
MUST have an 'https' scheme, MUST contain a path component"* — and §6.5 adds
that authorization servers *"SHOULD avoid fetching any URLs using private or
loopback addresses."* That is the exact pattern attack-suite clause 16,
`cimd_ssrf_loopback`, exists to refuse. Exhibiting a behaviour and defending
against it in one repository would be incoherent.

Pages supplies real HTTPS with a path component, and decouples *a public HTTPS
document* from *a public deployment of the server* — which is what let
[ADR-0011](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0011-it-runs-on-the-readers-machine-and-the-deviation-is-ours.md)
decline hosting outright while this capability survived.

## The redirect URI is `localhost`, deliberately

`clients/conformance/1.json` declares two loopback callbacks, on port `8085`:

```json
"redirect_uris": [
  "http://127.0.0.1:8085/callback",
  "http://localhost:8085/callback"
]
```

**Only the document must be HTTPS, never the redirect URI.** A vendor write-up
states that Client Identity Metadata Documents reject `localhost` redirect URIs
outright; that claim is rejected and recorded in
[ADR-0008](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md)
so it is not re-litigated. The draft prohibits no such thing, the Model Context
Protocol specification's own canonical example document lists
`http://127.0.0.1:3000/callback` and `http://localhost:3000/callback`, and
Claude Code demonstrably pairs a hosted document with a `localhost` callback.

Both forms appear because an authorization server matching redirect URIs by
exact string accepts only the form the client actually sends. The port is fixed
rather than omitted: RFC 8252 §7.3 puts a `MUST` on the authorization server to
accept any port on a loopback redirect, but Keycloak's honouring of that under
the preview `--features=cimd` flag is unverified, and research 0003 records a
real interop regression on exactly this matching
([claude-code#37747](https://github.com/anthropics/claude-code/issues/37747)).
Being wrong about it would cost a new document version. `8085` sits alongside
the exhibit's other fixed ports — `8080` the server, `8081` Keycloak, `9090` the
decoy audience.

## What the document does and does not declare

`client_id`, `client_name` and `redirect_uris` are the three properties the
Model Context Protocol requires; the draft itself requires only `client_id`.
`client_id` matches the document URL exactly, which the authorization server
`MUST` validate.

`token_endpoint_auth_method` is `"none"`. Every client in the realm is public
and authenticates with Proof Key for Code Exchange
([ADR-0007](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0007-the-realm-is-the-exhibit.md)); no secret exists
anywhere in this repository, and draft §4.1 forbids any method built around a
shared symmetric secret in this document regardless.

`grant_types` names `refresh_token` as well as `authorization_code` because the
realm rotates refresh tokens with zero reuse and the attack suite asserts that a
replayed one revokes the grant — so whether the authorization server issues a
refresh token to this client changes an authorization decision. `response_types`
is `["code"]` for the matching reason: it is what closes off every other
response type, including the implicit flow OAuth 2.1 removed.

**`scope` is deliberately absent.** The three capability scopes are gated by
role scope mappings and displayed on the consent screen
([ADR-0012](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0012-the-token-names-a-capability-never-a-role.md)), and
the client narrows its request through the `scope` parameter. Restating the
ceiling here would add a second place for that vocabulary to drift, in a file
that cannot be corrected in place — and under the governing rule a field earns
its place only if it changes an authorization decision. Whether Keycloak's
preview implementation reads this property at all is unverified, which is
exactly the kind of bet an immutable document should not take.

`client_uri` and `logo_uri` are absent for the same reason: they decide nothing.
Both are tempting — they are what a human would read on a consent screen — and
neither survives the governing rule. The screen already carries the client name
and the three capability lines, which is the delegation ceiling the screen
exists to show.

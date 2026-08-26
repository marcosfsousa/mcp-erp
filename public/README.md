# The published surface

Everything in this directory is served publicly over HTTPS at
<https://marcosfsousa.github.io/mcp-erp/>, by
[`.github/workflows/pages.yml`](https://github.com/marcosfsousa/mcp-erp/blob/main/.github/workflows/pages.yml) on every push to
`main`. Nothing else in the repository is published — the workflow uploads this
directory and no other.

Today it holds two artifacts and this note, all served:

| Path | Served at |
| --- | --- |
| `clients/conformance/1.json` | <https://marcosfsousa.github.io/mcp-erp/clients/conformance/1.json> |
| `clients/inspector/1.json` | <https://marcosfsousa.github.io/mcp-erp/clients/inspector/1.json> |
| `README.md` | <https://marcosfsousa.github.io/mcp-erp/README.md> |

The note ships with the artifacts deliberately. Anyone who dereferences a
`client_id` and wonders why it looks the way it does can follow the reasoning
from what they already have, without an account or a clone.

## Why there are two documents rather than one

The conformance document is what the suite drives. The Inspector document exists
because MCP Inspector cannot use the first one, for a reason that is worth
writing down rather than rediscovering.

The client library Inspector ships appends `offline_access` to the scopes it
asks for whenever two things are true at once: the authorization server
advertises that scope, and **the client's own metadata document declares the
`refresh_token` grant**. This realm advertises it, and the conformance document
declares that grant — so every Inspector run against the conformance identifier
asks for a scope no client here is permitted, and Keycloak refuses the
authorization request with `invalid_scope` before it provisions anything. No
Inspector flag suppresses it; the augmentation reads the document, not the
command line.

The Inspector document therefore declares `authorization_code` and nothing else.
That is the whole of the difference, and it is deliberate: this exhibit issues
five-minute tokens, and the one Person who holds an offline token holds it for
the recorded third-party session, which is argued in
[ADR-0007](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0007-the-realm-is-the-exhibit.md).
A tool that only ever reads and calls has no business asking for a long-lived
one.

Its `redirect_uris` name Inspector's own loopback callbacks — `6274` for the web
interface, `6276` for the command line, each in both spellings a caller may use.
The web interface's callback is not configurable, so a document that omitted it
would leave the mode most readers reach for unable to log in at all.

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

**It blocks, since [#47](https://github.com/marcosfsousa/mcp-erp/issues/47).**
Its context is required on `main`, as is every other job in `ci.yml` — set
equality in both directions, no exemption list — and
`tests/test_required_checks.py` holds the job names and the ruleset's required
contexts equal on every run, so a rename fails a check instead of quietly
detaching the rule that pointed at the old name.

**Force pushes to `main` are blocked in the same ruleset, and this job is why it
matters.** With no comparable base commit it warns and passes, having checked
nothing. A pull request always carries a base and an ordinary push always carries
a real predecessor, so the only reachable path to that green tick is a force push
to `main`. The `non_fast_forward` rule that refuses one has been in the ruleset
since it was created, before anybody noticed it was load-bearing here; what #47
added is the assertion that fails if it is ever removed.

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

## The other side has to invite it

*Added 2026-08-20 by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46),
which drove the flow.* Publishing the document is half of what makes it an
identifier. The authorization server has to be willing to dereference it, and
Keycloak is not by default: the preview feature makes the discovery document
advertise support, and the realm answers *Client not found* until a **client
policy** names which identifiers it will fetch.

`keycloak/import/mcp-erp-realm.json` carries that policy — `https` from
`marcosfsousa.github.io` and nothing else — and
[`keycloak/README.md`](https://github.com/marcosfsousa/mcp-erp/blob/main/keycloak/README.md)
carries the reasoning, including what a client provisioned this way inherits and
why the realm grew default client scopes for the first time.

**One claim on this page is confirmed by that configuration**: the loopback
redirect URIs below are accepted with Keycloak's `http`-scheme allowance
switched **off**, which is the production setting. That flag governs the client
identifier and the URL-valued metadata properties, and `redirect_uris` is not
among them.

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

## What the documents declare, and what they leave out

**This section describes `clients/conformance/1.json` except where a paragraph
says otherwise.** The two documents answer these questions the same way apart
from `grant_types`, called out below where it arises, and `redirect_uris`, whose
values name each client's own callbacks and are covered where each is described.
Neither gets a second copy of this section — a governing rule restated twice is a
rule with two places to drift.

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

**This is the one field the two documents differ on.**
`clients/inspector/1.json` names `authorization_code` alone, and the reason is
the same governing rule read the other way: for that client the grant changes an
authorization decision it should not. A client library that sees
`refresh_token` in a document adds `offline_access` to the scopes it requests,
whatever the caller asked for — so declaring the grant there would make every
Inspector run demand a long-lived token from a realm built on five-minute ones.
The section above has the mechanism.

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

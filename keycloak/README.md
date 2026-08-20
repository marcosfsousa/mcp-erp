# `keycloak/` — what the authorization server is imported from

Two kinds of file live here, and the difference is the whole point of the
directory:

| | Written by | Edited by hand |
| --- | --- | --- |
| `import/mcp-erp-users-0.json` | `python -m mcp_erp.authorization.identity` | never |
| `import/mcp-erp-realm.json` | a person | always |
| `import/mcp-erp-neighbour-realm.json` | a person | always |

ADR-0007 decided that the clients, redirect URIs, client scopes and audience
mappers are **hand-written JSON** — *"that section is the exhibit; a generated
blob is worse evidence than authored intent"* — and that only the users are
generated, from the seed, so the subject join cannot drift from the ERP's rows.

**Two files are what make that rule structural.** A `users` array spliced into
the authored realm would leave generated content sitting in the file a reader is
invited to open and edit, one hand-edit away from being silently overwritten by
the next render. Split, the rendered file is never edited and the authored file
has no `users` key to edit. It is also Keycloak's own shape: exporting a realm
with users in separate files produces `<realm>-realm.json` alongside
`<realm>-users-N.json`, and importing a directory reads both.

**Verified against a running container**, which ADR-0007 left to
[#36](https://github.com/marcosfsousa/mcp-erp/issues/36):

```
Importing from directory /opt/keycloak/bin/../data/import
Realm 'mcp-erp-neighbour' imported
Imported users from /opt/keycloak/bin/../data/import/mcp-erp-users-0.json
Realm 'mcp-erp' imported
```

The fallback ADR-0007 named — splice the `users` array back into the realm file,
one line of rendering — is not needed and is not taken.

## Running it

```
docker compose up
```

The `Dockerfile` builds the image once with `--features=cimd --db=dev-mem`,
because the metadata-document feature is a **build-time** option and a boot that
paid for it would make every continuous-integration run pay too. The container
then runs `start --optimized --import-realm`. `compose.yaml` mounts this
directory over the copy baked into the image, from the same committed path, so
editing a realm file and restarting shows the change immediately.

Everything is discarded on `docker compose down`: the database is in memory, so
every boot re-imports from these files and mints **fresh signing keys**. That is
the point rather than a limitation — it makes *Keycloak is a pure function of
these files* provable, and turns key rotation into something the resource server
actually exercises.

## Reaching it

The issuer is `http://keycloak:8081/realms/mcp-erp`, and that one string has to
resolve identically on both sides of the container boundary, because ADR-0005
configures the resource server with the issuer and nothing else.

- **Inside the Compose network**, `keycloak` resolves by Compose's own DNS.
- **From the host**, add one line to your hosts file:

  ```
  127.0.0.1 keycloak
  ```

  ADR-0005 §Consequences priced that line and accepted it.

Host-side tooling that has not had the line added can be pointed somewhere
reachable instead — `KEYCLOAK_BASE_URL=http://localhost:8081` — which moves the
address the requests go to and never the issuer they assert.

## Minting a token

`tests/tokens.py` drives the real authorization code flow — direct access
grants are off on every client, so there is no shortcut — and prints what came
back:

```
uv run python tests/tokens.py priya.raman erp.read erp.write
uv run python tests/tokens.py tomas.weber erp.read --realm mcp-erp-neighbour
uv run python tests/tokens.py tomas.weber erp.read --client-id mcp-conformance-bare
```

The client defaults per realm, because the two realms share no clients. Pick one
explicitly to reach a specific refusal: `mcp-conformance-decoy` for a token
bound to somebody else's resource, `mcp-conformance-bare` for one with no
audience at all, `mcp-expiry-probe` for a ten-second lifespan.

The two most instructive runs are the role scope mapping doing its work:

```
$ uv run python tests/tokens.py rafael.costa erp.read erp.write erp.decide
granted     erp.read erp.write openid
declined    erp.decide

$ uv run python tests/tokens.py ingrid.holm erp.decide
granted     erp.decide openid
```

Rafael Costa holds `invoice_clerk` and neither deciding role, so the scope is
silently omitted and the flow succeeds — conformant, per RFC 6749 §3.3, and the
reason ADR-0012 left the `scope` response parameter as an open verification
item. Ingrid Holm holds `unlimited_approver` and **not** `approver`, and still
receives `erp.decide`: that is why the mapping lists both roles, and gating on
`approver` alone would have made the above-threshold branch she exists for
unreachable.

## The user import

Rendered from `docs/organisation/seed.yaml`: one entry per Person in the Cast,
seven in all. Each carries:

- **`id`** — the seed's chosen subject, imported verbatim. This is the `sub`
  claim the ERP rows and the principal directory join on, which is why it is
  authored rather than generated: a realm that minted its own identifiers would
  put that join at the mercy of a re-import.
- **`realmRoles`** — the seed's issuer-side column, carried through
  uninterpreted. These are **not** the roles the server resolves per request,
  and one person's two columns disagree on purpose. ADR-0007 explains why that
  divergence is load-bearing.
- **`credentials`** — one conspicuously fake password, shared by all seven,
  **non-temporary with no required actions**. Imported credentials are temporary
  by default, which triggers an update-password action on first login and hangs
  a headless flow on a form it does not expect.

To change any of it, edit the seed and re-render:

```
python -m mcp_erp.authorization.identity
```

The `Seed renders clean` job re-runs that and fails on any diff.

## The neighbour realm

`mcp-erp-neighbour` is a second issuer with its own signing keys and its own
real flow — which is what lets the attack suite reject a token that is *perfect
in every respect except who issued it*, rather than one we invented. Its client
carries **our** audience deliberately: bound to its own, the token would be
refused by the audience comparison and `foreign_issuer_token` would go red on
removal while proving nothing about `iss`.

**Its subject is a claim rather than a user id, and that was forced.** A
Keycloak user id is the primary key of `USER_ENTITY` **across the whole
database, not per realm**, so importing a neighbour user whose `id` is one of
the Cast's subjects fails the boot outright:

```
ERROR: Duplicate resource error
ERROR: Unique index or primary key violation: "PUBLIC.PRIMARY_KEY_B ON PUBLIC.USER_ENTITY(ID) VALUES ( 'tomas-weber' )"
```

So the neighbour's user takes a generated id nothing reads, and a hardcoded
claim mapper asserts the subject. The subject has to match a directory row or
the scenario passes for the wrong reason: skip the `iss` check with a *foreign*
subject and the call still fails, at the principal directory, on `role_missing`.
`tests/authorization/test_realm.py` holds both halves.

Unlike the Cast, this one user is **authored**, and the rule at the top of this
file is untouched by that: the split exists to keep generated content out of a
file a person edits, and there is nothing generated here to overwrite.

## What a hosted identity document costs the realm

*Added 2026-08-20 by [#46](https://github.com/marcosfsousa/mcp-erp/issues/46),
which built the conformance client and found all of this by running it.*

`--features=cimd` in the `Dockerfile` makes the discovery document advertise
`"client_id_metadata_document_supported": true`, and that is where the free part
ends. **The feature ships switched off in the realm.** An authorization request
naming the published document as its `client_id` answers *Client not found* —
`error="client_not_found"` in the event log — until the realm says which
identifiers it will dereference.

Keycloak implements the draft as a **client policy**, not as a realm switch, and
both halves are in `mcp-erp-realm.json`:

| | Provider id | What it does |
| --- | --- | --- |
| Profile executor | `client-id-metadata-document` | Fetches the document and provisions a client from it |
| Policy condition | `client-id-uri` | Decides which `client_id` URLs reach that executor |

Two settings in there are worth reading rather than copying:

- **`cimd-allow-http-scheme` is off**, and the loopback callback still works.
  The flag governs the client identifier and the URL-valued *metadata*
  properties — `client_uri`, `logo_uri`, `tos_uri`, `policy_uri`, `jwks_uri` —
  and `redirect_uris` is not among them. So the exhibit keeps the production
  setting and `public/README.md`'s *only the document must be HTTPS, never the
  redirect URI* survives contact with an implementation.
- **`cimd-allow-permitted-domains` has to name the callback's host as well as
  the document's.** The executor checks the client identifier *and* the redirect
  URI against that one list, so the publishing origin alone would refuse the
  document's own loopback callbacks. The policy's condition is narrower —
  `https` from `marcosfsousa.github.io` and nothing else — which is what decides
  whether a stranger's document is looked at in the first place.

**A provisioned client inherits the realm's defaults, and this realm had none.**
The four hand-authored clients each name their own `defaultClientScopes` and
`optionalClientScopes`, so nothing had ever needed realm-level ones — and a
client the executor creates gets exactly those. It arrived with no `basic` scope
(no `sub` claim), no `mcp-erp-audience` (no audience, so this server refuses the
token at gate 4) and none of the three capability scopes, which answers an
authorization request with `Invalid scopes: erp.read erp.write erp.decide`.

So the realm declares them:

```json
"defaultDefaultClientScopes": ["basic", "mcp-erp-audience"],
"defaultOptionalClientScopes": ["erp.read", "erp.write", "erp.decide"]
```

That is the same pair `mcp-conformance` names for itself, which is the point: the
client that earns its identity and the client that was handed one differ by how
they are known and by nothing else. It changes none of the four authored
clients — each states its own lists, and the decoy still carries somebody else's
audience — and the policy condition above is what keeps *any* client the realm
provisions to identifiers from one origin.

**`offline_access` is deliberately absent from that second list.** Keycloak
advertises the scope in `scopes_supported` in every realm, and SEP-2207 has a
client append it to the request when it declares `refresh_token`. No Person in
the Cast holds the `offline_access` role, and Keycloak does **not** narrow an
unentitled one away the way a role scope mapping narrows `erp.decide` — it
refuses the token request outright with *Offline tokens not allowed for the user
or client*. `tests/conformance_client.py`'s `GRANT_TYPES` carries the finding and
what the client does about it.

**A provisioned client inherits no PKCE pin either, and the pin could not be
attached to the policy above.** The four authored clients each carry
`"pkce.code.challenge.method": "S256"` as a client attribute, which is what makes
them refuse `plain`. A client the executor creates carries no attributes of its
own, so the fifth arrived accepting `plain` — and accepting a request with no
`code_challenge` at all — while ADR-0007 claimed the method was pinned at the
server for every client.

The obvious repair does not work, and the reason is worth stating because it
generalises to every executor. Adding `pkce-enforcer` to the
`client-identity-metadata-document` profile is inert: `ClientIdUriSchemeCondition`
votes on `PRE_AUTHORIZATION_REQUEST` and **abstains on every other event**, while
`PKCEEnforcerExecutor` does its work on `AUTHORIZATION_REQUEST` and
`TOKEN_REQUEST`. The two never meet, so the executor sits in the profile looking
like enforcement and enforcing nothing. **A profile is only as reachable as its
policy's condition, and conditions are per-event.**

So the pin is a second policy, bound to what is actually true of every client
here rather than to a name:

```json
{ "condition": "client-access-type", "configuration": { "type": ["public"] } }
```

`ClientAccessTypeCondition` votes on any context that carries a resolved client,
which covers both events `pkce-enforcer` handles. Every client in this realm is
public, so the pin now holds for the four in this file, for the fifth that is
not, and for any sixth — and `auto-configure` stamps `S256` onto the provisioned
client as well, so the attribute and the policy agree rather than one standing in
for the other.

## Two traps this directory pays for, beyond the three ADR-0007 banked

Both were found by a flow stopping on them, not by reading.

1. **`VERIFY_PROFILE` fires even with `requiredActions: []` on the user.** It
   comes from Keycloak's declarative user profile, which marks email, first name
   and last name required — and the Cast carries none of the three, because no
   field of a profile changes an authorization decision and ADR-0003 rejected
   `email` as a directory key on the record. Both realms therefore declare the
   action **disabled**. Without it the flow reaches
   `login-actions/required-action?execution=VERIFY_PROFILE` instead of a code.

2. **A `description` longer than 255 characters fails the import**, as a
   `Value too long for column "DESCRIPTION CHARACTER VARYING(255)"`. JSON has no
   comments, so the temptation is to explain a decision in the nearest
   `description` field. Prose belongs in this file; `description` gets a
   sentence.

## What the realm refuses, checked

Both verified against 26.7.1 through the running container:

```
$ curl -s -X POST .../token -d grant_type=password&client_id=mcp-conformance&...
{"error":"unauthorized_client","error_description":"Client not allowed for direct access grants"}

$ curl -s .../auth?...&code_challenge_method=plain
302 -> ...?error=invalid_request&error_description=Invalid+parameter%3A+code+challenge+method+is+not+matching+the+configured+one
```

The first is `password_grant_refused`, the second `pkce_downgrade_plain` — and
the second is per client, so the discovery document still advertises `plain`.
ADR-0007's caveat is binding: that row must assert the *refusal*, never the
metadata.

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

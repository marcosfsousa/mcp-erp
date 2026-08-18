# `keycloak/` — what the authorization server is imported from

Two kinds of file live here, and the difference is the whole point of the
directory:

| | Written by | Edited by hand |
| --- | --- | --- |
| `import/mcp-erp-users-0.json` | `python -m mcp_erp.authorization.identity` | never |
| the realm file beside it | a person | always |

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

The realm file itself, the Dockerfile that bakes this directory in, and the
Compose mount over it all arrive with
[#36](https://github.com/marcosfsousa/mcp-erp/issues/36), which is also where a
directory import is first executed against a running container.

## The user import

Rendered from `docs/organisation/seed.yaml`. Seven users, each carrying:

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

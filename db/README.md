# `db/` — the ERP's schema, and the loader for the seed's third rendering

Two files, run in name order by Postgres's own entrypoint on an empty data
directory:

| | What it is |
| --- | --- |
| `001-schema.sql` | The schema, transcribed from ADR-0003 |
| `002-load-organisation.sh` | Loads `src/mcp_erp/purchase_to_pay/data/organisation.json` |

`compose.yaml` mounts both, plus the rendering itself at `/seed/organisation.json`,
read-only.

## The schema is the policy function's argument list

Every column comes from ADR-0003's entity table and its four rules. Nothing here
is invented, and the absences are as decided as the columns:

- **No roles.** They are policy facts resolved server-side per request, so they
  live in the principal directory — the rendering beside this one. A column here
  would be a second place to hold them and a second place for them to be wrong.
- **No timestamps.** ADR-0003 handed *when things happened* to the audit-trail
  work with a blank page, and named the cost: list results have no defined order
  until somebody specifies one.
- **No editor.** There is no update tool among the five, so a requisition is
  immutable once submitted and no editor identity exists to reason about.

**Three of the six tables are empty at boot**, and that split is the honest one.
`cost_centre`, `vendor` and `person` are the authored organisation and are
loaded here. `requisition`, `purchase_order` and `invoice` hold the seed's
*other* half — per-row fixtures generated from
`docs/decision-matrix/matrix.yaml` since #43, committed as
`src/mcp_erp/purchase_to_pay/data/fixtures.json`, and loaded by
`tests/fixtures.py` rather than by this directory. ADR-0003 has the seeder wipe
and reload once before a run, which is a thing a suite does and not a thing a
boot does; a loader here would put rows in the database that no run had asked
for.

## Why the loader reads JSON rather than running SQL

The rendering is committed as JSON because that is what `Seed renders clean`
re-renders and refuses a diff on. Having the generator emit `INSERT` statements
instead would put a second dialect inside `src/` and make the drift check
compare SQL rather than data. The translation belongs next to the database that
needs it, which is here.

The loader passes the file's contents as a psql variable and unpacks it with
`jsonb_array_elements`, in one transaction: a half-loaded organisation would
boot and then fail on a join, which is a worse failure than not booting.

It prints its row counts when it finishes. A silent load and an empty database
look identical in a container log, and the first thing anybody wants to know
after a cold start is whether the seed arrived:

```
organisation loaded:
 cost_centres | people | vendors
--------------+--------+---------
            3 |      7 |       4
```

## Cold start every time

There is no volume. `docker compose down` discards the data directory, so the
next `up` re-runs both files — the same property Keycloak gets from an in-memory
database, and for the same reason: what the database holds is a function of what
is committed, not of what has happened to it since.

That also matches how the matrix uses it. ADR-0003 has the seeder wipe and
reload once before a full run rather than between rows, which is what keeps a
test-only reset route — *"the single most quotable finding a reviewer could hand
back"* — out of a server whose entire subject is authorization.

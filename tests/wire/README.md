# `tests/wire/` — the server's own posture, over the wire

The three assertions this slice makes that belong to no proof artifact: the
endpoints that answer and the ones that do not, the tool listing's filter and
its freshness hint, and two replicas behind no sticky routing.

Needs Compose. Landed with #37.

## Why there is a fifth directory

ADR-0013 named four test directories **for artifacts** — the decision matrix,
the attack suite, the conformance run, and the ejection target — and said that
layers 1 and 3 get none of their own, because ADR-0008 routes every assertion
about them over the wire. Both halves of that still hold, and neither of them
places these three.

- The **metadata route answering without a token, and every other path being
  gated**, is ADR-0006's discovery decision. It defends nothing named in
  `scenarios.yaml` and expects no `(principal × tool × resource)` row.
- **Two replicas, round-robin, nothing remembered** is map constraint `#5`. It
  is a property of the deployment rather than of a caller.
- The **tool listing's filter, `cacheScope` and `ttlMs`** will become four rows
  of `matrix.yaml` when #43 writes it. Until that file exists there is nothing
  to generate them from, and `tests/matrix/` is generated in its entirety.

The alternative was to mint scenario rows for the first two. That was declined:
membership in the attack suite is ADR-0010's rule — one row per distinct clause
this project *enforces*, each recording the exact removal that makes it pass —
and the row count is a derived artifact under map constraint `#12`. Inventing
two rows to give three tests a home would move a number three documents track,
to record something that is not an attack.

**This directory is named for the altitude every assertion in it shares, not for
a layer.** ADR-0013's prohibition is on a directory named `transport/` or
`purchase_to_pay/` collecting in-process unit tests of a layer; everything here
drives real HTTP against Compose like the three suites beside it. Recorded as an
amendment to ADR-0013 by #37.

## Running it

```
docker compose up -d
uv run pytest tests/wire
```

The token helper mints against the issuer the seed declares, which is
`http://keycloak:8081/...`. Either add one line to your hosts file —

```
127.0.0.1 keycloak
```

— or point the helper's transport somewhere reachable, which changes the address
the requests go to and never the issuer they assert:

```
KEYCLOAK_BASE_URL=http://localhost:8081 uv run pytest tests/wire
```

`MCP_ERP_BASE_URL` moves the server's address the same way; it defaults to the
gateway's published `http://localhost:8080`.

## Not yet in continuous integration

No job runs these. ADR-0013 fixes the job set at eight and hands the three
Compose jobs to the tickets that own their suites — *Decision matrix (wire)* to
#43, *Attack suite (wire)* to #44, *Authorization code flow* to #46 — and a
ninth job named for this ticket would be a job named for a ticket rather than
for a seam. #36 left Compose in the same position for the same reason. The
evidence for this slice is a recorded run, not a green tick, and the pull
request carries it.

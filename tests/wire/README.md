# `tests/wire/` — the server's own posture, over the wire

The assertions that belong to no proof artifact: the endpoints that answer and
the ones that do not, the tool listing's filter and its freshness hint, two
replicas behind no sticky routing, what `submit_requisition` charges, how the
named-versus-discovered contract behaves across the live tools, and — since #40 —
everything `approve_requisition` decides.

Needs Compose. Landed with #37; #39 added two, #40 a third.

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
- **What `submit_requisition` charges** (#39) is the same case one ticket later:
  a principal and a tool mapped to an expected answer is a matrix row, and there
  is still nothing to generate it from. It is not `state_handle_hijack` either —
  that row is a refused write against a *named* resource, and this tool has none.
- **Everything `approve_requisition` decides** (#40) is the same case again, and
  the largest of them: a threshold, a submitter edge, a terminal state and two
  denial classes, every one of which is a `(principal × tool × resource →
  expected)` row waiting for a file to be generated from. Two of its assertions
  are *not* matrix rows and would not become ones — that the rules run in the
  declared order, and that CC-4300's remedy names a class of action no available
  human fills. The first is a property of the `Action` rather than of a row; the
  second is a property of the organisation's shape, which is what makes it worth
  a named test rather than a matrix row that happens to expect `over_threshold`.
- **The named-versus-discovered contract across all three tools** (#39) is the
  seam between two attack-suite rows rather than a third one. Each of
  `row_probe_indistinguishable` and `list_partition_scoped` asserts its own half
  about its own tool; neither says the *same* row takes the *other* shape through
  the other tool. Minting a row for the seam would move a derived count to record
  something that is not an attack, which is the same refusal the two above take.

The alternative was to mint scenario rows for the ones that could carry them.
That was declined:
membership in the attack suite is ADR-0010's rule — one row per distinct clause
this project *enforces*, each recording the exact removal that makes it pass —
and the row count is a derived artifact under map constraint `#12`. Inventing
rows to give these tests a home would move a number three documents track, to
record something that is not an attack.

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

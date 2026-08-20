# `tests/wire/` — the server's own posture, over the wire

The assertions that belong to no proof artifact: the endpoints that answer and
the ones that do not, the tool listing's filter and its freshness hint, two
replicas behind no sticky routing, what `submit_requisition` charges, how the
named-versus-discovered contract behaves across the live tools, everything
`approve_requisition` decides since #40, the fold since #41, and — since #42 —
everything `record_invoice` records.

Needs Compose, with one exception named below. Landed with #37; #39 added two,
#40 a third, #41 a fourth, #42 a fifth.

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
- **The fold** (#41) is layer 1's, and layer 1 has no directory. What one call
  answers with when it yields more than one outcome is not a
  `(principal × tool × resource)` row — the same call, the same caller and the
  same rows produce it — and it defends nothing named in `scenarios.yaml`. Two
  of its assertions would not become matrix rows under any file: that a list
  tool returning several rows is still *one* outcome, which is a claim about
  what an outcome is rather than about who may see what; and the one below,
  which has no altitude at all.
- **Everything `record_invoice` records** (#42) is the same case once more, and
  the smallest of them: the second separation edge, a terminal state, and the
  role gate on a scope that reaches two tools — every one of which is a
  `(principal × tool × resource → expected)` row waiting for a file to be
  generated from. Two of its assertions are *not* matrix rows. That an approver
  who holds `invoice_clerk` is refused on the order she approved and permitted on
  the one she did not is a statement about a **position versus a role**, which
  needs both calls to say anything and would be two rows expecting two answers
  with the connection between them lost. And what the suite deliberately does
  **not** assert is `partition_bypass`: nobody in the cast holds `auditor`
  together with `invoice_clerk`, row scoping runs after the role gate, so a
  declaration that wrongly granted breadth on this write would ship green — which
  ADR-0013 names as the mistake a reader makes on this tool by name. Review is
  the guard, and the reasoning is in the declaration.
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
`purchase_to_pay/` collecting in-process unit tests of a layer; ~~everything
here drives real HTTP against Compose like the three suites beside it~~.
Recorded as an amendment to ADR-0013 by #37.

**One assertion here is not over HTTP, since #41.** *Layer 1 contains no
reference to the tool name, nor to which argument is the batch* is the negative
guarantee the fold had to be built without breaking, and it is not reachable at
this altitude: a name absent from a module is absent, and no request can show
it. So `test_the_fold.py` reads layer 1's own source, with docstrings stripped
first — the guarantee is *stated* in two of those modules, and a check that read
prose would fail on the sentence describing what it asserts. The precedent is
`tests/authorization/test_purity.py`, which reads layer 2's source for the same
class of reason: a property true by **absence** has no behaviour to drive. The
alternative was a sixth directory holding one file. Recorded as an amendment to
ADR-0013 by #41, which narrows the struck sentence above rather than keeping it.

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

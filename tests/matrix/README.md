# `tests/matrix/` — the decision matrix, over the wire

One row per `(principal × tool × resource → expected)`, driven from
[`docs/decision-matrix/matrix.yaml`](../../docs/decision-matrix/matrix.yaml).
Landed with #43.

**This directory is driven from the table in its entirety** — *driven*, not
*generated*, and the distinction is worth one sentence. ADR-0013 wrote that
`tests/matrix/` would be "generated in its entirety", meaning that no expectation
here would be hand-authored. That holds: every `test_rows_for_*.py` is a
parametrised loop over the rows the table declares for one tool, so adding a row
adds a test with nothing edited. What is *not* true is that a generator emits
these files — nothing writes them, they are not renderings, and calling them
generated would put them under a drift check that has nothing to compare against.
Parametrising is the better build and this paragraph is why the ADR's word
changed.

`pytest -v` prints each row's own identifier, so a red check names the
expectation that broke rather than a parameter index. `driver.py` is what a row
*means*: it builds the request the row's tool takes, mints a real token for the
row's principal through the real authorization code flow, and asserts the answer.
Nothing in `driver.py` decides what is expected, and nothing in the table decides
how an expectation is checked.

**Rows state a `reason` only.** Wire shape, remedy and both retry booleans are
derived from the `Reason` record the two layers declare — there is no lookup
table anywhere in `src/`, and the one this suite builds is built *out of* the two
declared sets rather than beside them. So changing ADR-0002's mapping is a change
in one declaration, not in thirty-three expectations.

## What lives here besides the rows

**`test_the_reason_mapping.py`** — ADR-0003's *exactly one dedicated test*,
enumerating the union of both layers' declared reasons and asserting the
reason-to-shape mapping. It lives here rather than in `tests/authorization/`
because layer 3's four reasons are in layer 3, so the test necessarily imports
the package the ejection command deletes. `tests/authorization/test_reasons.py`
gave up two assertions to it in the same commit — two places asserting a mapping
is two places for it to disagree with itself — and the cost is named there: the
ejected run no longer checks the shapes, because the shapes are not a layer-2
fact on their own.

**`test_the_matrix_holds_together.py`** — the table's own invariants. The `meta`
block is a standing index and every count in it is asserted against the rows; the
floor is that **every reason either layer declares is expected by at least one
row**, which is what makes the closed vocabulary reachable rather than merely
declared; the ceiling is soft at 45 and crossing it reviews the split rather than
adds a row. It also holds the fixtures to the seed: every fixture's cost centre
must be its submitter's own, because `submit_requisition` stamps the submitter's
and a row that broke that would be data no tool could have produced.

Nothing in that file needs Compose, so **`Seed renders clean` runs it too**,
beside the re-render it already refuses a diff on. The overlap is the one
ADR-0013 priced for `tests/authorization/test_identity.py`: a re-render plus diff
catches a hand-edited rendering, and a test catches a broken generator.

## No expected-response-mode column

ADR-0013 specified one; #37 dropped it when ADR-0002 cut the streamed mode. Every
POST is answered `application/json`, so the column's every value would be the
same — a field that changes no assertion, which is the governing rule's own test
for a field that has not earned its place. #43's ticket text predates the cut and
still lists it in its acceptance criteria; the column is not built, and this
paragraph is the reason.

## Where the fixtures come from

`mcp_erp.purchase_to_pay.fixtures` reads `matrix.yaml` and emits one requisition
per row that names a `given`, plus the purchase order and the invoice that row's
chain reaches. The rendering is committed at
`src/mcp_erp/purchase_to_pay/data/fixtures.json` and `Seed renders clean` refuses
any diff, so a hand-edited fixture is a red check.

The generator ships in `src/` — which is why the matrix definition cannot live
under `tests/` — and it is deleted with layer 3, because it speaks layer 3's
words. `tests/fixtures.py` is the other half: it reads that rendering and loads
it, and it is where the test-side database credential lives. ADR-0003 accepted
that credential in preference to a test-only reset route on a server whose entire
subject is authorization.

**Identifiers are ordinal and nothing keys on them.** Every suite in the
repository asks for a fixture by the matrix row that owns it, or by the partition
it sits in, so inserting a row renumbers the rendering and changes no assertion.
`mcp_erp/purchase_to_pay/fixtures.py` carries the argument for why they are not
name-shaped.

## Running it

```
docker compose up -d
uv run pytest tests/matrix
```

The token helper mints against the issuer the seed declares, which is
`http://keycloak:8081/...`. Either add one line to your hosts file —

```
127.0.0.1 keycloak
```

— or point the helper's transport somewhere reachable, which changes the address
the requests go to and never the issuer they assert:

```
KEYCLOAK_BASE_URL=http://localhost:8081 uv run pytest tests/matrix
```

`MCP_ERP_BASE_URL` moves the server's address the same way, and
`MCP_ERP_DATABASE_URL` the loader's.

## In continuous integration

**`Decision matrix (wire)`** runs this directory on every pull request and every
push to `main`. A red check means **an authorization expectation is wrong** — one
row got an answer the table does not declare. That is a different diagnosis from
`Server posture`, which is what the server says *identically to every caller*.

It is the second Compose bring-up in `.github/workflows/ci.yml` and repeats
`server-posture`'s pattern rather than sharing it. #66 declined to factor the
first one out against three imagined consumers; this is the second real one, so
factoring is now fair game and #44 is the third that would settle the shape.

**This job sits on a cut path, visibly.** Cut order `#9` ranks the decision
matrix third, and cutting it removes this job and `Seed renders clean` together —
and since #66 the tool listing's scope filter goes with them, because the five
assertions that filter is exercised through are rows here now.

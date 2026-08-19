# `tests/matrix/` — the decision matrix, over the wire

One row per `(principal × tool × resource → expected)`, driven from
`docs/decision-matrix/matrix.yaml`.

**No expected-response-mode column.** ADR-0013 specified one; #37 dropped it
when ADR-0002 cut the streamed mode. Every POST is answered `application/json`,
so the column's every value would be the same — a field that changes no
assertion, which is the governing rule's own test for a field that has not
earned its place. Dropped now because `matrix.yaml` does not exist yet; after
#43 it would have been a schema change plus regenerated fixtures.

Also holds the one union mapping test — ADR-0003's *exactly one dedicated test*
enumerating the union of both layers' declared reasons. It lives here rather
than in `tests/authorization/` because layer 3's four reasons are in layer 3, so
the test necessarily imports the package the ejection command deletes.

Needs Compose. Lands with #43.

# `tests/matrix/` — the decision matrix, over the wire

One row per `(principal × tool × resource → expected)`, driven from
`docs/decision-matrix/matrix.yaml`, plus each row's expected response mode.

Also holds the one union mapping test — ADR-0003's *exactly one dedicated test*
enumerating the union of both layers' declared reasons. It lives here rather
than in `tests/authorization/` because layer 3's four reasons are in layer 3, so
the test necessarily imports the package the ejection command deletes.

Needs Compose. Lands with #43.

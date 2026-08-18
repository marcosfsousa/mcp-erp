# `tests/attack_suite/` — named attacks, over the wire

33 rows, driven from `docs/attack-suite/scenarios.yaml`, 11 of them
`basis: adr` and 3 of them ADR-0009's `basis: seam`. `scenarios.yaml` is
canonical for named attacks; `matrix.yaml` is canonical for the decision matrix.
The two are disjoint and neither arbitrates the other.

Needs Compose. Lands with #44 (the seam assertions with #38).

# `tests/attack_suite/` — named attacks, over the wire

33 rows, driven from `docs/attack-suite/scenarios.yaml`, 11 of them
`basis: adr` and 3 of them ADR-0009's `basis: seam`. `scenarios.yaml` is
canonical for named attacks; `matrix.yaml` is canonical for the decision matrix.
The two are disjoint and neither arbitrates the other.

Needs Compose. The bulk lands with #44 (the seam assertions with #38).

**Three rows landed early, with #37**, because that slice is what made them
reachable and its acceptance criteria name them: `list_partition_scoped`,
`audience_missing` and `foreign_issuer_token`. Each declares its scenario by
name in the module docstring, which is what the bijection check will read.

`seeded_requisitions.py` is #37's too, and **#43 deletes it.** ADR-0003 has the
per-row requisitions generated from the decision matrix definition, one fixture
owned outright by one row; `matrix.yaml` does not exist yet, and set equality
against an empty table asserts nothing. What is there is the smallest set that
makes `list_partition_scoped` falsifiable — one cost centre with two rows and the
other two with one each, so that *the caller's own partition*, *another
partition* and *all three* are three different answers.

# `tests/purchase_to_pay/` — layer 3's loaders, held to what they promise

The counterpart to [`tests/authorization/`](../authorization/README.md), for the
half of the seed the domain owns. Landed with #81.

**One question, and it is not the domain's behaviour.** What the five tools
*decide* is [`tests/matrix/`](../matrix/README.md)'s, driven from
`docs/decision-matrix/matrix.yaml` over the wire. What this directory asks is
narrower and needs no Compose: given a document built to be rejected, does the
loader reject it, and does the message name the row that caused it.

**A falsifier per refusal.** #81 found eight checks whose docstrings named a
refusal the code did not make — a loader promising to fail loudly on a duplicate
and accepting one, a docstring listing two refusals where the code made two of a
possible five. A promise with no falsifier is how that happens: a `Raises:` list
is prose until something feeds it the input it names. So every refusal
`read_organisation` and `read_matrix` declare has a case here, and the rule that
bounds what they refuse at all is written into the module each one governs.

**Run by `Seed renders clean`**, beside the re-render that already refuses a
diff. The two controls cover different failures and neither implies the other: a
re-render catches a hand-edited rendering, and a test catches a loader that
stopped refusing while still rendering byte-identical output. ADR-0013 priced
that overlap for `tests/authorization/test_identity.py`; this is the same trade
for the layer that does not survive ejection.

**It is deleted with the domain.** `rm -rf src/mcp_erp/purchase_to_pay` takes the
loaders these tests are about, so this directory goes with them — which is why
none of it lives in `tests/authorization/`, and why `Layer 2 ejects clean` runs
that directory and not this one.

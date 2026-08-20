# `tests/attack_suite/` — named attacks, over the wire

34 rows, driven from `docs/attack-suite/scenarios.yaml`, 12 of them `basis: adr`
and 3 of them ADR-0009's `basis: seam`. `scenarios.yaml` is canonical for named
attacks; `matrix.yaml` is canonical for the decision matrix. The two are disjoint
and neither arbitrates the other.

Needs Compose. The job is **`Attack suite (wire)`**, and a red check there means
*a defence regressed*.

## The bijection is the report

Every test declares the row it falsifies, by name, one line above itself:

```python
@exercises("audience_confusion")
def test_audience_confusion() -> None:
```

`test_the_suite_holds_together.py` holds that in three directions at once — every
asserting row has a test, every declaration names a row, and every test in this
directory declares something. Break any one of them and a defence can be deleted
without a red check, which is the failure the report exists to make impossible.

The declarations are collected out of the **source**, with `ast`, rather than by
importing these modules: importing a test module from inside a test is a second
import under a second name, and the question is what is written rather than what
runs. `tests/authorization/test_purity.py` reads layer 2's source for a
comparable reason.

**One row is exempt, and the exemption is derived rather than written down.**
`threshold_split_evasion` carries `status: documented` and asserts nothing, so it
needs no test — the check reads that off the status, so a row that changed status
would stop being exempt without anyone remembering to say so. ADR-0010 refused
the alternative in the sentence that granted the exemption: *"the accepted-risk
row has no test, and would need a skipped one to hold its metadata. A skipped
test in a security suite is a bad thing to own."*

The same file asserts the standing index — `total`, `basis_split`,
`strength_split`, the floor of eleven and what each of those eleven holds up, the
soft ceiling of 35, and the twenty-row line below which the write-up has to
retitle the table from *attack suite* to *clause inventory, N proven*. None of it
needs Compose; it is collected here because a suite that skipped its own
invariants when run whole would be a suite with a hole in it.

## What lands where

| File | Rows |
| --- | --- |
| `test_token_validation.py` | the token gate, whole — one row per word in its closed refusal vocabulary, plus the two the neighbour realm serves |
| `test_token_in_query_string.py` | `token_in_query_string` |
| `test_the_envelope_and_its_headers.py` | gate 2 and the envelope rungs behind it, including `unsupported_protocol_version` |
| `test_auth_bypass_via_method_header_mismatch.py` | gate 3, which is a branch rather than a refusal |
| `test_the_scope_gate.py` | `insufficient_scope` and `scope_exact_match` |
| `test_dns_rebinding_origin.py` | gate 1 |
| `test_get_stream_removed.py` | the modern leg's `405` |
| `test_retry_after_denial.py` | the three rows about what a client does with a refusal |
| `test_the_realm_refuses.py` | the three rows the authorization server keeps |
| `test_mixup_iss_mismatch.py` | the suite's only client-side row |
| `test_row_probe_indistinguishable.py`, `test_state_handle_hijack.py`, `test_list_partition_scoped.py`, `test_double_approval_via_batch_retry.py` | the four rows that landed with the tools that made them reachable |
| `test_legacy_era_seam.py` | ADR-0009's three seam assertions |

## What landed before this suite was whole

**The three `basis: seam` rows landed with #38**, in `test_legacy_era_seam.py`,
which ran on its own rather than inside #44 because their result was a design
input. It came back green: ADR-0009's *The first run, and what it settled*
records what they settled and what it cost, and is the one place that argument
lives.

They keep their place in the floor of 11 for a different reason than they were
written for. The legacy leg is always on and nothing else here touches it, so a
regression on it would be invisible everywhere else in the suite.

**Three rows landed early, with #37**, because that slice is what made them
reachable and its acceptance criteria name them: `list_partition_scoped`,
`audience_missing` and `foreign_issuer_token`.

`seeded_requisitions.py` was #37's too, and **#43 deleted it**, as its own
docstring said it would. `tests/fixtures.py` is what replaced it, and the
difference is the author: the rows are generated from
`docs/decision-matrix/matrix.yaml` now — one fixture owned outright by one matrix
row, which is what ADR-0003 specified before either half existed — and committed
as a rendering `Seed renders clean` refuses a diff on. This directory reads them
and asserts nothing about the table they came from: `matrix.yaml` and
`scenarios.yaml` share no rows, and two suites consuming one seed is data in
common rather than a row in common.

**Nothing here names a fixture by identifier**, and that is what makes the shared
seed safe. The identifiers are ordinals the generator renumbers when a matrix row
is inserted, so every scenario asks for a row by the **property** it needs — a
partition it cannot see, a row still decidable below the threshold — and a
renumbered rendering changes no assertion here. The rows this suite raises for
itself, through `requisitions.raised_by`, are named by nothing at all.

**One row landed early with #39**, `row_probe_indistinguishable`, and **its pair
with #40**, `state_handle_hijack` — the read and write halves of one clause,
split because their removals are different deletions. **And a fourth with #41**,
`double_approval_via_batch_retry`, which could not have landed sooner: the
failure it forbids is *a batch* re-deciding the items it had already done, and
until that ticket `approve_requisition` took one identifier. Each was
`status: asserted` with nothing asserting it, so no count moved when the
assertion arrived.

That state — a row claiming an assertion that does not exist — is exactly what
the bijection now refuses, and #44 closed the last two instances of it:
`get_stream_removed`, whose citation also described a `405` the gate chain
answers `401` to, and `unsupported_protocol_version`, which was held outside the
table until #38 met its condition by hand.

`double_approval_via_batch_retry`'s assertion still reaches past the wire, alone
in this directory. A refused item answers with a reason and no purchase order, so
a response cannot distinguish *no second order* from *a second order that was not
shown*, and there is no tool that lists one — ADR-0002 cut every read tool that
demonstrated no authorization behaviour. So *minted nothing* is counted in the
database, through `tests/fixtures.py`, which is where a test-side credential
already lives.

## Running it

```
docker compose up --wait
uv run pytest tests/attack_suite -v
```

Outside the Compose network the token helper needs `keycloak` to resolve — one
`127.0.0.1 keycloak` line in the host's hosts file, which is the documented path
and the one continuous integration takes, or `KEYCLOAK_BASE_URL=http://localhost:8081`
as the fallback ADR-0005 priced.

Two rows are slower than the rest and both are deliberate: `token_expired` waits
out a real ten-second token rather than a fake clock, and every row mints through
a real authorization code flow.

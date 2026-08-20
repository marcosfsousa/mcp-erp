# `tests/attack_suite/` — named attacks, over the wire

33 rows, driven from `docs/attack-suite/scenarios.yaml`, 11 of them
`basis: adr` and 3 of them ADR-0009's `basis: seam`. `scenarios.yaml` is
canonical for named attacks; `matrix.yaml` is canonical for the decision matrix.
The two are disjoint and neither arbitrates the other.

Needs Compose. The bulk lands with #44.

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
`audience_missing` and `foreign_issuer_token`. Each declares its scenario by
name in the module docstring, which is what the bijection check will read.

`seeded_requisitions.py` is #37's too, and **#43 deletes it.** It shipped in
this directory and moved up to `tests/` with #39, when the wire suites became a
second caller — the rule `tokens.py` states, applied: shared tooling that lives
in one artifact's directory becomes that artifact's and gets copied by the next.
ADR-0003 has the
per-row requisitions generated from the decision matrix definition, one fixture
owned outright by one row; `matrix.yaml` does not exist yet, and set equality
against an empty table asserts nothing. What is there is the smallest set that
makes `list_partition_scoped` falsifiable — one cost centre with two rows and the
other two with one each, so that *the caller's own partition*, *another
partition* and *all three* are three different answers. The same four rows serve
`row_probe_indistinguishable` unchanged.

**One row landed early with #39**, `row_probe_indistinguishable`, in
`test_row_probe_indistinguishable.py`. That ticket built `get_requisition`, which
is what made a named resource reachable at all, and its acceptance criteria name
the assertion — byte-identical `not_found` for a foreign row and a row that never
existed. The row was already in `scenarios.yaml` with `status: asserted` and
nothing asserting it, so no count moved.

**And its pair landed with #40**, `state_handle_hijack`, in
`test_state_handle_hijack.py`. It is the write half of the same clause and #39
handed it here by name — *"the scenario this is not is `state_handle_hijack`:
that row is a refused write against a named resource, and this tool has no
resource at all. Its falsifier arrives with the first write that takes one."*
`approve_requisition` is that write. The row was `status: asserted` with nothing
asserting it, so again no count moved; what did move is its `removal`, which was
written at #9 and named what ADR-0013 later made the design. The correction is
recorded in the row's own `note`.

**And a fourth landed early with #41**, `double_approval_via_batch_retry`, in
`test_double_approval_via_batch_retry.py`. It could not have landed sooner: the
failure it forbids is *a batch* answering for the items it managed and
re-deciding the ones it had already done, and until that ticket
`approve_requisition` took one identifier. #40 shipped the terminal state the row
rests on and the batch is what makes retrying a whole call a thing a client can
do. `status: asserted` with nothing asserting it again, so no count moved and
neither the row nor its `removal` needed a word changed.

Its assertion reaches past the wire, alone in this directory. A refused item
answers with a reason and no purchase order, so a response cannot distinguish
*no second order* from *a second order that was not shown*, and there is no tool
that lists one — ADR-0002 cut every read tool that demonstrated no authorization
behaviour. So *minted nothing* is counted in the database, through
`seeded_requisitions.py`, which is where a test-side credential already lives.

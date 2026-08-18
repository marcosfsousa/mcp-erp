# `tests/authorization/` — in-process, layer 2 only, no Docker

The ejection target. **The ejection test is a command, not a file:**

```
rm -rf src/mcp_erp/purchase_to_pay && pytest tests/authorization
```

so nothing in here may import layer 3. These are the unit tests of the policy
function: the ordered chain, the three entry points, the reason records, the
directory miss. Docker is not running when they pass.

Landed with #34. The stand-in declarations these run against are in
`declarations.py`, deliberately in a vocabulary this exhibit does not model —
a declaration naming a requisition would reintroduce layer 3's words into the
layer that has to survive without them. They are declarations rather than
fixtures: a fixture is generated from a matrix row and owned by it, and every
constant there is hand-written.

#35 added two files that read real data, and the reason they belong here is the
same reason the identity generator is layer 2's: **identity provisioning
survives ejection** (ADR-0004, criterion 4), so the tests that hold it have to
run with the domain deleted. Both do — the seed and the two renderings they read
are outside `purchase_to_pay/`.

- `test_identity.py` — the generator's invariants: byte-stability, the two role
  columns staying independent, and realm subject set equal to directory subject
  set with the divergence declared on the role columns only. `Seed renders
  clean` runs this file as well, for a different question; the workflow says
  which.
- `test_shipped_directory.py` — the wiring: `lookup` answering from the
  committed rendering, held immutable in memory, with no database and nothing
  to bring up.

Neither hardcodes the cast. They assert against the seed's own rows, and the one
literal from the organisation that appears at all is the subject declared as the
role-column exception — because an exception a test does not name is not an
exception, it is an absence of checking.

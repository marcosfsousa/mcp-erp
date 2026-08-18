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

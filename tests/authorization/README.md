# `tests/authorization/` — in-process, layer 2 only, no Docker

The ejection target. **The ejection test is a command, not a file:**

```
rm -rf src/mcp_erp/purchase_to_pay && pytest tests/authorization
```

so nothing in here may import layer 3. These are the unit tests of the policy
function: the ordered chain, the three entry points, the reason records, the
directory miss. Docker is not running when they pass.

Lands with #34.

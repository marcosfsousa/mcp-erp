"""mcp-erp — an MCP server exposing a mock ERP, with OAuth 2.0 as a first-class concern.

Three sibling packages and a composition root, per ADR-0013:

    transport/        layer 1 — transport and protocol conformance
    authorization/    layer 2 — the portable authorization pattern
    purchase_to_pay/  layer 3 — the ejectable domain
    app.py            the only module importing all three

Only declarations cross a layer boundary. Layer 3 declares an ``Action`` per tool
and its own reason values; layer 2 decides; layer 1 renders what comes back
without learning what produced it.

``.importlinter`` is the checked statement of the shape and the place to read it.
The docstrings below name only what their own layer may not import, so that a
change to the layering edits the contract file rather than four copies of it.
"""

"""Layer 1 — transport and protocol conformance.

Holds the ASGI application, the gate middleware, and the adapters that render a
layer-2 outcome onto the wire. Layer 1 learns the *shape* of a refusal —
``denial_class`` and cardinality — never its grounds: not which rule fired,
against which attribute, on which row.

Imports nothing from :mod:`mcp_erp.purchase_to_pay`. The composition root
registers handlers with this package; the two never reference each other.
"""

"""Layer 3 — the purchase-to-pay domain, ejectable.

Cloning this repository for another purpose means *deleting* this package, not
untangling it. Ejection is one ``rm -rf`` plus editing :mod:`mcp_erp.app`.

Declares exactly one ``Action`` per tool and its own four reason values, and
holds the handlers — the largest thing ejection deletes. Handlers return a
domain outcome or a refused ``Decision``, never anything protocol-shaped.

Imports nothing from :mod:`mcp_erp.transport`.
"""

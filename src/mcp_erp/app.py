"""The composition root — the only module importing all three layers.

Nothing here yet but the imports that make the shape real. Wiring arrives with
the layers it wires: the ASGI application and its gate middleware, the principal
directory, and the handler registration that lets layers 1 and 3 cooperate
without referencing each other.

This module sits at the package root rather than inside a sub-package so that
neither ``.importlinter`` contract needs an exception clause for it — it is out
of scope by construction rather than by a carve-out someone has to justify.

Ejecting layer 3 means deleting :mod:`mcp_erp.purchase_to_pay` and editing this
file. That is the whole procedure.
"""

from mcp_erp import authorization, purchase_to_pay, transport

# Load-bearing rather than decorative: these three imports exist to make the
# composition root's reach real, and nothing calls them yet. Without `__all__`
# marking them as re-exports the lint job flags all three as unused, and the
# obvious fix — deleting them — is the one that empties this module of meaning.
__all__ = ["authorization", "purchase_to_pay", "transport"]

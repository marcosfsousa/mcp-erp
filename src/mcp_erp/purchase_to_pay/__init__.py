"""Layer 3 — the purchase-to-pay domain, ejectable.

Cloning this repository for another purpose means *deleting* this package, not
untangling it. Ejection is one ``rm -rf`` plus editing :mod:`mcp_erp.app`.

Declares exactly one ``Action`` per tool and its own four reason values, and
holds the handlers — the largest thing ejection deletes. Handlers return a
domain outcome or a refused ``Decision``, never anything protocol-shaped.

Imports nothing from :mod:`mcp_erp.transport`.

What the composition root needs is re-exported here. The tool declarations —
name, schemas, description — are re-exported as a module rather than flattened,
because a second tool would otherwise turn every name into a prefixed one.

:mod:`~mcp_erp.purchase_to_pay.organisation` is **deliberately absent** below.
It is a generator with a ``__main__`` entry point, and importing it here would
put it in ``sys.modules`` before ``python -m`` executes it — which Python warns
about and which can run a module's top level twice. Layer 2 keeps its own
generator out of its ``__all__`` for the same reason.
"""

from mcp_erp.purchase_to_pay import handlers, requisition
from mcp_erp.purchase_to_pay.repository import PostgresRequisitions, Requisitions
from mcp_erp.purchase_to_pay.requisition import LIST_REQUISITIONS, Requisition

__all__ = [
    "LIST_REQUISITIONS",
    "PostgresRequisitions",
    "Requisition",
    "Requisitions",
    "handlers",
    "requisition",
]

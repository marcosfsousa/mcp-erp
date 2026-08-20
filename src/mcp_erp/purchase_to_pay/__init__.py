"""Layer 3 — the purchase-to-pay domain, ejectable.

Cloning this repository for another purpose means *deleting* this package, not
untangling it. Ejection is one ``rm -rf`` plus editing :mod:`mcp_erp.app`.

Declares exactly one ``Action`` per tool and its own reason values, and
holds the handlers — the largest thing ejection deletes. Handlers return a
domain outcome or a refused ``Decision``, never anything protocol-shaped.

Imports nothing from :mod:`mcp_erp.transport`.

What the composition root needs is re-exported here. The tool declarations —
name, schemas, description — are re-exported **as modules rather than
flattened**, one module per tool, because three tools declaring five
module-level names each would otherwise turn every one of them into a prefixed
name. Each module's ``Action`` is called ``ACTION``, so the tool's identity is
the module's and never repeated inside it.

:mod:`~mcp_erp.purchase_to_pay.organisation` is **deliberately absent** below.
It is a generator with a ``__main__`` entry point, and importing it here would
put it in ``sys.modules`` before ``python -m`` executes it — which Python warns
about and which can run a module's top level twice. Layer 2 keeps its own
generator out of its ``__all__`` for the same reason.
:mod:`~mcp_erp.purchase_to_pay.vendors` reads what that generator writes and has
no entry point, so it is re-exported normally.
"""

from mcp_erp.purchase_to_pay import (
    approve_requisition,
    get_requisition,
    handlers,
    invoice,
    list_requisitions,
    purchase_order,
    reasons,
    record_invoice,
    requisition,
    submit_requisition,
    vendors,
)
from mcp_erp.purchase_to_pay.invoice import Invoice
from mcp_erp.purchase_to_pay.purchase_order import PurchaseOrder
from mcp_erp.purchase_to_pay.repository import (
    PostgresPurchaseOrders,
    PostgresRequisitions,
    PurchaseOrders,
    Requisitions,
)
from mcp_erp.purchase_to_pay.requisition import Requisition

__all__ = [
    "Invoice",
    "PostgresPurchaseOrders",
    "PostgresRequisitions",
    "PurchaseOrder",
    "PurchaseOrders",
    "Requisition",
    "Requisitions",
    "approve_requisition",
    "get_requisition",
    "handlers",
    "invoice",
    "list_requisitions",
    "purchase_order",
    "reasons",
    "record_invoice",
    "requisition",
    "submit_requisition",
    "vendors",
]

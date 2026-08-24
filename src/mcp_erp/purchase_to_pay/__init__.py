"""Layer 3 — the purchase-to-pay domain, ejectable.

Cloning this repository for another purpose means *deleting* this package, not
untangling it. Ejection is one ``rm -rf`` plus editing :mod:`mcp_erp.app`.

Declares exactly one ``Action`` per tool and its own reason values, and
holds the handlers — the largest thing ejection deletes. Handlers return a
domain outcome or a refused ``Decision``, never anything protocol-shaped.

Imports nothing from :mod:`mcp_erp.transport`.

What the composition root needs is re-exported here. The tool declarations —
name, schemas, description — are re-exported **as modules rather than
flattened**, one module per tool, because every tool declares the same five
module-level names, and flattening them into one namespace would turn every one
of them into a prefixed name. Each module's ``Action`` is called ``ACTION``, so
the tool's identity is the module's and never repeated inside it.

:mod:`~mcp_erp.purchase_to_pay.organisation` is **deliberately absent** below.
It is a generator with a ``__main__`` entry point, and importing it here would
put it in ``sys.modules`` before ``python -m`` executes it — which Python warns
about and which can run a module's top level twice. Layer 2 keeps its own
generator out of its ``__all__`` for the same reason.
:mod:`~mcp_erp.purchase_to_pay.vendors` reads what that generator writes and has
no entry point, so it is re-exported normally.

**Every schema in this package carries ``additionalProperties: false``**, and
this is where the reason is written down. The convention holds across the tool
declarations and the entity schemas alike, and it is asserted by four suites
under ``tests/wire/`` — an argument recorded once beside one of those assertions
would be a claim in a place nobody edits this package from (#112).

The reason is *disclosure*, not validation. ``submit_requisition`` is the sharp
case: a requisition is written to the submitter's own cost centre, taken from
``principal.partition``, and there is no property to send. A free-text one would
leak which centres exist — the probing surface ADR-0002 designed out — and an
enumerated one would publish the organisation's shape in a document
``tools/list`` hands to anyone holding the scope. Saying ``false`` is how the
declaration tells a model reading it that the omission is deliberate rather than
an oversight it should work around.

**It is not an enforcement point, and must never be read as one.** Nothing on
this stack validates arguments against a published ``inputSchema``: an argument
list is what ADR-0003 makes the policy function's, and a caller sending a
forbidden key is refused by nothing. What closes that hole is the handler — it
never reads the key, and the write takes ``principal.partition`` regardless. So
each declaration states the shape and the handler holds it, and neither one is
the whole claim by itself.
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

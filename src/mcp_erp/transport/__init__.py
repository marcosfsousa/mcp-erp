"""Layer 1 — transport and protocol conformance.

Holds the ASGI application's parts, the gate middleware, and the adapters that
render a layer-2 outcome onto the wire. Layer 1 learns the *shape* of a refusal —
``denial_class`` and cardinality — never its grounds: not which rule fired,
against which attribute, on which row.

Imports nothing from :mod:`mcp_erp.purchase_to_pay`. The composition root
registers handlers with this package; the two never reference each other.

Everything the composition root needs is re-exported here, so the seam is one
import line and ``__all__`` below is the whole of what crosses it.
"""

from mcp_erp.transport import dispatch, metadata, refusals
from mcp_erp.transport.configuration import Configuration, from_environment
from mcp_erp.transport.gates import OriginGate, ScopeGate, ShapeGate, TokenGate
from mcp_erp.transport.keys import KeySet
from mcp_erp.transport.registry import Handler, Outcome, Registry, ToolRegistration
from mcp_erp.transport.tokens import ValidatedToken

__all__ = [
    "Configuration",
    "Handler",
    "KeySet",
    "OriginGate",
    "Outcome",
    "Registry",
    "ScopeGate",
    "ShapeGate",
    "TokenGate",
    "ToolRegistration",
    "ValidatedToken",
    "dispatch",
    "from_environment",
    "metadata",
    "refusals",
]

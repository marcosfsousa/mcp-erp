"""Layer 2 — the authorization pattern, portable and standing alone.

The ejection target. Deleting :mod:`mcp_erp.purchase_to_pay` leaves this package
building and ``tests/authorization`` passing, with only its extension points
unfilled (map constraint ``#10``).

Owns the principal directory, the frozen ``Claims``/``Principal`` stages, the
``Action`` seam, the ``Rule`` and ``Resource`` protocols, the ``Reason`` record
with its closed ``Remedy`` and ``DenialClass`` vocabularies, and the one ordered
policy chain behind three entry points.

Imports nothing from layers 1 or 3 — enforced by the *Layer 2 knows nothing
above it* contract over the whole static import graph, and by the ejection job
over what those tests actually run.

Everything layers 1 and 3 need is re-exported here, so the seam is one import
line and a reader can see the whole of what crosses it in ``__all__`` below.
"""

from mcp_erp.authorization.action import Action, Capability, Resource, Rule
from mcp_erp.authorization.directory import (
    DIRECTORY_MISS,
    DirectoryEntry,
    PrincipalDirectory,
    shipped_directory,
)
from mcp_erp.authorization.policy import (
    Decision,
    GateOutcome,
    decide_call,
    decide_item,
    permits_scope,
)
from mcp_erp.authorization.principal import Claims, Principal
from mcp_erp.authorization.reasons import (
    INSUFFICIENT_SCOPE,
    NOT_FOUND,
    REASONS,
    ROLE_MISSING,
    DenialClass,
    Reason,
    Remedy,
)

__all__ = [
    "DIRECTORY_MISS",
    "INSUFFICIENT_SCOPE",
    "NOT_FOUND",
    "REASONS",
    "ROLE_MISSING",
    "Action",
    "Capability",
    "Claims",
    "Decision",
    "DenialClass",
    "DirectoryEntry",
    "GateOutcome",
    "Principal",
    "PrincipalDirectory",
    "Reason",
    "Remedy",
    "Resource",
    "Rule",
    "decide_call",
    "decide_item",
    "permits_scope",
    "shipped_directory",
]

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
"""

# ── Deliberate contract violation. Reverted by the very next commit. ──────────
#
# Issue #33 asks that an import from `authorization` into `purchase_to_pay`
# fails `Layer boundaries`, demonstrated once. This is that import. Layer 2 is
# the ejection target, so reaching into layer 3 is the failure the contract
# exists to catch: after `rm -rf src/mcp_erp/purchase_to_pay` this module would
# not import at all.
#
# Expected on this commit: `Layer boundaries` red naming the crossed boundary,
# `Lint and types` green. The check names the layer without anyone opening logs,
# which is the property being demonstrated — not merely that something failed.
from mcp_erp import purchase_to_pay

__all__ = ["purchase_to_pay"]

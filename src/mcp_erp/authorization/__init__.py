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

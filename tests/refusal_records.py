"""The refusal body a `Reason` declares, derived here rather than rendered by layer 1.

Every suite that asserts a structured refusal needs the same four fields, and
before #87 two of them wrote those fields out as literals instead — which made a
change to ADR-0002's mapping a sweep rather than an edit, and made a defence
whose expectation had gone stale look exactly like one that still held.

**Not `mcp_erp.transport.refusals.refusal_payload`, deliberately.** That function
is the code under test. A suite calling it asserts that layer 1 agrees with
itself and would pass with the renderer dropping a key, promoting a `Remedy`
member in place of its value, or reading the wrong field off the record; what
belongs in a suite is the *independent* derivation, so that the two can disagree.
`tests/matrix/driver.py` made that argument first and this module is where it
now lives, because the argument was never specific to the matrix.

**One function, and no lookup table.** The reasons themselves are declared in the
two layers and imported by name — ADR-0013's *"nothing can name a reason without
also stating what it does to a client"* is what makes this a projection of a
record rather than a fifth place the vocabulary is written down.
"""

from typing import Any

from mcp_erp.authorization import Reason


def refusal_body(reason: Reason) -> dict[str, Any]:
    """The four fields a structured refusal carries, read off the record.

    The shape layer 1 puts in a tool result's `structuredContent` and in a
    JSON-RPC error's `data` — the two renderings ADR-0002 gives a body at all.
    A `CHALLENGE` reason has no body and never reaches this: its remedy and both
    retry booleans stay in the record, and what the caller gets is a header.

    Args:
        reason: The record the refusal names.

    Returns:
        The body, keyed as the wire keys it.
    """
    return {
        "reason": reason.value,
        "remedy": reason.remedy.value,
        "retry_identical_helps": reason.retry_identical_helps,
        "retry_as_other_person_helps": reason.retry_as_other_person_helps,
    }

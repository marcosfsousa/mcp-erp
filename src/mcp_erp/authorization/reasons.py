"""The closed refusal vocabularies, and layer 2's own three reasons.

A reason is a **record, not a string** (ADR-0013). Every instance states its own
wire shape, its own remedy and both retry booleans at the point of declaration,
so **there is no lookup table anywhere** — nothing can name a reason without
also stating what it does to a client. ADR-0002 derived that mapping; here the
derivation is a construction invariant.

Each layer declares its own instances. Layer 2 declares the three below; layer 3
declares its four in :mod:`mcp_erp.purchase_to_pay`, using this same record.
``Remedy``, ``DenialClass`` and both retry booleans stay wholly here — they
describe client behaviour, not domain facts (ADR-0004, coupling 1).
"""

from dataclasses import dataclass
from enum import StrEnum


class DenialClass(StrEnum):
    """One of the three shapes a refusal takes on the wire.

    Chosen by what would fix it for the caller, never by which rule fired. Layer
    1 renders on this member alone — it learns the *shape* of a refusal and
    never its grounds (ADR-0013). The wire renderings named in the member
    docstrings belong to layer 1 and are recorded here only so that a reader can
    follow ADR-0002's table.
    """

    CHALLENGE = "challenge"
    """A ``403`` carrying a ``WWW-Authenticate`` challenge. The caller re-authorizes."""

    PROTOCOL_ERROR = "protocol_error"
    """A JSON-RPC error. Not model-fixable, so it must not ride in a tool result."""

    TOOL_RESULT = "tool_result"
    """A tool result marked in error. Actionable feedback a model can self-correct on."""


class Remedy(StrEnum):
    """What would resolve a refusal, expressed as a class of action.

    Never a named human, and never a promise that such a person exists: ADR-0003
    lands one decision-matrix row on a cost centre where nobody holds the role,
    precisely so that the distinction is tested rather than described.
    """

    REAUTHORIZE = "reauthorize"
    ADMINISTRATOR_GRANT = "administrator_grant"
    DIFFERENT_PERSON = "different_person"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class Reason:
    """Why a refusal happened, together with everything a client needs to act on it.

    ``retry_as_other_person_helps`` is the field that earns the vocabulary
    (ADR-0002): "do not retry" is right for two of the three refusals here and
    wrong for segregation of duties, where retrying as a different person is the
    correct move. A single boolean would flatten the one case the domain exists
    to demonstrate.
    """

    value: str
    denial_class: DenialClass
    remedy: Remedy
    retry_identical_helps: bool
    retry_as_other_person_helps: bool


INSUFFICIENT_SCOPE = Reason(
    value="insufficient_scope",
    denial_class=DenialClass.CHALLENGE,
    remedy=Remedy.REAUTHORIZE,
    retry_identical_helps=False,
    retry_as_other_person_helps=False,
)
"""The token does not carry the action's scope.

Another person's token is narrowed by a ceiling of its own, so retrying as one
of them is not the remedy; acquiring the scope is.
"""

ROLE_MISSING = Reason(
    value="role_missing",
    denial_class=DenialClass.PROTOCOL_ERROR,
    remedy=Remedy.ADMINISTRATOR_GRANT,
    retry_identical_helps=False,
    retry_as_other_person_helps=False,
)
"""The token carries the scope; the principal holds no role the action requires.

A ``403`` here would be a lie — it would instruct the client to acquire a scope
it already holds, producing an identical token and an identical refusal. This
reason is also what a directory miss refuses with; see
:data:`mcp_erp.authorization.directory.DIRECTORY_MISS`.
"""

NOT_FOUND = Reason(
    value="not_found",
    denial_class=DenialClass.TOOL_RESULT,
    remedy=Remedy.NONE,
    retry_identical_helps=False,
    retry_as_other_person_helps=False,
)
"""A named row the principal may not see, or no such row at all.

One reason for both, reached through a single return site in
:mod:`mcp_erp.authorization.policy`. Both retry booleans are false, and
``retry_as_other_person_helps`` is the load-bearing one: true would confirm the
row exists and that somebody else can see it, which is the existence oracle
ADR-0002 declined to ship.
"""

REASONS: frozenset[Reason] = frozenset({INSUFFICIENT_SCOPE, ROLE_MISSING, NOT_FOUND})
"""Layer 2's declared set, in full.

ADR-0003's one dedicated mapping test enumerates the union of this and layer 3's
four. Because layer 3's live in layer 3, that test imports the package the
ejection command deletes, and so belongs in ``tests/matrix/`` rather than here —
``tests/matrix/test_the_reason_mapping.py``, written by #43, which also took the
two assertions in ``tests/authorization/test_reasons.py`` that had been asserting
the same mapping over three of the seven.
"""

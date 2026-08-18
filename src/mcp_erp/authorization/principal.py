"""The two identity stages: what a token asserts, and what the server stands behind.

``Claims`` and ``Principal`` are **not two halves of one thing**. They are two
stages — the unverified caller the token asserts, and the resolved principal the
server stands behind once the directory has answered. That distinction is this
exhibit's subject, so making it a type boundary is legible rather than
incidental (ADR-0013).

Both arrive frozen and complete. The policy chain takes no collaborators, so
there is nothing for it to resolve lazily and nowhere for a half-built principal
to acquire the rest of itself.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Claims:
    """The caller a validated access token asserts, before the server has resolved them.

    Every field here is token-derived, which is what makes this type the exact
    input the directory needs and the exact set of fields
    :func:`mcp_erp.authorization.policy.permits_scope` is allowed to read.
    """

    issuer: str
    subject: str
    granted_scopes: frozenset[str]


@dataclass(frozen=True, slots=True)
class Principal:
    """The resolved caller: a person's standing authority, under one token's ceiling.

    The two halves vary independently — the same person is a different principal
    under a narrower token — which is why ``granted_scopes`` (token-derived) and
    ``roles`` / ``partition`` (directory-derived) sit in one record without being
    the same kind of fact.

    ``partition`` is **non-optional, deliberately**. The tempting design — a
    directory miss yielding a principal with no roles, refused at the role step
    — fails open, because submitting is gated by scope alone and ``erp.write``
    is deliberately ungated: an unknown subject holding it would clear the scope
    gate, clear a role gate demanding nothing, and write a row charged to a null
    partition. A non-optional partition makes a miss structurally unable to
    produce a principal at all (ADR-0006, ADR-0013).
    """

    issuer: str
    subject: str
    granted_scopes: frozenset[str]
    roles: frozenset[str]
    partition: str

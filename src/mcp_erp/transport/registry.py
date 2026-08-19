"""What the composition root hands layer 1, and the only thing layer 1 knows about a tool.

Layer 1 imports nothing from layer 3 and layer 3 imports nothing from layer 1.
The composition root is what pairs them, and this module is the shape it pairs
them into: a name, the schemas the domain wrote, the ``Action`` the domain
declared, and one callable.

**A registration is not a domain object.** The schemas arrive as plain JSON
Schema documents and the handler yields plain mappings, so nothing layer 3 owns
is protocol-shaped and nothing layer 1 owns is domain-shaped. The one type
crossing in either direction is layer 2's ``Action``, which both may import.
"""

from collections.abc import AsyncIterator, Callable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from mcp_erp.authorization import Action, Decision, Principal, permits_scope

Outcome = Mapping[str, Any] | Decision
"""One item's answer: the domain's own payload, or a refused ``Decision``.

No new type, and that is the point. ADR-0013 says a handler returns *"a domain
outcome or a refused ``Decision``, never anything protocol-shaped"* — a shared
wrapper class would have to live somewhere, and the only package layers 1 and 3
may both import is layer 2, which would then hold a type describing how layer 1
renders. The union costs one ``isinstance`` at the single site that reads it.
"""

Handler = Callable[[Principal, Mapping[str, Any]], AsyncIterator[Outcome]]
"""A tool's implementation: a principal and parsed arguments in, outcomes out.

**Yielding rather than returning** is what makes ADR-0013's streaming rule
structural: layer 1 keys the response mode on **cardinality** — one outcome
answers ``application/json``, more than one opens the stream — and so never
learns which argument is the batch, nor that a tool is called
``approve_requisition``. A per-tool flag on the ``Action`` was rejected on
granularity: the mode is a property of the call, and one tool answers both ways.
"""


@dataclass(frozen=True, slots=True)
class ToolRegistration:
    """One tool, as layer 1 holds it.

    Attributes:
        name: What the caller names in ``tools/call``, and the key here.
        title: The display name.
        description: What a model reads before calling.
        input_schema: JSON Schema for the arguments, authored by layer 3.
        output_schema: JSON Schema for ``structuredContent``, authored by layer 3.
        action: What layer 2's chain is configured by. Layer 1 reads its
            ``scope`` and nothing else; the roles, rules and bypass are the
            chain's business.
        handler: The implementation.
    """

    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    action: Action[Any]
    handler: Handler


class Registry:
    """Every registered tool, and the two questions layer 1 asks of the set.

    Immutable after construction: the tool set is fixed at deploy, which is also
    why the listing declares ``listChanged: false`` — that notification announces
    that the *server's* set changed, and what varies here is per-caller, which
    the notification cannot express (ADR-0002).
    """

    def __init__(self, registrations: Iterable[ToolRegistration]) -> None:
        """Index the registrations by name, refusing a duplicate.

        Raises:
            ValueError: Two registrations share a name, which would make
                ``tools/call`` reach whichever the composition root happened to
                pass second.
        """
        indexed: dict[str, ToolRegistration] = {}
        for registration in registrations:
            if registration.name in indexed:
                raise ValueError(f"duplicate tool registration {registration.name!r}")
            indexed[registration.name] = registration
        self._registrations: Mapping[str, ToolRegistration] = MappingProxyType(indexed)

    def get(self, name: str) -> ToolRegistration | None:
        """The registration a caller named, or ``None`` if no tool has that name."""
        return self._registrations.get(name)

    @property
    def scopes_supported(self) -> tuple[str, ...]:
        """The scope vocabulary, derived from the declared capabilities and sorted.

        Published in the protected resource metadata and quoted in the no-token
        challenge. **Derived, never hand-written**: ADR-0012 made the tool's
        capability the single declaration that the listing filter,
        ``scopes_supported`` and the ``403`` challenge's ``scope`` parameter all
        come from, so the three cannot drift.

        Ejecting layer 3 leaves this rendering **empty**, which is ADR-0012's
        own falsifier for the scheme being a portable pattern rather than a
        naming convention.
        """
        return tuple(
            sorted({registration.action.scope for registration in self._registrations.values()})
        )

    def listed_for(self, principal: Principal) -> tuple[ToolRegistration, ...]:
        """The tools this principal's token permits, filtered on **granted scope alone**.

        Not the full chain. Running the role check here would hide a tool from a
        principal holding the scope but not the role, collapsing the ``-31010``
        denial class ADR-0002 exists to build — so listing is a strict *prefix*
        of the call gate, sharing one implementation with it rather than
        resembling it.

        This is also the invariant ADR-0002's cache proof rests on:
        :func:`~mcp_erp.authorization.policy.permits_scope` reads token-derived
        fields only, so the listing is a pure function of the access token and a
        ``private`` cache cannot serve one that misrepresents the caller's
        scopes.
        """
        return tuple(
            registration
            for registration in self._registrations.values()
            if permits_scope(principal, registration.action)
        )

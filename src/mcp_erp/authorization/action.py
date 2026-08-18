"""The seam: what one tool declares, and the two protocols the chain reads it through.

Layer 3 declares exactly one ``Action`` per tool and nothing else crosses the
boundary in that direction (ADR-0013). Ejecting the domain leaves every type
here intact with no instances declared, which is the whole of what the ejection
job proves.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from mcp_erp.authorization.principal import Principal
from mcp_erp.authorization.reasons import Reason


class Capability(StrEnum):
    """What a token must carry to reach a tool — the fixed vocabulary, owned here.

    Layer 3 supplies only the namespace token and which tool declares which of
    these; the words themselves are layer 2's and survive ejection (ADR-0012).
    ``decide`` rather than ``approve`` is what makes that survival honest: all
    three words are domain-free, where ``approve`` would have been layer 3
    wearing a layer-2 label.

    A domain needing a fourth word adds it **here**, which is the extension
    point — adding to this enum is a layer-2 edit, and that is the point.
    """

    READ = "read"
    WRITE = "write"
    DECIDE = "decide"


class Resource(Protocol):
    """The row an item-level decision is taken against.

    One member, deliberately. ``partition`` names the *value* row scoping
    compares, not the mechanism: prose keeps saying "row scoping" for the
    mechanism, and layer 3 maps the value to a cost centre. ``row_scope`` was
    rejected because ``principal.scopes`` and ``principal.row_scope`` would then
    sit in one record meaning different things, in the exhibit built to keep
    exactly that vocabulary straight (ADR-0013).

    A rule needing more than this member declares its own narrower protocol in
    layer 3 and parameterises its ``Action`` with it; layer 2 still reads only
    what is here.
    """

    @property
    def partition(self) -> str:
        """The partition this row belongs to."""


class Rule[R: Resource](Protocol):
    """A relationship rule — decided by the identities and amounts involved.

    ADR-0013 fixes the shape as ``(Principal, Resource) -> Reason | None``. The
    type parameter is that signature stated precisely rather than a departure
    from it: segregation of duties reads ``Requisition.submitted_by`` and the
    threshold reads an amount, neither of which is on :class:`Resource`, so an
    unparameterised protocol would force every layer-3 rule to cast its way back
    to the type it was declared alongside. ``R`` is bound to :class:`Resource`,
    so a rule can only ever narrow what layer 2 already requires.

    Parameter names are part of the contract: an implementation must name them
    ``principal`` and ``resource``.
    """

    def __call__(self, principal: Principal, resource: R) -> Reason | None:
        """Return the reason this rule refuses on, or ``None`` to pass."""


@dataclass(frozen=True, slots=True)
class Action[R: Resource]:
    """What one tool declares, and the only thing the policy chain is configured by.

    Every field is required — there are no defaults, so a declaration cannot
    omit one and inherit a permissive answer. ``partition_bypass`` is the field
    that makes this matter.

    Declarations need an explicit annotation to fix ``R``, because an action
    with no relationship rules leaves nothing for a type checker to infer it
    from::

        LIST_ROWS: Action[Requisition] = Action(
            namespace="erp",
            capability=Capability.READ,
            required_roles=frozenset(),
            rules=(),
            partition_bypass=frozenset({"auditor"}),
        )

    Attributes:
        namespace: The one domain-shaped token layer 3 supplies. Never parsed.
        capability: What a token must carry. Joined to the namespace, never
            split back out of a scope string.
        required_roles: Satisfied by holding **at least one** of these, which is
            the same semantics the authorization server's role scope mapping
            uses. Empty means the action is gated by scope alone.
        rules: The relationship rules, **in the order they are evaluated**. The
            first to refuse wins, so the tuple's order is a declaration about
            which refusal a caller sees.
        partition_bypass: Roles that read across partitions. Holds the auditing
            role on the two read tools and is **empty on the three writes**:
            breadth is a read widening, never a write grant. A reader who adds
            the auditing role here for symmetry on a write grants cross-partition
            writing, and nothing in this type will object (ADR-0013).
    """

    namespace: str
    capability: Capability
    required_roles: frozenset[str]
    rules: tuple[Rule[R], ...]
    partition_bypass: frozenset[str]

    @property
    def scope(self) -> str:
        """The granted scope a token must carry to reach this action.

        **Derived, never stored.** A stored literal would be a hand-written
        scope string in the one place the attack suite forbids one: the
        ``insufficient_scope`` scenario states that the ``scope=`` strings it
        asserts on are derived from the capability each tool declares. The three
        artifacts that consume it — the ``tools/list`` filter, ``scopes_supported``
        in the protected resource metadata, and the ``scope`` parameter of the
        ``403`` challenge — therefore cannot drift from each other (ADR-0012).
        """
        return f"{self.namespace}.{self.capability.value}"

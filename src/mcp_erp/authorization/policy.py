"""The one ordered chain, behind three entry points. The whole of the decision.

The order is fixed and it is a security property, not a style choice (ADR-0006):

1. **scope** — does the token carry what the action requires?
2. **role** — does the principal hold a role the action requires?
3. **row scoping** — is this row in the principal's partition, or does a role
   bypass that?
4. **relationship rules** — the identities and amounts involved, in the order
   the action declares.

Three entry points name where a caller stops. They are the *same* chain: steps
1 and 2 have one implementation and two call sites, which is what makes
"listing is a strict prefix of the call gate" visible rather than inferred.

**This module takes no collaborators at all.** Purity is structural rather than
promised — there is nothing to inject, so it cannot perform input or output even
by accident. Directory lookup is its own named step ahead of the chain
(:mod:`mcp_erp.authorization.directory`), and resource hydration is a named
layer-3 step ahead of it. An injected directory would make purity a promise
every implementation must keep, and the shipped one reads from a file.

**The N+1 evaluation is deliberate.** A batch of N items evaluates steps 1 and 2
once for the call and once per item. They are pure and cheap, and paying for
them keeps the fixed order in one implementation rather than two. A reader will
otherwise file it as a defect.
"""

from dataclasses import dataclass
from typing import Any

from mcp_erp.authorization.action import Action, Resource
from mcp_erp.authorization.principal import Principal
from mcp_erp.authorization.reasons import (
    INSUFFICIENT_SCOPE,
    NOT_FOUND,
    ROLE_MISSING,
    Reason,
)


@dataclass(frozen=True, slots=True)
class GateOutcome:
    """What the caller-level gates say about a whole call.

    A separate type from :class:`Decision`, and that is the point: a whole-call
    permit cannot be handed to something expecting an item permit. What this
    does **not** close, stated plainly — a handler that calls
    :func:`decide_call`, receives a permit and returns every row without ever
    calling :func:`decide_item` type-checks cleanly and fails open. Choosing the
    entry point is a handler obligation, handlers are layer 3, and no signature
    can force the item path to be walked. The falsifiers for that residual are
    behavioural and live at the wire (ADR-0013).
    """

    reason: Reason | None

    @property
    def permitted(self) -> bool:
        """Whether the call may proceed to its items."""
        return self.reason is None


@dataclass(frozen=True, slots=True)
class Decision:
    """What the whole chain says about one item.

    Refusals here are per-item: a batch yields one outcome per item **named in
    the request** — permit or refusal, never a silent drop. That is what makes
    the *answer* a function of the request rather than of the data.

    It said "the response mode" until ADR-0002 cut the streamed mode, leaving
    one wire shape and nothing to key. The rule is unchanged and now carries
    more: layer 1 folds N outcomes into one result body, and this is the
    invariant that fold rests on.
    """

    reason: Reason | None

    @property
    def permitted(self) -> bool:
        """Whether this item may be acted on."""
        return self.reason is None


def permits_scope(principal: Principal, action: Action[Any]) -> bool:
    """Step 1, alone: does the token carry this action's scope?

    Called directly by ``tools/list``, which cannot run the full chain — that
    would hide a tool from a principal holding the scope but not the role,
    collapsing the middle denial class ADR-0002 exists to build.

    **This function reads token-derived fields only** — never ``roles``, never
    ``partition``. ADR-0002's ``ttlMs`` proof depends on it: the listing is
    cacheable under ``cacheScope: "private"`` because it is a pure function of
    the access token, and new scopes mean a new token and so a different cache
    key. A role check here would make a directory revocation invisible for up to
    five minutes on an unchanged token, and nothing else in the code would
    object. If this ever reads a directory-derived field, that argument must be
    re-derived.

    The comparison is exact, case-sensitive set membership. Unrecognised scopes
    are inert for the same reason ``openid`` is — they are not in the set. Layer
    2 constructs scope strings and never parses one, so nothing here splits on
    the separator or inspects the namespace.

    The action's type parameter is unconstrained because this step reads nothing
    from a resource, and a caller filtering ``tools/list`` holds every declared
    action at once.
    """
    return action.scope in principal.granted_scopes


def decide_call(principal: Principal, action: Action[Any]) -> GateOutcome:
    """Steps 1 and 2: the refusals that depend on the caller rather than the row.

    Caller-level refusals are whole-call. Because a batch is one call, a refusal
    that depends on the caller cannot ride in a per-item result — it replaces
    the whole response.
    """
    if not permits_scope(principal, action):
        return GateOutcome(reason=INSUFFICIENT_SCOPE)
    # Holding **any one** of the required roles satisfies the gate; an empty set
    # means the action is gated by scope alone.
    if action.required_roles and not (action.required_roles & principal.roles):
        return GateOutcome(reason=ROLE_MISSING)
    return GateOutcome(reason=None)


def decide_item[R: Resource](
    principal: Principal, action: Action[R], resource: R | None
) -> Decision:
    """The whole chain, for one row.

    ``resource`` carries **no default**. A single entry point with a defaulted
    resource truncates the chain on argument absence: a handler that forgets to
    pass the row would get a permit indistinguishable from a real one, which is
    the class of fault the fixed order is named for.

    It is nonetheless nullable, and that is a different claim. Layer 3 hydrates
    the row with ``load(action, arguments) -> Resource | None`` before calling
    here, and passing that result straight through is what makes **the empty
    join and the foreign row converge**: a row that does not exist and a row in
    another partition are one refusal, reached through the single return site
    below. Two return sites would make the refusal an existence oracle, which is
    the finding ADR-0002 declined to ship.
    """
    call = decide_call(principal, action)
    if call.reason is not None:
        return Decision(reason=call.reason)
    # Step 3. The absent row and the foreign row converge here, on purpose: this
    # is the single return site the indistinguishability claim rests on, and
    # `tests/authorization` asserts structurally that there is only one.
    if resource is None or not _within_row_scope(principal, action, resource):
        return Decision(reason=NOT_FOUND)
    # Step 4, in the order the action declares. The first rule to refuse wins.
    for rule in action.rules:
        refusal = rule(principal, resource)
        if refusal is not None:
            return Decision(reason=refusal)
    return Decision(reason=None)


def _within_row_scope[R: Resource](principal: Principal, action: Action[R], resource: R) -> bool:
    """Step 3: one equality check on the partition, plus the roles that bypass it.

    Breadth is a role, not a wider membership — an auditing role reading three
    partitions of three is visibly a different mechanism from a principal who
    merely belongs to two.
    """
    if principal.roles & action.partition_bypass:
        return True
    return principal.partition == resource.partition

"""The one thing a handler says that is not about authorization at all.

A tool's declaration states what its arguments may be, and nothing on this stack
validates a call against that declaration — so an argument the declaration
forbids arrives at the handler rather than being refused ahead of it. ADR-0013
settled what happens next: layer 1 answers ``-32602``, the refusal vocabulary is
not amended, and the case is deliberately not a fourth denial class.

**What lives here is the signal, not the decision.** This module holds one
exception and no logic. It sits in layer 2 for the reason every other shared type
does — layers 1 and 3 import nothing from each other, so a name they both need
has exactly one place to be — and it survives ejection with nothing left raising
it, which is what a seam looks like when the half that uses it is deleted.

**Why not ``ValueError``, which ADR-0013 chose first.** The argument for it was
that a handler could signal without importing anything layer 1 owns — true of the
raise and false of the catch. Layer 1 wraps a handler's whole iteration and the
store is awaited inside it, so a type the standard library shares with every
library below made *the arguments are not ones the declared schema permits* the
answer to any ``ValueError`` from anywhere down there: a failure of ours, reported
to the caller as a mistake of theirs. The span could not be narrowed instead —
an async generator's body does not run until it is iterated — so the type is what
had to give.

**And why not layer 3, which the ticket proposed.** The *Transport and domain
never meet* contract makes those two packages independent, so a name in the domain
package is one layer 1 could not catch. ADR-0013's own words are *without
importing anything **layer 1** owns*, which layer 2 satisfies as well: ``Action``,
``Decision`` and ``Principal`` already cross here.

**It changes no authorization decision**, which is the governing rule's bar for
an entity earning its place — and it is not an entity or a field. It is the seam's
vocabulary, like ``Handler``'s shape and ``Outcome``'s, and the rule about what
layer 2 *decides* is untouched: nothing here is consulted by the chain.
"""


class UnusableArgument(Exception):
    """A handler was called with an argument its own declaration does not permit.

    **Not a refusal, and deliberately not one.** Nothing was authorized or denied
    — no gate ran, no rule fired, no row was read — so it carries no
    :class:`~mcp_erp.authorization.reasons.Reason` and gets the protocol's own
    code for a request that cannot be acted on. Giving it a ``Reason`` would
    amend a closed vocabulary for a spelling mistake, and would tell a model to
    route around a wall that is not there.

    **A type rather than ``ValueError``, since #82**, for the reason the module
    docstring gives. The negative guarantee is unchanged either way: the message
    is the handler's, and layer 1 never inspects it.
    """

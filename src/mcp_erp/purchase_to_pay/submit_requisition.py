"""``submit_requisition`` — scope-only, and the tool with no resource at all.

The first write, and the entry point that stops at
:func:`~mcp_erp.authorization.policy.decide_call`. There is nothing to decide
*against*: ADR-0013 says the resource is *"the thing acted against, never the
thing created"*, and a requisition does not exist at decision time.

**The partition is server-derived, so an out-of-partition write is
inexpressible rather than refused.** The input schema below takes no cost
centre; the row is stamped with the submitter's own, which the directory
resolved. ADR-0002 designed the input out and ADR-0003 closed the question that
would have brought it back — a person holds exactly one cost centre — and the
reason it stays out is the leak a free-text one would be: refusing an unknown
centre tells a caller which centres exist, and no schema anywhere enumerates
them.

The vendors *are* enumerated, and the difference is the same rule read
carefully. A vendor is a party the catalogue publishes; a cost centre is a fact
about the organisation's shape that row scoping decides on.
"""

from typing import Any, Final

from mcp_erp.authorization import Action, Capability
from mcp_erp.purchase_to_pay import vendors
from mcp_erp.purchase_to_pay.requisition import ROW_SCHEMA, Requisition

NAME: Final = "submit_requisition"
"""The tool's name on the wire, and the key layer 1's registry holds it under."""

TITLE: Final = "Submit requisition"

DESCRIPTION: Final = (
    "Raise a purchase requisition against a vendor. "
    "It is charged to the caller's own cost centre, which the server supplies "
    "and no argument can change."
)
"""What a model reads before calling.

The second sentence exists so a model does not go looking for the argument that
is not there. Row scoping is invisible in the schema of every tool here, and on
a write the invisible thing is not *which rows come back* but *which centre is
charged* — a model that assumed a default would otherwise retry with invented
arguments until the schema refused them.
"""

CURRENCY: Final = "EUR"
"""The one legal currency, carried explicitly on the way in as well as out.

An amount without a currency is a defect waiting for a second currency, which is
why the column exists with one legal value. Taking it as an argument with a
one-member ``enum`` says that in the place a caller reads, rather than defaulting
it silently and leaving the wire shape asymmetric with the row that comes back.
"""

AMOUNT_PATTERN: Final = r"^(0|[1-9][0-9]{0,9})(\.[0-9]{1,2})?$"
"""A decimal string, never a float — up to ten integer digits and two decimals.

The column is ``numeric(12, 2)``, and this is that stated where a model can read
it. It is a **declaration and not the enforcement**: nothing validates arguments
against a declared schema on this stack, so the handler parses the value itself
and a string this pattern would have refused is refused there. The pattern
deliberately admits ``0``, which the column's own ``CHECK (amount > 0)`` refuses
— expressing *positive* in a regular expression buys an unreadable pattern for a
rule the database already states.
"""

INPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        # Generated from the vendor rows, so the tool definition cannot drift
        # from the data — and it is names rather than identifiers because the
        # definition *is* the lookup: `list_vendors` was cut, so `ven_0002`
        # would be a value with nothing anywhere to resolve it against.
        "vendor": {"enum": vendors.names()},
        "amount": {"type": "string", "pattern": AMOUNT_PATTERN},
        "currency": {"enum": [CURRENCY]},
        "description": {"type": "string"},
    },
    "required": ["vendor", "amount", "currency", "description"],
    "additionalProperties": False,
}
"""Four arguments, and the fifth field of a requisition is the one not here.

``cost_centre`` is server-derived and ``submitted_by`` is the token's subject;
``id`` and ``status`` are the server's to mint. So the caller supplies exactly
what the organisation does not already know, which is ADR-0003's governing rule
running the other way: a field earns a place in this schema only if the server
cannot supply it.

``description`` is the named legibility exception (ADR-0003) — it changes no
authorization decision and is carried so a walkthrough reads.
"""

OUTPUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {"requisition": ROW_SCHEMA},
    "required": ["requisition"],
    "additionalProperties": False,
}
"""The row as written, in the shape the two read tools return.

Returning it rather than an identifier alone is what makes the server-stamped
cost centre observable: the caller sees which centre was charged without a
second call, and a walkthrough can show that it is theirs rather than assert it.
"""

ACTION: Action[Requisition] = Action(
    namespace="erp",
    capability=Capability.WRITE,
    required_roles=frozenset(),
    rules=(),
    partition_bypass=frozenset(),
)
"""What ``submit_requisition`` declares — the **empty** half of ADR-0013's field.

``partition_bypass`` is empty because breadth is a read widening and never a
write grant. ADR-0013: it holds ``{auditor}`` on the two read tools and is
*"empty on the three writes"*; ADR-0007 puts the same rule as *"``auditor``
widens which rows are returned, it does not grant reading."*

**Declaring it empty here is honest rather than ceremonial.** This tool has no
resource at all, so ``decide_call`` is its entry point and the field is never
consulted — only ``decide_item`` reads it. Stating it anyway is what stops the
value becoming a latent grant if the tool ever acquires a resource, and nothing
in the type will object to the wrong one: ADR-0013 records that as a known cost
and #34 declined to close it in layer 2, because a constructor check reading
*bypass is legal only on a read* would be layer 2 legislating a rule the ADR
deliberately left open, on a field whose whole point is that layer 3 owns it.

``required_roles`` is empty because submitting is gated by scope alone
(ADR-0003): anyone who can reach the server may raise a requisition against
their own centre, and ADR-0003's option 7 rejected a fifth role for modelling a
permission almost everyone holds. The consequence is that ``erp.write`` is the
only thing standing between a caller and a row — which is exactly why a directory
miss yields no principal at all rather than one with no roles (ADR-0013).

The explicit annotation fixes ``R`` with no relationship rules to infer it from.
``Requisition`` is the parameter even though nothing is decided against one,
because it is the type this Action's rules would read if it ever grew any.
"""

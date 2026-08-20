"""What one Person sees, and what one Person raises, for every suite that asks.

The third piece of shared tooling above the test directories, beside `rpc.py`,
`tokens.py` and `fixtures.py`, and it is here for the reason
`tokens.py` states: shared tooling that lives in one artifact's directory
becomes that artifact's and gets copied by the next. This one was written three
times before it moved — once in `list_partition_scoped`, once beside the write
suite to assert that a refused submission wrote nothing, and once for the
named-versus-discovered contract.

**It is one question, not one tool call.** *Which rows come back* is what row
scoping is about, so what a suite wants is the set of identifiers rather than
the result body — and set equality over returned identifiers is what ADR-0003
fixed read rows on, because no entity carries a timestamp and there is no order
the authorization model has an opinion about.

`get_requisition` and `submit_requisition` are deliberately absent. Their
callers want different things from the same call — a parsed result here, a raw
response there, so a refusal's status code and headers can be asserted — and a
helper that returned one shape would have the other suite unwrapping it back.

*Amended 2026-08-20 by #41, on the same rule that put the first function here.*
**Raising a row for a suite to act on is a third caller, and it moved at three.**
`raised_by` was written once beside `approve_requisition`'s suite, once beside
the fold's, and once beside `double_approval_via_batch_retry` — the same three
that the sentence above says brings a helper up here.

It does not reopen the exclusion; it narrows what the exclusion was about. That
paragraph names the suite that **tests** submitting, which wants the raw response
so a refusal's status code and headers can be asserted, and it still gets one.
This serves the suites that need a row to **exist** before they can assert
anything about deciding it, and all three of them want the same one thing: the
identifier. A suite that raises a row as setup and one that asserts on the
raising are two callers, not one written twice.
"""

from __future__ import annotations

import rpc
from tokens import mint

LIST = "list_requisitions"
SUBMIT = "submit_requisition"

VENDOR = "Meridian Cloud Services"
"""One of the four names `submit_requisition` enumerates.

Nothing that raises a row for setup turns on which vendor it names, so they all
name this one — a suite that picked its own would be declaring a variable that
changes no assertion.
"""

DESCRIPTION = "Quarterly window cleaning"
"""The default label, and the one thing here a caller sometimes overrides.

`description` is ADR-0003's named legibility exception, and it is the half of a
raised row that surfaces again: a purchase order carries it as its
requisition's label, so a suite asserting on that pair needs to know the word it
sent.
"""


def visible_to(username: str) -> set[str]:
    """The requisition identifiers one Person sees through the tool, over the wire.

    Minted with `erp.read` alone, because that is the ceiling this question is
    asked under: the tool is gated by scope, and a wider token would be asking a
    different question of the same Person.

    Raises:
        AssertionError: The call was refused. Every caller wants the set, so a
            refusal is a broken precondition rather than an answer — and one that
            reads better here, with the result in the message, than as a
            `KeyError` in whichever assertion consumed it.
    """
    minted = mint(username, ["erp.read"])
    result = rpc.result(rpc.call_tool(LIST, token=minted.access_token))

    assert result["isError"] is False, result
    return {row["id"] for row in result["structuredContent"]["requisitions"]}


def raised_by(username: str, amount: str, *, description: str = DESCRIPTION) -> str:
    """Raise one requisition as this Person and return its identifier.

    **Against their own cost centre, because there is no other kind.**
    `submit_requisition` takes no cost centre and stamps the submitter's, so who
    raises the row is what decides which centre it lands in — which is how a
    CC-4300 row above the threshold gets written at all, and why a suite that
    needs a row *somewhere* names the Person rather than the place.

    Minted with `erp.write` alone, for the reason `visible_to` mints with
    `erp.read` alone: that is the ceiling this call is made under, and a wider
    token would be raising the row under a different question.

    Args:
        username: Who raises it. Their cost centre is the row's.
        amount: The decimal string, which is what decides whether the threshold
            refuses an approver later. Required rather than defaulted, because
            every caller is choosing a side of it.
        description: The label, which comes back on a purchase order raised from
            this row.

    Raises:
        AssertionError: The submission was refused. Every caller wants a row to
            act on, so a refusal is a broken precondition rather than an answer.
    """
    minted = mint(username, ["erp.write"])
    result = rpc.result(
        rpc.call_tool(
            SUBMIT,
            {
                "vendor": VENDOR,
                "amount": amount,
                "currency": "EUR",
                "description": description,
            },
            token=minted.access_token,
        )
    )

    assert result["isError"] is False, result
    identifier: str = result["structuredContent"]["requisition"]["id"]
    return identifier

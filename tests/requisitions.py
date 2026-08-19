"""What one Person sees through `list_requisitions`, for every suite that asks.

The third piece of shared tooling above the test directories, beside `rpc.py`,
`tokens.py` and `seeded_requisitions.py`, and it is here for the reason
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
"""

from __future__ import annotations

import rpc
from tokens import mint

LIST = "list_requisitions"


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

"""The three shapes a refusal takes on the wire, and the two that layer 1 renders alone.

ADR-0002 keyed the shapes on **what would fix this for the caller**, never on
which rule fired:

======================================  ==============================  ====================
Situation                               Wire                            Remedy
======================================  ==============================  ====================
No credentials at all                   ``401`` + a challenge, no error  Present one
Token presented and rejected            ``401`` + ``invalid_token``      Get a valid one
Scope absent, tool called anyway        ``403`` + ``insufficient_scope`` Re-authorize
Scope present, ERP role absent          JSON-RPC ``-31010``              An administrator grants
Domain rule violated                    Tool result, ``isError: true``   A different person acts
======================================  ==============================  ====================

A ``403`` on the missing-role case would be a **lie**: it carries a header
instructing the client to acquire a scope it already holds, producing an
identical token and an identical refusal — a loop. That is the whole reason
three shapes exist rather than one.

**Layer 1 learns the shape, never the grounds.** Everything below keys on
``denial_class`` or on a description from :mod:`mcp_erp.transport.tokens`'s
closed vocabulary. Nothing here knows which rule fired, against which attribute,
on which row (ADR-0013).
"""

import json
from collections.abc import Mapping
from typing import Any, Final

from starlette.responses import Response

from mcp_erp.authorization import Reason

RequestId = str | int | None
"""A JSON-RPC request identifier, in the two shapes the specification permits.

``None`` covers both an absent identifier and a body this server could not read
— JSON-RPC asks for ``null`` in exactly that case.
"""

ROLE_DENIED_CODE: Final = -31010
"""The JSON-RPC code for scope-present-role-absent.

Not a value in ``-32000…-32019``: that sub-range is **legacy** — *"New codes
MUST NOT be allocated in this sub-range"* — and new application codes should sit
outside the reserved range ``-32768…-32000`` entirely. Any implementation
reaching for the "implementation-defined" JSON-RPC range under this revision is
wrong (ADR-0002).
"""

INVALID_TOKEN: Final = "invalid_token"
INSUFFICIENT_SCOPE: Final = "insufficient_scope"

JSON_RPC_VERSION: Final = "2.0"


def missing_credentials(*, metadata_url: str, scopes: tuple[str, ...]) -> Response:
    """The challenge for a request carrying no credentials at all.

    **No error code, deliberately.** RFC 6750 draws the line and ADR-0006 honours
    it: nothing is wrong with the token, there simply is not one. An error code
    belongs only where a token was presented and rejected, and inventing one here
    would tell a client to fix something it has not done.
    """
    return _challenge(
        401,
        _parameters(resource_metadata=metadata_url, scope=" ".join(scopes)),
    )


def rejected_credentials(description: str, *, metadata_url: str) -> Response:
    """The challenge for a token that was presented and refused.

    ``error_description`` carries one word from
    :data:`mcp_erp.transport.tokens.DESCRIPTIONS`. Four of those are named attack
    scenarios, and without distinguishable descriptions they would all assert the
    same ``401`` — which is why the vocabulary is closed rather than free prose.
    """
    return _challenge(
        401,
        _parameters(
            error=INVALID_TOKEN,
            error_description=description,
            resource_metadata=metadata_url,
        ),
    )


def insufficient_scope(scope: str, *, tool: str, metadata_url: str) -> Response:
    """The ``403`` for a token that does not carry the called tool's scope.

    It names a **scope genuinely published** in ``scopes_supported`` and confirms
    a **tool name the caller themselves supplied**. Neither is a fact only the
    database holds, which is the repaired form of ADR-0002's disclosure rule:
    ADR-0006 found the original justification wrong — RFC 9728 publishes no tool
    names — while the rule survived.
    """
    return _challenge(
        403,
        _parameters(
            error=INSUFFICIENT_SCOPE,
            error_description=f"the token does not carry {scope!r}, required by {tool!r}",
            scope=scope,
            resource_metadata=metadata_url,
        ),
    )


def forbidden_origin() -> Response:
    """The ``403`` for a browser-originated request.

    Plain text and no challenge: re-authorizing would not help, because what is
    refused is where the request came from rather than what it carried.
    """
    return Response("Origin not allowed", status_code=403, media_type="text/plain")


def protocol_error(
    code: int,
    message: str,
    *,
    request_id: RequestId = None,
    data: Mapping[str, object] | None = None,
    status: int = 200,
) -> Response:
    """A JSON-RPC error as an HTTP response, for the gates that run before dispatch.

    The gates sit outside the protocol package's ASGI application, so a refusal
    they raise has to be rendered here rather than by it. ``request_id`` is
    whatever the body carried — ``null`` when the body could not be read, which
    is what JSON-RPC asks for when the identifier is unknown.
    """
    body = {
        "jsonrpc": JSON_RPC_VERSION,
        "id": request_id,
        "error": {"code": code, "message": message} | ({"data": data} if data is not None else {}),
    }
    return Response(json.dumps(body), status_code=status, media_type="application/json")


def refusal_payload(reason: Reason) -> dict[str, Any]:
    """The structured half of a refusal, for a tool result or a JSON-RPC error's data.

    Every field comes off the :class:`~mcp_erp.authorization.reasons.Reason`
    record, which states its own wire shape at the point of declaration — so
    there is no lookup table here and nothing can name a reason without also
    saying what it does to a client (ADR-0013).

    ``retry_as_other_person_helps`` is the field that earns the vocabulary: *do
    not retry* is right for two of layer 2's three reasons and wrong for
    segregation of duties, where retrying as a different person is the correct
    move.
    """
    return {
        "reason": reason.value,
        "remedy": reason.remedy.value,
        "retry_identical_helps": reason.retry_identical_helps,
        "retry_as_other_person_helps": reason.retry_as_other_person_helps,
    }


def _challenge(status: int, parameters: str) -> Response:
    """A ``WWW-Authenticate`` response with an empty body.

    Built directly rather than raised as an exception. #32 established that
    route-level middleware sits inside the application's exception handling and
    that an ``HTTPException`` would render normally, so this is a choice and no
    longer a constraint — a header-carrying refusal reads better written than
    routed.
    """
    return Response(
        status_code=status,
        headers={"WWW-Authenticate": f"Bearer {parameters}"},
    )


def _parameters(**values: str) -> str:
    """Quoted ``auth-param`` pairs in the order given, skipping empty values.

    RFC 6750 §3 makes every one of these a quoted string. Order is the argument
    order rather than sorted, so the tests read in the same sequence the
    specification's own examples do.
    """
    return ", ".join(f'{name}="{value}"' for name, value in values.items() if value)

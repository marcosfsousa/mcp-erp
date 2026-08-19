"""The protected resource metadata document, and the route that answers it.

RFC 9728 is one of the two hard ``MUST``s that land on a resource server — the
half most exhibits do shallowly, and the half that survives the authorization
server being swapped (ADR-0005).

**This route sits outside the token gate structurally**, as a sibling of the tool
endpoint rather than by a path allow-list on a gate. The preference is for an
attack to be impossible rather than defended against, which is the same move the
gate ordering makes.

**Published both ways.** The document is served here *and* named by
``resource_metadata`` in every ``WWW-Authenticate`` challenge. A server need
implement only one; clients must support both, and implementing both costs
little once the document exists.
"""

from typing import Any, Final

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from mcp_erp.transport.configuration import Configuration

DOCUMENTATION_URL: Final = "https://github.com/marcosfsousa/mcp-erp"
"""Where a reviewer goes next.

``resource_documentation`` is one of the three optional fields ADR-0006 kept, and
it earns its place by being the only field that points at the reasoning behind
everything else here.
"""

BEARER_METHODS: Final = ["header"]
"""Publishing this is what makes *no token in the query string* a contract.

RFC 6750 forbids a token in the URI query string; declaring the supported method
turns a behaviour this server happens to exhibit into one it has published and
then keeps, which is what ``token_in_query_string`` asserts against.
"""


def document(configuration: Configuration, scopes_supported: tuple[str, ...]) -> dict[str, Any]:
    """The document itself: two required fields plus three that earn their place.

    ``offline_access`` is deliberately absent from ``scopes_supported``: the
    specification says a protected resource **SHOULD NOT** list it, since refresh
    tokens are not a resource requirement.

    ``scopes_supported`` is derived from the capability each tool declares, so it
    cannot drift from the ``tools/list`` filter or from the ``scope`` parameter of
    a ``403`` challenge — one declaration, three artifacts (ADR-0012).
    """
    return {
        "resource": configuration.resource,
        "authorization_servers": [configuration.issuer],
        "scopes_supported": list(scopes_supported),
        "bearer_methods_supported": BEARER_METHODS,
        "resource_documentation": DOCUMENTATION_URL,
    }


def route(configuration: Configuration, scopes_supported: tuple[str, ...]) -> Route:
    """The route serving the document, at the **path-inserted** address and no other.

    ``GET /.well-known/oauth-protected-resource/mcp`` answers; the bare
    ``/.well-known/oauth-protected-resource`` does not, and its ``404`` is a
    decision rather than an oversight — that address describes a resource
    identifier with no path component, which is a different resource from ours.
    """
    payload = document(configuration, scopes_supported)

    async def endpoint(request: Request) -> JSONResponse:
        """Answer the document, to anyone, with no token."""
        return JSONResponse(payload)

    return Route(configuration.metadata_path, endpoint=endpoint, methods=["GET"])

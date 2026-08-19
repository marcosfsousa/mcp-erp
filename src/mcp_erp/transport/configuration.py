"""The three strings the server is configured with, and nothing else.

ADR-0005 configures the resource server with **the issuer** and has it discover
everything else — the authorization server's metadata, and through it the key
set. That is what makes swapping Keycloak for a self-authored server a
one-string change rather than a migration, and it is why there is no
``jwks_uri`` setting here to drift from the issuer that implies it.

Two more strings earn their place. The **resource identifier** is what this
server calls itself in its own protected resource metadata and what it demands
in a token's audience; it is a second input only because it is a fact about us
rather than about the authorization server. The **database URL** is layer 3's,
and it is here because the composition root is the only module that may hold
both.

**Nothing has a default.** A missing issuer or resource identifier is a boot
failure, not a server that starts and validates against a guess: the audience
check is the load-bearing control that RFC 8707's unhonoured ``resource``
parameter left carrying everything — the register's *Resource indicators
unhonoured* deviation — and a default would make the one string it compares against
something nobody chose. The
authorization server's realm gives its placeholders defaults for the opposite
reason — an unresolved ``${VAR}`` is left literally in place rather than
erroring — so the asymmetry is deliberate on both sides.
"""

import os
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlsplit

ISSUER_VARIABLE: Final = "MCP_ISSUER"
"""The authorization server this resource server trusts, and the only one."""

RESOURCE_VARIABLE: Final = "MCP_RESOURCE_URL"
"""This server's resource identifier — its own URL in the environment it runs in.

The same name the realm's audience mapper resolves, deliberately: the value a
token carries in ``aud`` and the value this server compares it against are one
string set in one place, so a mismatch is a Compose edit rather than a silent
acceptance.
"""

DATABASE_VARIABLE: Final = "DATABASE_URL"
"""Where the ERP's rows live."""


@dataclass(frozen=True, slots=True)
class Configuration:
    """Everything the composition root needs to build the application.

    Attributes:
        issuer: The authorization server's issuer identifier. Discovery is
            path-inserted from it (RFC 8414 §3), and every token must name it.
        resource: This server's resource identifier, published in its protected
            resource metadata and required in every token's audience.
        database_url: Layer 3's connection string.
    """

    issuer: str
    resource: str
    database_url: str

    @property
    def metadata_path(self) -> str:
        """Where the protected resource metadata document is served.

        **Path-inserted, and only path-inserted.** RFC 9728 §3.1 puts the
        well-known segment between host and path rather than appending it —
        research 0003 calls that the single most commonly mis-implemented line
        in the whole discovery chain. The bare root address is deliberately not
        served: it describes a resource identifier with no path component,
        which is a *different resource* from ours, and answering there would be
        a conformance error dressed as helpfulness.
        """
        path = path_of(self.resource)
        return f"/.well-known/oauth-protected-resource{path}"

    @property
    def metadata_url(self) -> str:
        """The absolute address of the metadata document, for a challenge to name.

        Both discovery mechanisms the specification offers point at one document:
        this string is what every ``WWW-Authenticate`` challenge carries in
        ``resource_metadata``, and :attr:`metadata_path` is where that same
        document is served. One derivation, so a client following the header and
        a client guessing the well-known address arrive at the same place.
        """
        return f"{origin_of(self.resource)}{self.metadata_path}"

    @property
    def endpoint_path(self) -> str:
        """The path the tool endpoint answers on, taken from the resource identifier.

        Derived rather than configured, so the address a client posts to and the
        address the audience names cannot come apart.
        """
        return path_of(self.resource) or "/"


def from_environment() -> Configuration:
    """Read the configuration from the process environment, or refuse to start.

    No injection seam. ``create_app`` already takes a :class:`Configuration`
    directly, so a second one here would be a parameter with no caller — and the
    thing worth being able to build without an environment is the application,
    not this function.

    Raises:
        RuntimeError: A required variable is unset or empty, named in the
            message so the failure says which one.
    """
    source = os.environ
    missing = [
        name
        for name in (ISSUER_VARIABLE, RESOURCE_VARIABLE, DATABASE_VARIABLE)
        if not source.get(name)
    ]
    if missing:
        raise RuntimeError(f"required environment variable(s) unset: {', '.join(missing)}")

    return Configuration(
        issuer=source[ISSUER_VARIABLE].rstrip("/"),
        resource=source[RESOURCE_VARIABLE].rstrip("/"),
        database_url=source[DATABASE_VARIABLE],
    )


def path_of(url: str) -> str:
    """The path component of an absolute URL, without its trailing slash.

    One normalisation, used by everything in layer 1 that has to take a URL
    apart. A second hand-rolled parser somewhere else in the package is how the
    metadata document ends up describing an address the endpoint is not served
    at — so the split is the standard library's and the trailing-slash rule is
    stated once.
    """
    return urlsplit(url).path.rstrip("/")


def origin_of(url: str) -> str:
    """The scheme and authority of an absolute URL, with no path."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"

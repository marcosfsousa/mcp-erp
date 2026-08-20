"""The seed's issuers and what Compose actually configures, held equal.

`docs/organisation/seed.yaml` carries both identifiers the realm answers to, and
`compose.yaml` carries the strings the containers run on. They are one fact
written in two files, and the failure when they disagree is the worst shape this
repository has: a token that clears every gate — signature, issuer, audience,
scope — and is then refused at the principal directory with `role_missing`,
several steps from the line that caused it. `IdentitySeed.issuers` and
`tests/tokens.py`'s issuer check both exist to keep that failure unreachable;
neither of them can see an edit to `compose.yaml` or to `tls.env`.

**It interpolates rather than matching literals.** Compose's `${VAR:-default}`
is the mechanism the whole profile rests on — the default configuration is what
the file says with nothing set, and the profile is what it says with `tls.env`
set — so the assertions below resolve both the way Compose does and compare the
results. A literal match would pass on a file whose default had been moved into
the variable, which is exactly the edit that breaks the zero-setup run.

No Docker and no network: this asks whether committed files agree, which is a
question about files. It runs in `Seed renders clean`, beside the other
invariants a diff cannot see.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from mcp_erp.authorization.identity import SEED, IdentitySeed, read_identity_seed

REPOSITORY = Path(__file__).resolve().parents[1]
"""The checkout, for the three committed files this reads."""

COMPOSE = REPOSITORY / "compose.yaml"
PROFILE = REPOSITORY / "tls.env"

REPLICAS = ("server-1", "server-2")
"""Both, because one replica configured differently is a stack that half works."""

SUBSTITUTION = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")
"""Compose's `${NAME}` and `${NAME:-default}`, which is all this file uses.

Deliberately not a general implementation of Compose's interpolation grammar:
`:?`, `-` without the colon and nested braces are unused here, and a parser for
syntax nothing writes would be a second thing to keep true.
"""


def _interpolate(value: str, environment: dict[str, str]) -> str:
    """Resolve one Compose value the way Compose would, given an environment."""

    def resolve(match: re.Match[str]) -> str:
        return environment.get(match.group(1)) or match.group(2) or ""

    return SUBSTITUTION.sub(resolve, value)


def _env_file(path: Path) -> dict[str, str]:
    """An env file, as Compose reads it: `NAME=value`, comments and blanks skipped.

    One reader for both of them — `tls.env` and the TLS-only Keycloak options it
    points at — because they are the same format and a second parser would be a
    second set of edge cases.
    """
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, _, value = stripped.partition("=")
        values[name] = value
    return values


@pytest.fixture(scope="module")
def seed() -> IdentitySeed:
    """The committed organisation, which is where both issuers are authored."""
    return read_identity_seed((REPOSITORY / SEED).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def services() -> dict[str, Any]:
    """`compose.yaml`'s services, uninterpolated — the templates, not one resolution."""
    document: dict[str, Any] = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services: dict[str, Any] = document["services"]
    return services


@pytest.fixture(scope="module")
def profile() -> dict[str, str]:
    """`tls.env`, which is the whole of what selecting the profile means."""
    return _env_file(PROFILE)


def _issuer(services: dict[str, Any], environment: dict[str, str]) -> str:
    """The one issuer this stack would run on, resolved for one environment.

    Both replicas and the authorization server's own hostname go into it, and the
    function refuses to answer unless they agree: a resource server demanding one
    issuer while Keycloak stamps another is a stack that boots and then refuses
    every token it is given.
    """
    demanded = {
        _interpolate(services[replica]["environment"]["MCP_ISSUER"], environment)
        for replica in REPLICAS
    }
    assert len(demanded) == 1, demanded

    issuer = demanded.pop()
    stamped = _interpolate(services["keycloak"]["environment"]["KC_HOSTNAME"], environment)
    assert issuer.startswith(f"{stamped}/"), (issuer, stamped)

    return issuer


def test_the_default_configuration_runs_on_the_seed_s_issuer(
    services: dict[str, Any], seed: IdentitySeed
) -> None:
    """`docker compose up` with nothing set, against the string the seed authors.

    This is the assertion that catches a default moved into `tls.env` — the edit
    that would leave the zero-setup run configured for a stack it cannot reach.
    """
    assert _issuer(services, {}) == seed.issuer


def test_the_profile_runs_on_the_second_issuer_the_seed_authors(
    services: dict[str, Any], profile: dict[str, str], seed: IdentitySeed
) -> None:
    """`--env-file tls.env`, against `tls_issuer` — the one that has directory rows."""
    assert _issuer(services, profile) == seed.tls_issuer


def test_the_profile_file_selects_a_profile_some_service_carries(
    services: dict[str, Any], profile: dict[str, str]
) -> None:
    """One flag, and it has to reach a service or it is an env file with opinions.

    `COMPOSE_PROFILES` is a Compose setting read from an env file like any other,
    which is what makes `docker compose --env-file tls.env up` one command rather
    than two flags. Naming a profile no service carries would start the stack with
    the profile's issuer set and no certificate minted — TLS demanded and nothing
    to serve it with.
    """
    carried = {name for service in services.values() for name in service.get("profiles", ())}

    assert profile["COMPOSE_PROFILES"] in carried


def test_the_profile_serves_tls_on_the_one_published_port(
    services: dict[str, Any], profile: dict[str, str]
) -> None:
    """The published port does not move, and that is what protects the default run.

    A second published port would be a change to a reader who never selected the
    profile — their machine may already be using it — so the profile puts HTTPS on
    the port that is published either way and moves the plain listener to one that
    is published nowhere.
    """
    keycloak = services["keycloak"]
    published = {str(entry).split(":")[0] for entry in keycloak["ports"]}
    options = _env_file(REPOSITORY / profile["MCP_TLS_KEYCLOAK_ENV"])
    plain = _interpolate(str(keycloak["environment"]["KC_HTTP_PORT"]), profile)

    assert published == {options["KC_HTTPS_PORT"]}
    assert plain not in published

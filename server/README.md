# `server/` — the resource server's image

One file. `Dockerfile` builds the exhibit's own server, and `compose.yaml` runs
**two of it** behind `gateway/` — which is what makes map constraint `#5`'s
statelessness falsifiable rather than asserted.

## Two pinned images, pinning different things

Map constraint `#11`, applied twice in one file:

| Image | What it holds still |
| --- | --- |
| `python:3.13.15-slim` | The **interpreter**, at the exact patch `.python-version` names |
| `ghcr.io/astral-sh/uv` | The **resolver**, so the lockfile is read by the tool that wrote it |

Python dependencies pin by lockfile rather than by tag: `uv.lock` is committed
and `--locked` fails rather than re-resolving. All three move only in a pull
request that does nothing else.

`--no-dev` is not an optimisation. A module the application imports but this
image does not carry resolves fine on a runner and fails at container start,
which is the failure the dev group exists to prevent — so installing a
superset here would make continuous integration faithful to nothing.

## Configuration: three strings, none with a default

```
MCP_ISSUER        the one authorization server this server trusts
MCP_RESOURCE_URL  what this server calls itself, and what every token must name
DATABASE_URL      the ERP's rows
```

A missing value is a boot failure rather than a server that starts and validates
against a guess. The audience check is the load-bearing control — Keycloak does
not honour RFC 8707's `resource` parameter, which is normative register row 1 —
and a defaulted resource identifier would make the one string it compares
against something nobody chose.

Everything else is **discovered** from the issuer: the authorization server's
metadata document, and through it the key set. That is what makes swapping
Keycloak for a self-authored server a one-string change (ADR-0005).

## Running it

```
docker compose up
```

The gateway publishes `http://localhost:8080`, which is the resource identifier
and therefore the address a token's audience names. Neither replica publishes a
port of its own, deliberately: a caller that could reach one directly could pin
itself to it, and the statelessness result would be one nobody tested.

To watch one replica:

```
docker compose logs -f server-1
```

## Running it outside a container

Possible on Linux and macOS —

```
MCP_ISSUER=http://keycloak:8081/realms/mcp-erp \
MCP_RESOURCE_URL=http://localhost:8080/mcp \
DATABASE_URL=postgresql://mcp_erp:not-a-secret-demo-password@localhost:5432/mcp_erp \
uv run uvicorn --factory mcp_erp.app:create_app --port 8080
```

— and **not on Windows**, where psycopg refuses asyncio's default
`ProactorEventLoop` and says so at the first query. That is a property of the
driver rather than of this server, the container runs Linux, and the evaluation
moment is `docker compose up` (ADR-0011). It is written down here because the
failure arrives as a pool error in a log rather than as a refusal to start.

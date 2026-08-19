# `gateway/` — one address in front of two replicas

`nginx.conf`, mounted read-only by `compose.yaml`. It exists so that map
constraint `#5` — *two replicas, no sticky sessions, so statelessness is
falsifiable rather than asserted* — is something a reader can watch.

## Why a fourth service

The resource identifier is one URL, `http://localhost:8080/mcp`, and it is what
every token's audience names. Two replicas therefore have to answer at one
address, and Compose publishes a host port to one container. The alternative —
two replicas on two host ports — would make the audience a claim about a port no
caller used.

## Why two named upstreams rather than a scaled service

nginx resolves an upstream name **once at start-up**. A single scaled service
name would hand it whichever address Docker's resolver returned first, and the
alternation this file exists to demonstrate would depend on that ordering. Two
names is nginx's own default round robin: deterministic, and observable.

The cost is stated rather than discovered: a replica replaced while nginx is
running keeps its old address until nginx reloads. `docker compose up` creates
both before the gateway starts, and nothing in the exhibit replaces one mid-run.

## `X-Served-By`

Every response carries the upstream that served it. It is the **gateway's**
statement about its own routing, not something the resource server says about
itself — the server has no idea it is one of two, which is the property under
test.

It names a container address inside a network that exists on the reader's
machine and nowhere else (ADR-0011), so there is nothing here to leak. A
byte-identity assertion over a whole HTTP response would have to exclude it; the
ones this exhibit makes are over the JSON-RPC body, which no proxy touches.

## What it does not do

No TLS. Plain HTTP on both identifiers is normative register row 2, a hard
`MUST` deviation carried deliberately, and the route that would close it —
terminating TLS at a fixed hostname as a **non-default opt-in profile** — is
declined for v1 on setup cost rather than on impossibility. This file is where
that profile would land.

No `Origin` header is added or removed. Gate 1 lives in the server, where the
allow-list ships empty and the emptiness is the position.

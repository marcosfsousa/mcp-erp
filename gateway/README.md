# `gateway/` — one address in front of two replicas

`nginx.conf`, mounted read-only by `compose.yaml`. It exists so that map
constraint `#5` — *two replicas, no sticky sessions, so statelessness is
falsifiable rather than asserted* — is something a reader can watch.

## Why a fourth service

**ADR-0006 §Discovery is published both ways, at one address** holds the
argument: one resource identifier means one published address, two replicas mean
something has to stand in front of them, and the audience check is why the
alternative — two replicas on two host ports — hollows out a control while
leaving it green.

It is not restated here. What follows is the mechanics of the thing that stands
in front.

## Why two named upstreams rather than a scaled service

nginx resolves an upstream name **once at start-up**. A single scaled service
name would hand it whichever address Docker's resolver returned first, and the
alternation this file exists to demonstrate would depend on that ordering. Two
names is nginx's own default round robin: deterministic, and observable.

The cost is stated rather than discovered: a replica replaced while nginx is
running keeps its old address until nginx reloads. `docker compose up` creates
both before the gateway starts, and nothing in the exhibit replaces one mid-run.

## `Host`, and the pool behind it

The upstream sees the `Host` a caller wrote, port and all — `$http_host` rather
than `$host`, which drops the port. It decides nothing: the audience is compared
against the configured resource identifier, and a request carrying
`Host: evil.example` is answered identically (execution, 2026-08-20). The
directive is there so the gateway is not the thing that rewrites who a caller
said it was calling.

Connections to the replicas are pooled and reused. That takes three things
together — HTTP/1.1, a cleared `Connection` header, and `keepalive` on the
`upstream` block — and without the third, one run of 41 requests opened 41
upstream connections where the same run now opens two. #83 has the measurement.

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

No TLS. Plain HTTP on both identifiers is the normative register's *Plain-HTTP
identifiers* deviation, a hard `MUST` departure carried deliberately, and the route that would close it —
terminating TLS at a fixed hostname as a **non-default opt-in profile** — is
declined for v1 on setup cost rather than on impossibility. This file is where
that profile would land.

No `Origin` header is added or removed. Gate 1 lives in the server, where the
allow-list ships empty and the emptiness is the position.

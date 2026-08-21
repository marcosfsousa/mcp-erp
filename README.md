# mcp-erp

A Model Context Protocol server exposing a mock enterprise resource planning
system, with OAuth 2.0 as a first-class concern. It is a **portfolio exhibit**:
it exists to be read and run, not to serve users.

It closes two gaps that contract postings ask for and a file tree does not show.

**The Model Context Protocol as a build task.** A modern-era server — revision
`2026-07-28`, which removed connection initialization entirely — answering real
clients over Streamable HTTP, with five purchase-to-pay tools and no handshake to
establish anything.

**OAuth 2.0, OpenID Connect and role-based access control.** Tokens are earned
through a real authorization code flow against a real authorization server,
validated here against its published keys, and every call is decided by granted
scope intersected with roles the server resolves per request. A token is a
ceiling on what an application may do on someone's behalf; it is never a
statement of what that person is allowed to do.

## Run it

Docker Compose 2.24 or newer, and [uv](https://docs.astral.sh/uv/). One line in
your hosts file first, because the issuer is a name that has to resolve
identically inside the container network and outside it:

```
127.0.0.1 keycloak
```

Then:

```
uv sync
docker compose up --wait
uv run python tests/conformance_client.py priya.raman
```

The last line performs the whole flow — a client identified by a document GitHub
Pages serves, a login, a consent screen, a redeemed code — and calls a tool with
the token it earned. `uv run pytest` runs everything; each suite's own README
says what it asserts and whether it needs the stack up.

**No browser can complete a login against the default configuration**, and that
is a fact about browsers rather than about this stack: Keycloak marks its session
cookies `Secure`, and a browser stores one from a plain-HTTP origin only when the
host is literally `localhost` or a loopback address. `docker compose --env-file
tls.env up` terminates TLS at the same service name and fixes it.
[`keycloak/README.md`](keycloak/README.md) documents that profile, including the
one step only a human can take.

## One proof

`tools/list`, answered for two access tokens at the same endpoint. Priya Raman
consented to all three capabilities. Rafael Costa holds no deciding role, so the
authorization server declined `erp.decide` and never issued it — and the tool it
guards is **absent from the listing** rather than refused when called.

<!-- proof: derived from docs/transcripts/tools-list-for-two-tokens.txt -->
```
POST /mcp        Mcp-Method: tools/list
authorization:   Bearer eyJhbGciOiJSUzI1NiIsInR5cCIg…cp5Efun4ZJTg
                 sub    priya-raman
                 scope  erp.write erp.read erp.decide

    -> approve_requisition
    -> get_requisition
    -> list_requisitions
    -> record_invoice
    -> submit_requisition

POST /mcp        Mcp-Method: tools/list
authorization:   Bearer eyJhbGciOiJSUzI1NiIsInR5cCIg…hAiE4XNYOmXA
                 sub    rafael-costa
                 scope  erp.write erp.read

    -> get_requisition
    -> list_requisitions
    -> record_invoice
    -> submit_requisition
```
<!-- /proof -->

Both tokens were earned at a login screen, by the run that gates merges into this
repository. The block above is derived from the committed transcript and never
retyped; that transcript and the rest of the captured set are in
[`docs/transcripts/`](docs/transcripts/), verbatim, bearer tokens and all — they
were minted by a throwaway local realm, they expired five minutes after capture,
and that directory's README says why publishing them is not a leak.

## Where everything else is

Every directory holding something non-obvious carries its own README, and GitHub
renders it when you click in. What browsing will not show you:

- [`CONTEXT.md`](CONTEXT.md) — the ubiquitous language. Two vocabularies meet
  here, the protocol one and the purchase-to-pay one, and this is what keeps them
  apart.
- [`docs/adr/`](docs/adr/) — every architectural decision, with the options it
  refused and why. They are the argument this exhibit is made of, and the only
  place the reasoning lives.
- [`docs/normative-register.md`](docs/normative-register.md) — every `MUST`,
  `MUST NOT` and `SHOULD` this project does not simply follow: each deliberate
  departure, and each non-obvious reading. Nobody would find it by clicking
  around, and it is the strongest signal on this page.
- [`docs/decision-matrix/matrix.yaml`](docs/decision-matrix/matrix.yaml) — who
  may do what to which row, held as data and rendered into the tests, the seeded
  fixtures and a table beside it.
- [`docs/attack-suite/scenarios.yaml`](docs/attack-suite/scenarios.yaml) — named
  attacks, each citing the clause it defends and recording the exact deletion
  that would let it through. A test declares the row it falsifies, and a check
  holds the two in bijection.

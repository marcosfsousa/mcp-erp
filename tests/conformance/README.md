# `tests/conformance/` — the authorization code flow, wire and outbound

The proof map constraint `#1` calls primary: a real OAuth flow completing
against a running server. Every other suite here is handed a token; this one
**earns** one. A client that is registered nowhere in the realm identifies itself
by a document GitHub Pages serves, a Person logs in and consents, the code is
redeemed, and the token reaches a tool through the whole gate chain.

The only suite that reaches the network, and its preflight names external causes
first so an outage does not read as a regression.

Landed with [#46](https://github.com/marcosfsousa/mcp-erp/issues/46), which is
also when the `Authorization code flow` job started running it.

## The client is beside this directory, not inside it

`tests/conformance_client.py`, above the four test directories with `tokens.py`
and `rpc.py`, for the reason `tokens.py` states: shared tooling that lives in one
artifact's directory becomes that artifact's and gets copied by the next.

It is [ADR-0008](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md)'s
**one library surface with two entry points** — this suite imports it, and its
`__main__` block performs the flow from a command line.

ADR-0008 says *package* and this is one **module**, which is the same claim at
the size the thing turned out to be. What that sentence was drawing a line
against is two distributions with a version relationship between them — its
option 5, *"two packaging manifests… for a single constructor argument"* — and a
directory with an `__init__.py` would buy the word at the cost of splitting a
file nothing has yet asked to split. `tokens.py` sits beside it in the same
shape, library and `__main__` in one file, and the pair reads as a pair because
of it. The two differ by
**exactly one object**, and that is a property of the protocol package rather
than a choice: `mcp` 2.0.0's unified `Client` takes no authentication parameter,
so authentication attaches to the HTTP client underneath the transport.
`connect()` takes an `httpx2.Auth` and knows nothing else about it — `Flow`
earns a token through the hosted document, `Bearer` presents one `tokens.py`
minted. Mint versus earn is a constructor argument, not an architecture, and
`test_minting_and_earning_differ_by_exactly_one_object` is that claim as an
assertion rather than a diagram.

## The half of the client this suite cannot prove

`tests/test_conformance_client.py`, beside `tests/test_tokens.py` and Docker-free
for the same reason, carried by the same `Lint and types` job.

It holds the waits. Every request this suite makes is bounded by
`conformance_client.TIMEOUT`, and a long-lived `GET` stream underneath it is
deliberately **not** — a stream that is quiet is idle rather than stuck, and
[#86](https://github.com/marcosfsousa/mcp-erp/issues/86) was that distinction
being missing.

A flow cannot assert it in either direction, and against this server it is never
even reached — that constant's own docstring records which era is negotiated
here and why nothing opens such a stream under it. So the assertion is made
against a socket that answers with an open event stream and then says nothing,
which is the state no clock can name.

## The second module, and why a client-side clause is asserted here

`test_a_refusal_is_attributed_before_it_is_repeated.py` keeps the other half of
the attack suite's `mixup_iss_mismatch` row. The protocol package validates
RFC 9207 `iss` on the success path — but `AuthorizationCodeResult` requires a
`code`, a refused response carries an `error` and none, so a refusal can never be
handed over and the party that would attribute it never sees it. That leaves
`Flow._callback` as the only place the *"MUST NOT act on or display error,
error_description, or error_uri"* can be kept, and
[#78](https://github.com/marcosfsousa/mcp-erp/issues/78) is where it started
being kept.

It is here rather than in `tests/attack_suite/` because the client under test is
this directory's and that directory collects its declarations out of its own
source. It needs Keycloak and not GitHub Pages: the redirect it reads is a real
refusal from a real realm, handed to a flow that discovered the other one.

## Running it

```
docker compose up -d --wait
uv run pytest tests/conformance
```

Or watch one flow happen, which is the same code with a different caller:

```
uv run python tests/conformance_client.py --preflight
uv run python tests/conformance_client.py priya.raman
uv run python tests/conformance_client.py rafael.costa
```

The second pair is the interesting one. Priya Raman holds `approver` and is
granted every scope requested; Rafael Costa holds `invoice_clerk` and neither
deciding role, so `erp.decide` is declined and `approve_requisition` disappears
from the listing.

**The issuer has to resolve.** The protocol package follows a discovered
endpoint verbatim and has no rebasing hook of its own, so this client needs the
one line
[ADR-0005](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0005-the-authorization-server-is-a-dependency-not-a-deliverable.md)
priced:

```
127.0.0.1 keycloak
```

Without it, point the transport somewhere reachable — which moves the address
the requests go to and never the issuer they assert:

```
KEYCLOAK_BASE_URL=http://localhost:8081 uv run pytest tests/conformance
```

The `Authorization code flow` job adds the hosts line rather than setting the
variable, deliberately: a run that rebased nothing is the faithful one, and the
gate should be the faithful one.

**One assertion needs a cold boot.** Keycloak remembers a grant per Person and
per client, so *login and consent were both posted* is a claim about the first
flow of a boot. Continuous integration always is one — the database is in memory
and the realm re-imports on every start — which is what
[ADR-0012](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/adr/0012-the-token-names-a-capability-never-a-role.md)
means by *"deterministic rather than sometimes-remembered"*. A reader who has
already run the flow for that Person against the same container has a warm one;
the assertion says so in its own failure message.

## The preflight, and why it is a step rather than a fixture

ADR-0008's second mechanism, and half the reason this job is allowed to block.
Without it, Pages being unreachable and this server rejecting a valid flow
present identically as *the flow failed*. With it, an external cause fails a
**named step before our server has run at all**.

It asserts an HTTP `200` — redirects deliberately not followed, because the
`client_id` **is** the URL and a document served from somewhere else is a
different client wearing this one's identifier — and that the body hashes to
`public/clients/conformance/1.json`.

That digest is the half `Published documents are immutable` cannot see. That job
reads this repository's history and refuses a commit that rewrites a published
document; this reads what is **actually being served**, which is a different
question with a different failure.

## What the run answered, and what it therefore does not record

ADR-0012 left one thing open: Keycloak omits an unpermitted scope **silently**,
and RFC 6749 §3.3 puts a `MUST` on the authorization server to report the
narrowing in the `scope` response parameter. Whether it honoured that was
unverified, and the outcome was deliberately not pre-committed — a conformance
proof, or a normative register row.

**Measured on 26.7.1: it honours it.** Rafael Costa requests
`erp.read erp.write erp.decide`, the token carries `erp.read erp.write`, and the
token response carries `"scope": "erp.write erp.read"`. So the exhibit gains a
conformance proof and
[`docs/normative-register.md`](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/normative-register.md)
gains **no row**. There is no gap to record, and a register that recorded one
anyway would be worth less for it.

The reading is taken off the wire rather than out of the package's own model,
and that detail is load-bearing. RFC 6749 §5.1 lets an authorization server omit
the parameter when nothing was narrowed, and the package conformantly fills an
absent one in from what it requested — which erases exactly the distinction this
suite exists to observe. `Flow` wraps the auth flow and reads the token
response's own `scope` key as it passes.

**The behaviour is real but not general**, which the run also found. Keycloak
refuses an unentitled `offline_access` at the token endpoint outright rather than
omitting it from the grant. `conformance_client.GRANT_TYPES` carries that
finding and what this client does about it.

## One added call, and why it duplicates something twice proven

`approve_requisition`, presented with Priya Raman's **earned** token, is refused
`-31010`. `tests/matrix/` and `tests/wire/` both prove that refusal already, on a
token we minted for ourselves; this one uses a token a human consented to at a
login screen, which is the only path to it a reader cannot call circular. ADR-0014
§*The gating job performs the centrepiece* is where the duplication is argued,
and it also fixes an inconsistency the capture rule would otherwise have: the
beat's transcript now comes out of a run the merge gate protects.

The identifier it names is the one no row carries, and that is the assertion
rather than a shortcut. ADR-0006 fixes the gate order and the role step is ahead
of anything that reads a row, so a caller holding `erp.decide` and no deciding
role is refused before the resource is looked at. Naming a real fixture would
make this leg depend on a seeded database the `Authorization code flow` job does
not load; naming the absent identifier makes it depend on the order instead,
which is the property.

## It also writes three of the walkthrough's captured transcripts

ADR-0014 makes the walkthrough's wire exchanges **captured artifacts** — a run
writes them, the write-up includes them, and a check refuses a diff — and three
of the six beats need a token consented to at a login screen: the flow
completing, `tools/list` answered for two earned tokens, and the refusal above.

**This suite writes those three because it is the only thing that can.** Keycloak
remembers a grant per Person and client, so a second process performing the same
flows would post one form where these posted two, and the transcript would record
the difference. `tests/capture.py` writes the other three, which need no consent
screen and no ordering; `tests/transcripts.py` is what the two share, and
[`docs/transcripts/README.md`](https://github.com/marcosfsousa/mcp-erp/blob/main/docs/transcripts/README.md)
says what the mask covers and why the committed tokens are not secrets.

**Committing is not an assertion.** `transcripts.keep` rewrites a file only when
the masked forms differ, and the verdict is a `git status` in the job that ran
this. What this suite asserts is that each beat **found** its exchanges — a
selector that matched nothing would commit an empty transcript over a good one,
which is the one failure a diff check cannot see.

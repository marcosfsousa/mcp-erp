# ADR-0001: No off-the-shelf MCP client can run a modern-only server

- **Status:** Accepted
- **Date:** 2026-08-06
- **Ticket:** [#4 Survey the MCP client landscape](https://github.com/marcosfsousa/mcp-erp/issues/4)
- **Evidence:** [`docs/research/0004-mcp-client-landscape.md`](../research/0004-mcp-client-landscape.md)
- **Amended:** 2026-08-07 — terminology only, to match [`CONTEXT.md`](../../CONTEXT.md), which postdates this ADR and discourages the abbreviation this document used nine times. No finding, option or decision changed.
- **Amended:** 2026-08-11 — substantive, by [#8](https://github.com/marcosfsousa/mcp-erp/issues/8). The conformance client is **no longer a legitimate cut candidate**. Recorded in [ADR-0008](0008-the-run-is-over-the-wire-and-the-token-is-the-only-seam.md) at the time and back-amended here 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12). See *Consequences*. No decision here is reversed.

## Question

Can a client the reader already has complete an OAuth authorization code flow against a server that speaks MCP `2026-07-28` as specified?

This gates *Decide what performs the run* ([#8](https://github.com/marcosfsousa/mcp-erp/issues/8)). If yes, the circularity in the self-written-conformance-client option evaporates and the hedge is cheap. If no, the conformance client is promoted from deliverable to load-bearing dependency.

## Findings

`2026-07-28` removes the `initialize` handshake outright. This is not a compatible extension — it partitions the ecosystem into two **eras** the spec names *legacy* and *modern*, and the spec's own compatibility matrix rules the legacy-client → modern-server case **"Fails. Legacy clients have no fall-forward mechanism."** That makes the question binary rather than gradual.

Exactly two off-the-shelf tools clear the bar, **both requiring a non-default setting**:

| | How | Verified |
| --- | --- | --- |
| MCP Inspector 2.1.0 | Server Settings → Protocol Era → **Modern** (default is Legacy) | published tarball |
| Claude Code 2.1.223 | `MCP_PROTOCOL_NEGOTIATION=auto` (undocumented) | installed binary, independently re-verified |

Claude Code bundles the modern client and already hosts a Client Identity Metadata Document, but HTTP negotiation is gated behind the server-controlled flag `tengu_mcp_protocol_negotiation_http`, default `false`. The env var overrides it. Neither the flag nor the var is documented.

Everything else — Claude Desktop, VS Code, Cursor, Windsurf, Zed, JetBrains, `mcp-remote`, both `mcp-cli`s — is legacy-era and fails. Separately, **no framework or LLM-vendor integration performs an authorization code flow at all** (LangChain, OpenAI Agents SDK, OpenAI Responses hosted `mcp` tool, `google-genai`, Anthropic's own API connector are static-token consumers that delegate consent to the calling application).

Two premise corrections fall out (see *Consequences*): the prior revision is **2025-11-25**, not 2025-06-18, and that is where the **Client Identity Metadata Document was introduced** — `2026-07-28` only *deprecated DCR*.

## Options considered

1. **Rely on an off-the-shelf client.** Viable only via a debugging tool or a hidden env var. Neither reads as "here is a real client using this server," and neither exercises a Client Identity Metadata Document against a self-hosted identity unless the operator first hosts one.
2. **Conformance client as load-bearing.** Rejected — the premise is false. The server is demonstrable today, so the client is not the only thing that can run it.
3. **Conformance client as demonstrator.** A thin harness over `@modelcontextprotocol/client@2.0.0` (or `mcp` 2.0.0), which already implements the whole wire format and the whole OAuth stack.

## Decision

**The conformance client is neither uncuttable nor merely a hedge — it is a demonstrator.** It stays in scope, scoped as a thin harness over an SDK plus a hosted Client Identity Metadata Document plus assertions, not a protocol implementation. Its justification is no longer "nothing else can run the server" but "nothing else exercises that document end-to-end, runs headlessly, or asserts on the wire."

The binding decision on *what performs the run* remains #8's to make; this ADR removes the false constraint that was forcing its hand.

## Consequences

*Amended 2026-08-11 by [#8](https://github.com/marcosfsousa/mcp-erp/issues/8), back-amended 2026-08-18 by [#12](https://github.com/marcosfsousa/mcp-erp/issues/12).* The cut-candidate clause below is **withdrawn**. Packaging the client as one library with two entry points means cutting it removes the runnable entry point and the hosted document only — the transport, the calls and the assertions stay, because the suites import them. The saving fell to about a day while the value rose. It is **not** on the cut list, and map note `#9` is unchanged.

**Cost.** The conformance client survives the cut list on weaker grounds than "load-bearing," so it is now a legitimate cut candidate — a change to the note-9 cut order that #8 should weigh. It also needs a publicly-reachable HTTPS document: a Client Identity Metadata Document `client_id` is a URL the authorization server fetches, so a `localhost` client cannot self-host its own identity.

**The highest-leverage consequence is not about the client.** Making the server **dual-era** moves the audience from "Inspector plus an env var" to every MCP client in existence, and the TypeScript SDK server does it by default (`createMcpHandler` defaults to `legacy: 'stateless'`). Deferred to the build tickets, but flagged here as the cheapest available leverage.

Server-side requirements this research pins down:

- **Advertise `client_id_metadata_document_supported: true`**, or no client ever takes that path.
- **Keep `registration_endpoint`.** Supporting only Client Identity Metadata Documents locks out most of the ecosystem. Claude Desktop additionally requires `"none"` in `token_endpoint_auth_methods_supported` before selecting one.
- **Do not bind ERP context at connection time** — there is no handshake and no session id. Already consistent with the map's stateless core.
- **Return a helpful error to `initialize`**, naming supported versions; the spec notes this may be the only diagnostic a legacy client can surface.
- **Decide 401-vs-header-validation ordering.** Unspecified by the spec, and it determines whether a legacy client completes a full, successful, pointless OAuth dance before failing.

**Attack-suite input:** the negative paths no shipped client will exercise — `-32020` `HeaderMismatch`, `-32022` `UnsupportedProtocolVersionError` with a `supported` list, `405` on `GET`/`DELETE`, `403` on bad `Origin`, `401` carrying `WWW-Authenticate` with both `resource_metadata` and `scope`.

**Caveat.** Nothing was executed against a live server. Every verdict derives from source, shipped binaries, and normative spec text. Revision support is moving weekly — Inspector 2.1.0 and C# 2.1.0 both shipped 2026-08-05. Re-check before relying on any "not supported" claim.

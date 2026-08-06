# The MCP client landscape, and whether any of it can OAuth against a 2026-07-28 server

Research for [issue #4](https://github.com/marcosfsousa/mcp-erp/issues/4). All findings dated **2026-08-06**. Revision `2026-07-28` was published nine days earlier, so every "which revision does it speak" answer below is a snapshot with a short half-life — the version checked is named in every case.

Evidence is labelled: **[code]** = read from source, a shipped binary, or a published package; **[docs]** = vendor documentation only; **[?]** = could not determine. Nothing here was executed against a live server — all behavioural claims are derived from source plus the normative spec.

---

## Verdict

**Qualified yes — but only just, and not by the clients that would make the exhibit land.**

Two off-the-shelf tools can complete an OAuth authorization code flow against a server that speaks only `2026-07-28`, and **both need a non-default setting flipped**:

- **MCP Inspector 2.1.0** (published 2026-08-05). Set **Server Settings → Protocol Era → Modern**; the default is Legacy. OAuth works via DCR out of the box, or CIMD if you supply your own publicly-hosted metadata URL. **[code]**
- **Claude Code 2.1.223**. The modern-era client is compiled in and already does CIMD, but HTTP version negotiation is **gated off by default** behind a server-controlled feature flag. The undocumented env var `MCP_PROTOCOL_NEGOTIATION=auto` turns it on. **[code]**

**Everything else fails.** Claude Desktop, VS Code, Cursor, Windsurf, Zed, JetBrains, `mcp-remote`, every `mcp-cli`, and every framework/LLM-vendor integration is still legacy-era. This is not a graceful degradation: per the spec's own compatibility matrix a legacy client against a modern-only server **fails**, and "legacy clients have no fall-forward mechanism." It sends `initialize`, gets `400`, and stops.

A second, independent finding cuts across all of this: **no framework or LLM-vendor MCP integration performs an authorization code flow at all** — LangChain, the OpenAI Agents SDK, the OpenAI Responses hosted `mcp` tool, Google's `google-genai`, and Anthropic's own API MCP connector are all static-token consumers that explicitly delegate consent to your application. For those, the revision question never even arises.

### What this means for the conformance client

The decision rule in the issue was binary; the honest answer is not. The server **is** runnable and demonstrable today, so the conformance client is **not load-bearing in the strict sense** — it is not the only thing that can run the server. But calling it "a cheap hedge" undersells it, for three reasons:

1. The two clients that work are a **debugging tool** and a **hidden environment variable**. Neither is a satisfying "here is a real client using this server" exhibit.
2. **Nothing off the shelf exercises CIMD end-to-end against a self-hosted server** without the operator first hosting their own metadata document at a public HTTPS URL. CIMD is the most distinctive part of this design, and it is precisely the part no existing client will demonstrate for free.
3. Inspector 2.1.0 pins a **beta** SDK that predates a fix for 401-on-probe handling (see *Partial interop*), so even the one working tool has a known rough edge against an authenticated modern server.

**Recommendation: build it, but scope it as a demonstrator rather than a rescue**, and reuse `@modelcontextprotocol/client@2.0.0` (or `mcp` 2.0.0 in Python), which already implements the entire wire format and the entire OAuth stack including CIMD.

**The highest-leverage design decision this research surfaces is not about the client at all:** make the server **dual-era**. Accepting both `initialize` and modern per-request `_meta` on the same endpoint moves the audience from "Inspector plus an env var" to "every MCP client in existence," and the TypeScript SDK's server package does it by default (`createMcpHandler` defaults to `legacy: 'stateless'`). The cost is low; the difference in what the exhibit can claim is large.

---

## The premise, corrected

The issue's framing was right about the destination and wrong about two details worth fixing before anything else.

**1. The prior revision is `2025-11-25`, not `2025-06-18`.** There was an intermediate revision, and it matters for attribution: `2025-11-25` is where **CIMD was introduced** (SEP-991) as a recommended registration mechanism, alongside OIDC Discovery support and incremental scope consent. `2026-07-28` then went further and **deprecated DCR outright**. So "CIMD preferred over DCR" is not new in `2026-07-28` — what is new is DCR's formal deprecation. Several clients therefore already speak CIMD *without* speaking `2026-07-28`.

**2. "Stateless core, header-based routing" substantially understates the break.** `2026-07-28` removes the `initialize` / `notifications/initialized` handshake entirely. This is not a compatible extension — it partitions the ecosystem into two **eras** the spec itself names *legacy* and *modern*. Version negotiation moved from a handshake to a per-request declaration. This is the single most important fact for this project, and it is what makes the client question binary rather than gradual.

Everything else in the premise checks out: statelessness, header-based routing, and CIMD-over-DCR are all real and all in `2026-07-28`.

---

## What revision 2026-07-28 actually requires of a client

This is the bar an off-the-shelf client has to clear.

### Wire format

- **No handshake.** There is no `initialize`. Every request independently declares its version in `_meta` under `io.modelcontextprotocol/protocolVersion`, and carries `io.modelcontextprotocol/clientCapabilities`; clients SHOULD also send `io.modelcontextprotocol/clientInfo`.
- **`MCP-Protocol-Version` is MUST on every POST**, and its value **MUST match** the `_meta` field in the body. Mismatch → `400` + JSON-RPC `-32020` `HeaderMismatch`.
- **`Mcp-Method` is REQUIRED on all requests**; **`Mcp-Name` is REQUIRED** on `tools/call`, `resources/read`, `prompts/get` (mirroring `params.name` / `params.uri`). Non-ASCII values use a `=?base64?…?=` sentinel. This is the premise's "header-based routing": it exists so intermediaries can route without parsing bodies, and the server **MUST** cross-validate header against body.
- **`Mcp-Session-Id` is gone.** Servers must not mint or echo it. `GET`/`DELETE` on the MCP endpoint → `405`.
- **SSE resumability is gone** — no `Last-Event-ID`, no event IDs. A broken stream loses the request; the client MUST re-issue with a new request ID.
- **`server/discover` is a mandatory server RPC** but **optional for clients** to call. It returns `supportedVersions`, `capabilities`, `instructions`.
- **Every result carries `resultType`** (`"complete"` or `"input_required"`). Server-to-client interaction (sampling, elicitation, roots) is no longer a server-initiated request — it is **MRTR**: the server returns an `InputRequiredResult`, and the client retries the original request with `inputResponses`.
- **SSE response mode stays mandatory for clients**: a POST may be answered with `application/json` *or* `text/event-stream`, and "the client **MUST** support both."
- Clients **MUST** support `x-mcp-header` (mirroring annotated tool parameters into `Mcp-Param-*`) and **MUST** reject tool definitions violating its constraints.

### Version negotiation and forward compatibility

There is no handshake to negotiate in. A server that does not support the requested version returns `400` + `-32022` `UnsupportedProtocolVersionError` with a `supported` list; the client SHOULD pick from it and retry.

The spec's [compatibility matrix](https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning) is blunt about the case this project lands in:

> | Client | Server | Outcome |
> | --- | --- | --- |
> | Legacy | Modern | **Fails.** … Legacy clients have no fall-forward mechanism. |

On HTTP a legacy client's `initialize` POST lacks the required headers and is rejected `400` per server validation. Notably, the spec advises a modern-only server to **name its supported versions in any error it returns to an `initialize` request**, because "this message may be the only diagnostic they can surface to users." That is a cheap, concrete server-side requirement worth implementing.

### Authorization

The bar is high, and mostly inherited from `2025-11-25`. `2026-07-28` additions marked ★:

| Requirement | Level |
| --- | --- |
| RFC 9728 Protected Resource Metadata discovery | Client **MUST** use it for AS discovery |
| RFC 8414 **and** OIDC Discovery 1.0 | Client **MUST** support both |
| PKCE (S256) | Required via OAuth 2.1 |
| RFC 8707 `resource` on **both** authorize and token requests | Client **MUST**, "regardless of whether authorization servers support it" |
| CIMD (`draft-ietf-oauth-client-id-metadata-document-00`) | Client **SHOULD** support |
| RFC 7591 DCR | **MAY** — ★ formally **deprecated**, retained for back-compat |
| ★ RFC 9207 `iss` validation before redeeming the code | Client **MUST** (four-row decision table) |
| ★ `application_type` on DCR requests (SEP-837) | Client **MUST** |
| ★ Credentials keyed by AS `issuer`; re-register on AS change (SEP-2352) | Client **MUST** |
| `Authorization: Bearer` on **every** request | **MUST** |

Registration priority for a fully-featured client: **pre-registered → CIMD (if the AS advertises `client_id_metadata_document_supported`) → DCR (if `registration_endpoint`) → prompt the user.**

**The CIMD wrinkle that shapes this project.** A CIMD `client_id` is an **HTTPS URL with a path component**, hosting a JSON document whose `client_id` field equals that URL exactly; the authorization server fetches it. A client on `localhost` therefore **cannot self-host its own `client_id`** — the document must live somewhere publicly reachable over HTTPS. This is why CIMD in a local client is always either "bring your own metadata URL" (Inspector) or "the vendor publishes one for you" (Claude Code, which ships `https://claude.ai/oauth/claude-code-client-metadata`). Any conformance client written here faces the same constraint and will need a hosted document — GitHub Pages or the server's own domain.

---

## Client-by-client findings

**Read the table with one thing in mind:** the "auth flow" and "revision" columns are independent, and almost every client here has a perfectly competent OAuth implementation. What they lack is the *era*. A client doing flawless CIMD + PKCE + RFC 8707 never reaches the point of spending its token if it opens with `initialize`.

| Client | Kind | Revision (checked 2026-08-06) | Sends `MCP-Protocol-Version` | Auth code flow | Identity mechanism | Streamable HTTP | SSE response mode | Forward-compat behaviour |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **MCP Inspector 2.1.0** | Tool | legacy default, **2026-07-28 selectable** | Yes (modern mode) | **Yes** | static / DCR / **CIMD** | Yes | Yes | Clean — era selector, handles `-32022` |
| **Claude Code 2.1.223** | Client | legacy default, **2026-07-28 gated** | Yes (auto mode) | **Yes** | DCR / **CIMD** / static | Yes | Yes | Modern-capable, degrades to legacy |
| **Claude Desktop / claude.ai** | Client | ≤ 2025-11-25 | Yes | **Yes** | DCR / CIMD / pre-reg / static | Yes (Anthropic-side) | [?] | **Fails** — no fall-forward |
| **VS Code 1.132 / Copilot Chat** | Client | **2025-11-25** | **No** — auth discovery only | **Yes** | DCR (CIMD [?]) | Yes | Yes | **Fails** |
| **Cursor 3.14.27** | Client | **2025-11-25** | Yes | **Yes** | DCR / static (**CIMD dormant**) | Yes | Yes | **Fails** — clean named error |
| **Windsurf / Devin Desktop 3.6.27** | Client | ≤ 2025-11-25 [docs] | [?] | Yes [docs] | DCR [docs] | Yes | [?] | **Fails** |
| **Zed 1.14.2** | Client | **2025-11-25** | Yes | Yes | DCR | Yes | Yes | **Fails** |
| **JetBrains AI Assistant / Junie** | Client | **2025-03-26** | [?] | Yes [docs] | DCR [docs] | Yes | [?] | **Fails** |
| **`mcp-remote` 0.1.38** | Shim | 2025-11-25 (frozen) | Yes | Yes | **DCR only** | Yes | Yes | **Fails**, dormant 6 months |
| **`chrishayuk/mcp-cli` 0.20.1** | Client | 2025-06-18 | Yes | Yes | DCR only | Yes | Yes | **Fails** |
| **`@wong2/mcp-cli` 2.0.0** | Client | 2025-11-25 | Yes | Yes | DCR only | Yes | Yes | **Fails** |
| **TS SDK v2** `@modelcontextprotocol/client@2.0.0` | **Library** | **2026-07-28** + legacy | Yes | **Yes** | static / **CIMD** / DCR | Yes | Yes | Best in class — `auto`/`pin`/`legacy` |
| **TS SDK v1** `@modelcontextprotocol/sdk@1.30.0` | **Library** | 2025-11-25 | Yes | Yes | DCR / CIMD | Yes | Yes | Opaque `SdkHttpError` |
| **Python SDK `mcp` 2.0.0** | **Library** | **2026-07-28** + legacy | Yes | **Yes** | **CIMD** / DCR | Yes | Yes | `mode="auto"` default |
| **C# SDK 2.1.0** | **Library** | **2026-07-28** + legacy | Yes | **Yes** | **CIMD** / DCR | Yes | Yes | Era-aware |
| **Go SDK v1.7.0** | **Library** | **2026-07-28** (needs `Stateless=true`) | Yes | **Yes** | **CIMD** / DCR / pre-reg | Yes | Yes | Era-aware |
| **Rust SDK `rmcp` 3.1.1** | **Library** | 2026-07-28 **opt-in** | Yes | **Yes** | **CIMD** / DCR | Yes | Yes | `LATEST` still 2025-11-25 |
| **Ruby SDK 1.1.0** | **Library** | server-side only | n/a | n/a | n/a | Yes | Yes | Client lacks `server/discover` |
| **Java / Kotlin / Swift SDKs** | **Library** | ≤ 2025-11-25 | Yes | Varies | DCR | Yes | Yes | **Not started** |
| **LangChain / OpenAI Agents / google-genai / Anthropic MCP connector** | **Library** | ≤ 2025-11-25 | Yes | **No — static token only** | n/a | Yes | Yes | **Fails** |

### MCP Inspector 2.1.0 — the one tool that works

Published **2026-08-05**; `2.0.0` landed **2026-07-28**, spec day. v2 is a full rewrite shipping a web UI, a CLI (`--cli`) and a TUI. **[code]**

It speaks both eras, selected per-server. The web UI exposes **Server Settings → Options → "Protocol Era"**, whose own help text reads: *"Legacy uses the 2025-11-25 initialize handshake; Auto probes server/discover and falls back to legacy; Modern pins the 2026-07-28 sessionless protocol. Defaults to Legacy — debugging tools should not auto-probe."* The default really is legacy (`core/mcp/types.ts`: `DEFAULT_PROTOCOL_ERA = "legacy"`), so **an untouched Inspector will not connect to a modern-only server.** Selecting Modern pins `2026-07-28`. **[code]**

OAuth is settings-driven rather than the v1 "Guided OAuth Flow" tab, which was removed deliberately (the v2 design notes list "disparate OAuth flows" as a v1 problem to be replaced with "a single auth flow mechanism"). All three identity mechanisms are modelled explicitly — `core/auth/types.ts` declares `type OAuthClientRegistrationKind = "static" | "dcr" | "cimd"` — and the negotiated kind is displayed in Connection Info. **[code]**

Two details matter for this project:

- **DCR is the default** and registers with `application_type: "native"` so loopback redirect URIs are accepted (SEP-837). Inspector's own UI text: *"If the server still rejects Dynamic Client Registration, use a Client ID Metadata Document (below) or a preregistered client instead."*
- **CIMD requires you to host the document.** The UI states: *"The metadata document must be served over HTTPS and list this redirect URI: `http://localhost:6274/oauth/callback`"*, with a field labelled *"Public HTTPS URL of your OAuth client metadata JSON document."* The CLI equivalent is `--client-metadata-url <url>`. Inspector does **not** host one for you. **[code]**

Verified independently by extracting the published tarball: 45 occurrences of `2026-07-28`, `server/discover`, `io.modelcontextprotocol/protocolVersion`, and `client_id_metadata_document_supported` are all present in the shipped bundles.

### Claude Code 2.1.223 — modern-capable, gated off

This is the most decision-relevant finding in the report, and it is not documented anywhere.

I inspected the **installed binary** at `~/.local/share/claude/versions/2.1.223` (build `2026-08-05T18:12:31Z`). It **bundles the MCP TypeScript SDK v2** — the modern `_meta` envelope validator, error code `-32020`, `resultType: "input_required"`, `subscriptions/listen`, and 55 occurrences of `server/discover` are all present. **[code]**

But capability is not behaviour. The negotiation mode is chosen per transport by a resolver function:

```js
function JNs(e){
  let t = te.MCP_PROTOCOL_NEGOTIATION,
      r = (t==="legacy"||t==="auto") ? t : void 0;
  if (t!==void 0 && r===void 0) T(`MCP_PROTOCOL_NEGOTIATION=${t} is invalid; expected 'legacy' or 'auto' — ignoring`,{level:"warn"});
  if (r==="legacy") return {mode:"legacy"};
  let n={timeoutMs:WA()}, o={timeoutMs:Math.min(Os_,Math.floor(WA()/3))};
  if (r==="auto"){ if(!$s_.has(e)) return {mode:"legacy"};
                   return e==="stdio" ? {mode:"auto",probe:o} : {mode:"auto",probe:n}; }
  switch(e){
    case "http":           return Je("tengu_mcp_protocol_negotiation_http",  !1)===!0 ? {mode:"auto",probe:n} : {mode:"legacy"};
    case "claudeai-proxy": return Je("tengu_mcp_protocol_negotiation_claudeai",!1)===!0 ? {mode:"auto",probe:n} : {mode:"legacy"};
    case "stdio":          return Je("tengu_mcp_protocol_negotiation_stdio", !1)===!0 ? {mode:"auto",probe:o} : {mode:"legacy"};
    case "ccr-proxy": case "sse": case "ws": case "ide":
    case "in-process": case "sdk-control": return {mode:"legacy"};
  }
}
// $s_ = new Set(["http","claudeai-proxy","ccr-proxy","stdio"])
```

Reading this out:

- **Default for `http` is `{mode:"legacy"}`**, because the feature gate `tengu_mcp_protocol_negotiation_http` defaults to `false` and is server-controlled. So out of the box Claude Code opens with `initialize` and **fails against a modern-only server**.
- **`MCP_PROTOCOL_NEGOTIATION=auto` overrides the gate** for `http` (which is in the `$s_` allowlist), yielding `{mode:"auto"}` — the client probes `server/discover` and negotiates the modern era. This is the switch that makes Claude Code work.
- `sse`, `ws`, `ide`, `in-process`, `sdk-control` are **hard-wired legacy** and cannot be overridden at all.
- The env var is **not documented** — it does not appear on the [settings page](https://code.claude.com/docs/en/settings), and `CHANGELOG.md` (through 2.1.223) contains **zero** mentions of `2026-07-28`, `stateless`, or `server/discover`.

Corroborating the legacy default: the OAuth discovery helpers default their outbound `MCP-Protocol-Version` header to `MPe`, and `MPe = "2025-11-25"`. The claude.ai proxy path likewise pins `"MCP-Protocol-Version": Ivo` with `Ivo = "2025-11-25"`. **[code]**

**A correction worth recording.** A parallel line of investigation read the array `ma_ = [RUu, Ivo, "2025-06-18", …]` (where `RUu = "2026-07-28"`, `Ivo = "2025-11-25"`) as a client preference list showing 2026-07-28 was preferred. It is not. `ma_` has exactly one use site — `function ha_(e){ let t = ma_.find(r=>r===e); return t===undefined ? Ae("other") : ge(t) }` — a mapper that normalises a negotiated version string into a telemetry enum. It never reaches the wire. The resolver above is authoritative.

**OAuth is genuinely complete and era-independent.** PKCE S256, RFC 8707 `resource` on both authorize and token requests, and RFC 9728 PRM discovery with RFC 8414 fallback (overridable via `oauth.authServerMetadataUrl`). CIMD landed in **v2.1.81** — *"Updated MCP OAuth to support Client ID Metadata Document (CIMD / SEP-991) for servers without Dynamic Client Registration."* **[code + docs]**

Two CIMD specifics this project can exploit:

- Claude Code's default `client_id` is **`https://claude.ai/oauth/claude-code-client-metadata`**, hard-coded. I fetched it live today (HTTP 200): it is a valid, self-referential CIMD document declaring `redirect_uris: ["http://localhost/callback","http://127.0.0.1/callback"]` and `token_endpoint_auth_method: "none"`.
- It is **overridable**: the provider's `clientMetadataUrl` getter returns `process.env.MCP_OAUTH_CLIENT_METADATA_URL` when set, logging *"Using CIMD URL from env"*. So a test client identity can be substituted without touching Anthropic's document.

CIMD is selected only when the AS advertises `client_id_metadata_document_supported`; otherwise it falls back to DCR silently. **The server must advertise that flag or Claude Code will never exercise the CIMD path.**

### Claude Desktop / claude.ai connectors — legacy, and architecturally remote

Remote servers are supported natively as "custom connectors" (Settings → Connectors), on free, Pro, Max, Team and Enterprise plans, with free users limited to one. **[docs]**

Two things make it a poor fit for this exhibit regardless of revision:

- **Anthropic's infrastructure is the HTTP client**, not your machine: connectors "run on Anthropic's infrastructure and reach your server over the public internet." A localhost dev server is unreachable; you need a tunnel or a deployment.
- **The documented auth-spec ceiling is 2025-11-25** — connector docs state support for "the 2025-03-26, 2025-06-18, and 2025-11-25 auth specifications", still describe the `initialize` handshake with `clientInfo`, and never mention `server/discover` or the new headers. No Desktop changelog entry (through v1.25927.0, 2026-08-04) references `2026-07-28`. **[docs]**

Auth itself is strong: authorization code only (`client_credentials` explicitly unsupported), PKCE S256, RFC 8707 `resource`, RFC 9728 PRM required — and it selects among `oauth_dcr`, `oauth_cimd`, Anthropic-held pre-registered credentials, and user-supplied static credentials. CIMD is chosen only when the AS advertises **both** `client_id_metadata_document_supported: true` **and** `"none"` in `token_endpoint_auth_methods_supported` — a stricter condition than the spec's, worth honouring on the server. Callback is `https://claude.ai/api/mcp/auth_callback`. **[docs]**

The only timing statement Anthropic has published is *"Support is rolling out across Claude products soon"* — undated, and already behind reality for Claude Code.

### VS Code / GitHub Copilot Chat — legacy, confirmed in source

`src/vs/platform/mcp/common/modelContextProtocol.ts:43` on `main` today:

```ts
export const LATEST_PROTOCOL_VERSION = "2025-11-25";
```

The same constant appears in the bundled Copilot extension at `extensions/copilot/src/extension/common/modelContextProtocol.ts:43`. A repository-wide code search for `2026-07-28` across `microsoft/vscode` returns **0 results**, against 8 files matching `"2025-11-25"`. VS Code is squarely legacy-era and **fails** against a modern-only server. **[code]**

**It also does not send `MCP-Protocol-Version` on JSON-RPC POSTs.** The header appears exactly **once** in the entire repository — `src/vs/workbench/api/common/extHostMcp.ts:814`, inside the `sameOriginHeaders` passed to `createAuthMetadata()`, i.e. only on OAuth metadata-discovery fetches after a 401. Ordinary MCP requests carry no protocol-version header at all. That has been a spec requirement since `2025-06-18`, so this is a live conformance gap in the most widely deployed MCP client, and worth knowing about if the server ever keys behaviour off the header. **[code]**

Streamable HTTP and the SSE response mode are supported, and there is a documented OAuth story using DCR. Whether VS Code implements CIMD is **[?]**: `client_id_metadata_document_supported` does appear in `src/vs/base/common/oauth.ts` and `mainThreadAuthentication.ts`, but those are the generic VS Code authentication stack rather than the MCP client, and I did not trace whether the MCP path reaches them.

### Zed — legacy, confirmed in source

`crates/context_server/src/types.rs:11`:

```rust
pub const LATEST_PROTOCOL_VERSION: &str = "2025-11-25";
```

with `VERSION_2024_11_05`, `VERSION_2025_03_26`, `VERSION_2025_06_18` alongside and an acceptance check `matches!(version, VERSION_2025_06_18 | LATEST_PROTOCOL_VERSION)`. A repo-wide search for `2026-07-28` returns **0 results**. Legacy-era; **fails**. **[code]**

Zed's only forward motion is an unreviewed **draft PR (#61625)** toward the modern era. Nothing has shipped.

### Cursor 3.14.27 — closed source, but verified from shipped binaries

Cursor turns out to be checkable despite being closed-source. Three shipped artifacts — the official `.deb` (desktop **3.14.27**, built 2026-08-04), the `cursor-agent` CLI (2026.08.04), and the `@cursor/sdk` npm tarball — all bundle **`@modelcontextprotocol/sdk` 1.25.1**, whose `src/types.ts:4` reads `LATEST_PROTOCOL_VERSION = '2025-11-25'`. **Zero occurrences of `2026-07-28`** in any of the three. It still opens with `initialize`, still uses `Mcp-Session-Id`, and has no `server/discover`, `Mcp-Method` or `Mcp-Name`. **[code]**

The sharpest datum: **`@cursor/sdk` 1.0.26 was published `2026-07-28T21:24:55Z`** — hours after the revision shipped — and still pins `2025-11-25`.

Two things Cursor does better than its reputation, both invisible in its docs:

- It **does send `mcp-protocol-version`** on every request (`_commonHeaders()`), which makes VS Code the only client of the five that omits it.
- Its **OAuth stack is the most complete of the closed-source clients**: PKCE S256 (it bundles `pkce-challenge@5.0.0`), RFC 9728 PRM discovery *and* `resource_metadata=` parsing from `WWW-Authenticate`, RFC 8707 resource indicators with response validation, DCR, plus a static-credentials escape hatch. The bundled SDK's CIMD branch exists but is **inert** — nothing Cursor-side ever supplies `clientMetadataUrl`.

Forward-compat is a **clean named error** *if* the server answers `initialize`: `Server's protocol version is not supported: 2026-07-28`. Against a pure modern server with no `initialize` handler it degrades to a generic connection error — **[?]**, not observed live.

Two caveats worth carrying: Cursor's changelog **stopped labelling versions after 3.11 (2026-07-10)**, and its public issue tracker is closed (`getcursor/cursor` now redirects to `cursor/cursor` with issues disabled). So "no planned `2026-07-28` support" for Cursor is *absence of evidence*, not evidence of absence — and forum.cursor.com was not searched.

### Windsurf and JetBrains — docs-level only

Neither could be verified from code. **JetBrains AI Assistant / Junie** appears to be on **`2025-03-26`** — the oldest in the table by a wide margin. **Windsurf**, now shipping as **Devin Desktop 3.6.27**, is **[?]** on revision, header behaviour and SSE response handling; it documents remote MCP over Streamable HTTP with DCR-based OAuth. Both **fail** against a modern-only server on the same reasoning as the rest, but that conclusion is inference from the era model rather than an observed result.

### `mcp-remote` — dormant, and structurally incapable

**0.1.38, published 2026-02-05.** Last commit the same day; ~147 open issues/PRs; **zero commits in six months**; still ~487k downloads/week. **[code]**

It bundles `@modelcontextprotocol/sdk@1.25.3` into `dist/`. Inspection of the published tarball found protocol strings from `2024-10-07` through `2025-11-25`, `mcp-session-id`, and **zero** occurrences of `Mcp-Method`, `Mcp-Name`, `server/discover`, or `io.modelcontextprotocol/protocolVersion`.

Its OAuth is good for its era — RFC 9728 PRM, PKCE S256, RFC 8707 `resource`, browser open with a loopback callback — but it is **DCR only**: its `NodeOAuthClientProvider` never sets `clientMetadataUrl`, leaving the bundled SDK's CIMD branch unreachable dead code.

**It cannot work against a modern-only server.** It POSTs a headerless `initialize`, which the spec requires be rejected `400`; its transport-fallback logic only handles `404`/`405`, so it dies before auth is ever attempted. Its own README already advises dropping it once your client supports remote auth natively — which is now true of Claude Code and VS Code.

### CLI clients

- **`chrishayuk/mcp-cli` 0.20.1** (2026-07-22) — actively developed but capped at **2025-06-18** via `chuk-mcp`. Browser OAuth + PKCE + RFC 8707 + DCR; no CIMD. Cannot connect. **[code]**
- **`@wong2/mcp-cli` 2.0.0** (2026-05-12) — SDK `^1.29.0`, so a **2025-11-25** ceiling. Browser OAuth, DCR only. Cannot connect. **[code]**
- **`mark3labs/mcphost`** — repo **archived**; its `auth login` targets the Anthropic API, not MCP servers. **`f/mcptools`** — last release 2025-05-05, stuck on 2025-03-26, static headers only.

### Official SDKs — libraries, not clients

These require writing code, so none of them answers "can a reader already connect?". They answer "what can the conformance client stand on?", and the answer is: a lot.

| SDK | Tier | Latest | Date | 2026-07-28 |
| --- | --- | --- | --- | --- |
| TypeScript (`@modelcontextprotocol/{core,client,server}`) | 1 | **2.0.0** | 2026-07-27 | Released (v2 line only) |
| Python (`mcp`) | 1 | **2.0.0** | 2026-07-28 | Released |
| C# (`ModelContextProtocol`) | 1 | **2.1.0** | 2026-08-05 | Released |
| Go | 1 | **v1.7.0** | 2026-07-28 | Released |
| Rust (`rmcp`) | 2 | **3.1.1** | 2026-08-05 | Released, **opt-in** |
| Ruby (`mcp`) | 2 | 1.1.0 | 2026-08-01 | **Server only** |
| Kotlin | 3 | 0.15.0 | 2026-07-28 | In progress |
| Java | 2 | v2.0.0 | 2026-06-11 | **Not started** |
| Swift | 3 | 0.12.1 | 2026-05-07 | Not started |

All four Tier 1 SDKs shipped on time, as the GA post claimed. The [tiering policy](https://modelcontextprotocol.io/community/sdk-tiers) explains the tail: Tier 1 must ship before a spec release, Tier 2 gets six months, Tier 3 has no timeline commitment.

**TypeScript v2** is the most relevant. Key details **[code]**:

- The published `@modelcontextprotocol/core@2.0.0` contains `FIRST_MODERN_PROTOCOL_VERSION = "2026-07-28"`, `SUPPORTED_MODERN_PROTOCOL_VERSIONS = [FIRST_MODERN_PROTOCOL_VERSION]`, and `MODERN_WIRE_REVISION = "2026-07-28"`, kept **deliberately separate** from the legacy `LATEST_PROTOCOL_VERSION = "2025-11-25"` so "adding a revision here can never leak a modern version string into a 2025-era handshake."
- The client emits `MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name` and `Mcp-Param-*`, gated on the outgoing request carrying the modern `_meta` envelope, with the `=?base64?…?=` sentinel encoding. `Mcp-Session-Id` is only ever populated by a legacy handshake, so it correctly never appears in the modern era.
- Auth implements the complete stack: CIMD (conditional on `client_id_metadata_document_supported`), DCR fallback with `application_type`, PKCE S256, RFC 8707, RFC 9728, RFC 8414 + OIDC, RFC 9207 `iss` validation, SEP-2352 issuer binding, and insufficient-scope step-up.
- **Its default negotiation mode is `legacy`.** `DEFAULT_VERSION_NEGOTIATION_MODE = 'legacy'`; you must pass `versionNegotiation: { mode: 'auto' }` or `{ pin: '2026-07-28' }`. A conformance client built on this must opt in explicitly.

**Note the packaging trap:** `@modelcontextprotocol/sdk@1.30.0` — the package most tutorials name and the one npm resolves for `@modelcontextprotocol/sdk` — is the **legacy** line with a 2025-11-25 ceiling. Modern support lives only in the new split packages.

Gotchas elsewhere: **Go** only enables the modern era when `StreamableHTTPOptions.Stateless = true`; **Rust**'s `ProtocolVersion::LATEST` is still `V_2025_11_25` despite the README, so modern is opt-in there too.

### Frameworks and LLM vendors — none does an authorization code flow

| | Kind | Browser auth code flow? | What it actually supports | Max revision |
| --- | --- | --- | --- | --- |
| `langchain-mcp-adapters` 0.3.2 | client lib | **No** | static header, or BYO `httpx.Auth` | 2025-11-25 |
| `openai-agents` 0.19.4 | client lib | **No** | static headers / `httpx.Auth` | 2025-11-25 |
| OpenAI Responses hosted `mcp` tool | server-side | **No** | static `authorization` token | [?] |
| `google-genai` 2.17.0 | **not a client** | **No** | whatever you pre-configured | 2025-11-25 |
| Anthropic API MCP connector | server-side | **No** | static `authorization_token` | 2025-11-25 |

Verbatim from OpenAI's Responses API docs: *"OAuth client registration and authorization must be handled separately by your application."* Anthropic's connector says the same: *"API consumers are expected to handle the OAuth flow and obtain the access token prior to making the API call."*

Two further notes. LangChain hard-caps `mcp>=1.24.0,<2.0.0` — a hotfix merged **2026-08-06** because `mcp` 2.0.0 broke production LangGraph deployments on import; its OAuth issue was closed **`not_planned`**. And `google-genai` does not embed an MCP client at all — you construct the session yourself.

---

## Partial interop — what "almost works" looks like

The write-up should be able to report these honestly rather than rounding them to success or failure.

**1. Auth succeeds, protocol fails.** This is the dominant failure mode and the most misleading one. Claude Desktop, VS Code, Cursor, `mcp-remote` and both `mcp-cli`s can all complete a textbook OAuth 2.1 authorization code flow — PRM discovery, PKCE, resource indicators, a browser consent screen, a token in hand — and then fail on the very next request because it is an `initialize`. If the server 401s *before* header validation, the user sees a full, successful, pointless OAuth dance followed by an opaque `400`. **The ordering of 401-vs-header-validation on the server is a real UX decision**, and the spec does not fix it.

**2. DCR yes, CIMD no.** `mcp-remote`, both `mcp-cli`s, and (as far as their docs say) Cursor/Windsurf/JetBrains implement only RFC 7591. Against a server that advertises `client_id_metadata_document_supported` but keeps a `registration_endpoint`, these degrade quietly to the deprecated path. Against a **CIMD-only** server they fail with a registration error. Dropping DCR support server-side is therefore a real, and quite aggressive, compatibility choice.

**3. CIMD yes, but you must host the document.** Inspector supports CIMD only if you supply a public HTTPS URL listing `http://localhost:6274/oauth/callback`. Claude Code supports CIMD but defaults to *Anthropic's* document; pointing it at your own needs `MCP_OAUTH_CLIENT_METADATA_URL`. Neither will demonstrate this project's CIMD path without setup work by the operator.

**4. Inspector's beta pin.** Inspector 2.1.0 pins `@modelcontextprotocol/client@2.0.0-beta.5` (2026-07-21), not the `2.0.0` GA (2026-07-27) — in a stable release published 2026-08-05. The GA delta includes a change to the probe classifier so that **HTTP 401/403 on the negotiation probe is treated as an auth failure rather than as evidence the server is legacy**. On a beta.5 Inspector, an authenticated modern-only server may therefore be misclassified as legacy on the probe and fall back to `initialize`. I found no issue or PR explaining the pin. The practical workaround is to select **Modern** explicitly rather than **Auto**, which skips the probe classification entirely. *(Behavioural consequence inferred from the diff — not executed.)*

**5. Claude Code's gate is per-transport.** Even with `MCP_PROTOCOL_NEGOTIATION=auto`, only `http`, `claudeai-proxy`, `ccr-proxy` and `stdio` honour it. A server reached over `sse`, `ws`, or the IDE bridge stays legacy no matter what.

**6. OpenAI's hosted client is mid-migration and currently emits an invalid hybrid.** Two independently-filed SDK issues document it: [java-sdk #1072](https://github.com/modelcontextprotocol/java-sdk/issues/1072) — *"Starting on 2026-07-30 … we observed OpenAI's hosted MCP client begin sending `server/discover` before `tools/list`"* — and [csharp-sdk #1783](https://github.com/modelcontextprotocol/csharp-sdk/issues/1783) — *"ChatGPT negotiates MCP protocol version `2025-11-25` but sends per-request metadata following `2026-07-28`."* Treat it as in-flight, not as support.

**7. The stateless cutover is already breaking live servers.** [claude-code #81965](https://github.com/anthropics/claude-code/issues/81965) documents a Microsoft Business Central MCP server losing per-request header context around 2026-07-27 — exactly the failure mode of a server that bound context at `initialize`. Relevant to this project's own design: **do not bind ERP tenant/session context at handshake time**, because there is no handshake.

---

## Implications for the conformance client

### What it must do that no existing client does

1. **Exercise CIMD against a self-hosted server identity end-to-end**, including hosting its own metadata document at a public HTTPS URL whose `client_id` field is that URL. This is the only item on this list that nothing off the shelf will do unattended, and it is the most distinctive part of the design.
2. **Run headlessly and assert**, rather than render. Inspector is interactive; a conformance client can drive the authorization code flow with a scripted or stubbed authorization server and assert on the wire: that `MCP-Protocol-Version` matches `_meta`, that `Mcp-Method`/`Mcp-Name` are present and correctly base64-sentinel-encoded, that `resource` appears on **both** authorize and token requests, that `iss` is validated before the code is redeemed.
3. **Prove the negative paths**, which no shipped client will do for you: `-32020` `HeaderMismatch` on a deliberately mismatched header, `-32022` `UnsupportedProtocolVersionError` with a correct `supported` list, `405` on `GET`/`DELETE`, `403` on a bad `Origin`, and a `401` carrying a `WWW-Authenticate` with both `resource_metadata` and `scope`.
4. **Demonstrate the legacy-client diagnostic.** The spec asks a modern-only server to name its supported versions in the error it returns to an `initialize`. Nothing tests that; a two-line fixture posting a bare `initialize` proves the server is a good citizen to the 90% of the ecosystem that will hit it that way.

### What it can reuse

Nearly all of the hard parts. `@modelcontextprotocol/client@2.0.0` already implements the full `2026-07-28` wire format and the complete OAuth stack (CIMD, DCR + `application_type`, PKCE S256, RFC 8707, RFC 9728, RFC 8414 + OIDC, RFC 9207, SEP-2352 issuer binding, step-up on `insufficient_scope`). Python's `mcp` 2.0.0 is equivalent and ships a working browser-flow example under `examples/clients/simple-auth-client/`.

So the conformance client is realistically **a thin harness over an SDK plus a hosted CIMD document plus assertions** — not a protocol implementation. Two cautions: pass `versionNegotiation: { pin: '2026-07-28' }` or `{ mode: 'auto' }` explicitly, because the SDK default is `legacy`; and depend on `@modelcontextprotocol/client`, not `@modelcontextprotocol/sdk`, which is the legacy line.

### Server-side consequences

- **Ship dual-era** unless there is a positive reason not to. It is the difference between "Inspector plus an env var" and "everything".
- **Keep `registration_endpoint` alive** alongside `client_id_metadata_document_supported` for as long as DCR-only clients dominate — CIMD-only locks out most of the table above.
- **Advertise `client_id_metadata_document_supported: true`**, or no client will ever take the CIMD path.
- Consider also advertising `"none"` in `token_endpoint_auth_methods_supported`, which Claude Desktop requires before it will select CIMD.
- **Do not bind state at connection time.** There is no handshake and no session ID.
- **Return a helpful error to `initialize`**, naming supported versions.

---

## Open questions / what I could not verify

1. **Nothing was executed against a live server.** Every verdict is derived from source, published packages, or normative spec text. The end-to-end claim for Inspector and Claude Code is *strongly evidenced but untested*; the obvious next step is to stand the server up and try both.
2. **Windsurf and JetBrains** could not be verified from code — revision, header behaviour and SSE response handling are docs-level or unknown, and the legacy-era conclusion for them is inference. Cursor *was* verified from shipped binaries, but its changelog no longer labels versions and its issue tracker is closed, so "no planned `2026-07-28` support" is absence of evidence; forum.cursor.com was not searched.
3. **VS Code's identity mechanism** (DCR vs CIMD) is undetermined. `client_id_metadata_document_supported` appears in VS Code's generic auth stack (`src/vs/base/common/oauth.ts`), but I did not trace whether the MCP client path reaches it.
4. **Cursor's error text against a *pure* modern server** (one with no `initialize` handler at all) was not observed; only the case where the server answers `initialize` with an unsupported version is known.
5. **Whether Claude Code's `MCP_PROTOCOL_NEGOTIATION=auto` path survives an authenticated probe.** Its bundled SDK build could not be identified as pre- or post-GA (the relevant symbols are minified away), so whether it carries the 401-on-probe fix is **[?]**.
6. **Why Inspector 2.1.0 pins a beta SDK** — no issue, PR or changelog entry found.
7. **Whether a modern-only server should 401 before or after header validation** is unspecified, and determines whether legacy clients even reach their OAuth flow.
8. **Claude Desktop's exact negotiated `protocolVersion` string** is never published; the ≤2025-11-25 ceiling is inferred from the auth-spec list and handshake documentation.
9. **`server/discover` and authorization interact in an unspecified way** — whether a server may require a token for `server/discover` (and thus 401 the very probe used for era detection) is not addressed by the spec pages I read.
10. **Revision support is moving weekly.** C# 2.1.0 and Inspector 2.1.0 both shipped on 2026-08-05, the day before this was written. Re-check before relying on any "not supported" claim.

---

## Sources

**Specification — 2026-07-28**
- https://modelcontextprotocol.io/specification/2026-07-28
- https://modelcontextprotocol.io/specification/2026-07-28/changelog
- https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http
- https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
- https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover
- https://modelcontextprotocol.io/specification/2026-07-28/deprecated
- https://modelcontextprotocol.io/specification/versioning
- https://modelcontextprotocol.io/community/feature-lifecycle
- https://modelcontextprotocol.io/community/sdk-tiers
- https://modelcontextprotocol.io/docs/sdk
- https://modelcontextprotocol.io/extensions/client-matrix

**Specification — prior revisions**
- https://modelcontextprotocol.io/specification/2025-11-25/changelog
- https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

**Announcements**
- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- https://blog.modelcontextprotocol.io/posts/sdk-betas-2026-07-28/
- https://claude.com/blog/bringing-mcp-2026-07-28-to-claude

**IETF**
- https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-13 (OAuth 2.1)
- https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00 (CIMD)
- https://datatracker.ietf.org/doc/html/rfc7591 (DCR)
- https://datatracker.ietf.org/doc/html/rfc8414 (AS Metadata)
- https://www.rfc-editor.org/rfc/rfc8707.html (Resource Indicators)
- https://datatracker.ietf.org/doc/html/rfc9728 (Protected Resource Metadata)
- https://datatracker.ietf.org/doc/html/rfc9207 (Issuer Identification)
- https://datatracker.ietf.org/doc/html/rfc6750 (Bearer Token Usage)
- https://openid.net/specs/openid-connect-discovery-1_0.html
- https://openid.net/specs/openid-connect-registration-1_0.html

**SDK and tooling source / packages**
- https://github.com/modelcontextprotocol/typescript-sdk
- https://registry.npmjs.org/@modelcontextprotocol/core (2.0.0, 2026-07-27)
- https://registry.npmjs.org/@modelcontextprotocol/client (2.0.0, 2026-07-27; 2.0.0-beta.5, 2026-07-21)
- https://registry.npmjs.org/@modelcontextprotocol/sdk (1.30.0, 2026-07-27)
- https://github.com/modelcontextprotocol/inspector
- https://registry.npmjs.org/@modelcontextprotocol/inspector (2.1.0, 2026-08-05)
- https://github.com/modelcontextprotocol/python-sdk
- https://github.com/modelcontextprotocol/python-sdk/issues/2891
- https://github.com/modelcontextprotocol/csharp-sdk
- https://github.com/modelcontextprotocol/csharp-sdk/issues/1783
- https://github.com/modelcontextprotocol/go-sdk
- https://github.com/modelcontextprotocol/rust-sdk
- https://github.com/modelcontextprotocol/java-sdk/issues/1072
- https://registry.npmjs.org/mcp-remote (0.1.38, 2026-02-05)
- https://github.com/geelen/mcp-remote

**Client source and vendor docs**
- `~/.local/share/claude/versions/2.1.223` (installed binary, build 2026-08-05T18:12:31Z)
- https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md
- https://github.com/anthropics/claude-code/issues/36861 (CIMD documentation gap)
- https://github.com/anthropics/claude-code/issues/81965 (stateless cutover breakage)
- https://code.claude.com/docs/en/mcp
- https://code.claude.com/docs/en/settings
- https://claude.ai/oauth/claude-code-client-metadata (fetched live, HTTP 200)
- https://claude.com/docs/connectors/building
- https://claude.com/docs/connectors/building/authentication
- https://claude.com/docs/connectors/custom/remote-mcp
- https://support.claude.com/en/articles/11176164
- https://raw.githubusercontent.com/microsoft/vscode/main/src/vs/platform/mcp/common/modelContextProtocol.ts
- https://raw.githubusercontent.com/microsoft/vscode/main/src/vs/workbench/api/common/extHostMcp.ts
- https://raw.githubusercontent.com/microsoft/vscode/main/extensions/copilot/src/extension/common/modelContextProtocol.ts
- https://code.visualstudio.com/docs/copilot/chat/mcp-servers
- https://raw.githubusercontent.com/zed-industries/zed/main/crates/context_server/src/types.rs
- https://github.com/zed-industries/zed/pull/61625 (draft, modern-era support)
- https://cursor.com/docs/context/mcp
- https://cursor.com/api/download?releaseTrack=stable (version 3.14.27)
- https://registry.npmjs.org/@cursor/sdk (1.0.26, 2026-07-28T21:24:55Z)
- https://docs.windsurf.com
- https://www.jetbrains.com/help/ai-assistant/mcp.html
- https://developers.openai.com/api/docs/mcp/
- https://github.com/langchain-ai/langchain-mcp-adapters
- https://github.com/openai/openai-agents-python

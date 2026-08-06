# MCP 2026-07-28 — Authorization requirements and the client-identity decision

**Question:** What does the MCP `2026-07-28` revision actually require for OAuth 2.0 client identity, discovery, audience binding, and stateless header-based routing — and does an off-the-shelf IdP exist that can speak the required client-identity mechanism end to end with a real client?

**Date:** 2026-08-06

**Method note:** The `2026-07-28` revision postdates the author's training data. Everything below was fetched live on 2026-08-06. Where a source could not be fetched, or where a quote came through a summarising fetch rather than raw page text, it is flagged in [Confidence notes](#confidence-notes).

---

## Sources fetched

### MCP specification (all fetched 2026-08-06, all returned HTTP 200)

| URL | What it is |
| --- | --- |
| <https://modelcontextprotocol.io/specification/2026-07-28/> | Revision landing page; BCP-14 keywords clause; "Stateless, self-contained requests" |
| <https://modelcontextprotocol.io/specification/versioning> | Revision list — confirms `2026-07-28` is **Current** |
| <https://modelcontextprotocol.io/specification/2026-07-28/changelog> | "Key Changes" — explicitly diffs against `2025-11-25` |
| <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization> | Core authorization page |
| <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration> | CIMD / pre-registration / DCR |
| <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/authorization-server-discovery> | RFC 9728 + RFC 8414 discovery rules |
| <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations> | Normative security requirements |
| <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http> | Transport, headers, GET removal |
| <https://modelcontextprotocol.io/specification/2026-07-28/basic/index> | Statelessness, `_meta`, error-code policy |
| <https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices> | Token passthrough, confused deputy, SSRF, state-handle hijacking |
| <https://blog.modelcontextprotocol.io/posts/2026-07-28/> | Release announcement |

### IETF sources

| URL | What it is |
| --- | --- |
| <https://datatracker.ietf.org/doc/draft-ietf-oauth-client-id-metadata-document/> | CIMD draft index — versions `-00`, `-01`, `-02`; `-02` dated **2026-07-06**; WG State "WG Document", IESG State "I-D Exists" |
| <https://www.ietf.org/archive/id/draft-ietf-oauth-client-id-metadata-document-00.html> | **The version MCP 2026-07-28 normatively cites** (published 2025-10-08) |
| <https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-01> | `-01` (2026-03-02), for the change history |
| <https://datatracker.ietf.org/doc/html/rfc9728> | OAuth 2.0 Protected Resource Metadata |
| <https://www.rfc-editor.org/rfc/rfc8707.html> | Resource Indicators for OAuth 2.0 |

RFC 7591, RFC 6749/6750, RFC 9207, RFC 9700 and OAuth 2.1 `draft-ietf-oauth-v2-1-13` are cited below **as referenced by the MCP spec text**, not independently re-fetched — see [Confidence notes](#confidence-notes).

### Ecosystem / IdP evidence

| URL | What it is | Date |
| --- | --- | --- |
| <https://oauth.net/2/client-id-metadata-document/> | oauth.net implementation roster | fetched 2026-08-06 |
| <https://claude.com/docs/connectors/building/authentication> | Anthropic's connector auth docs — Claude's CIMD behaviour | fetched 2026-08-06 |
| <https://github.com/keycloak/keycloak/issues/45106> | "Experimental Support for OAuth Client ID Metadata Document" | opened 2026-01-01, **closed 2026-06-23** |
| <https://github.com/keycloak/keycloak/issues/49730> | `--features=cimd` missing `none` in `token_endpoint_auth_methods_supported` | opened 2026-06-05, **closed 2026-06-16**, label `release/26.7.0` |
| <https://github.com/keycloak/keycloak/releases/tag/26.7.0> and <https://www.keycloak.org/2026/07/keycloak-2670-released> | Keycloak 26.7.0 | released **2026-07-09** |
| <https://github.com/ory/hydra/issues/4061> | "Support Client ID Metadata Document (CIMD)" | opened 2026-01-17, **still OPEN** (last activity 2026-07-30) |
| <https://www.authlete.com/developers/cimd/> | Authlete CIMD support since **3.0.22**, implementation completed Nov 2025 | fetched 2026-08-06 |
| <https://stytch.com/blog/stytch-supports-cimd/> | Stytch CIMD (beta), demo site `client.dev` | published **2025-10-17** |
| <https://workos.com/blog/client-id-metadata-documents-cimd-oauth-client-registration-mcp> | WorkOS AuthKit CIMD | published **2025-12-08** |
| <https://www.descope.com/blog/post/cimd-support> | Descope CIMD **generally available** in Agentic Identity Hub | published **2026-01-27** |
| <https://auth0.com/docs/get-started/auth0-overview/create-applications/register-applications-with-cimd> | Auth0 "Client ID Metadata Document Registration" tenant toggle | fetched 2026-08-06 |
| <https://github.com/modelcontextprotocol/python-sdk/issues/1801> | Server-side CIMD in the MCP Python SDK — **still OPEN** | opened 2025-12-18, last update 2026-04-17 |
| <https://github.com/anthropics/claude-code/issues/37747> | Real CIMD interop regression (redirect_uri port matching) | opened 2026-03-23, closed 2026-05-24 |
| <https://github.com/PrefectHQ/fastmcp/issues/2863> | FastMCP CIMD support | opened 2026-01-13, closed 2026-02-06 |

---

## Verdict — does an off-the-shelf IdP exist?

**Yes. Several, and the end-to-end path with a real client is already proven in production.** A self-authored authorization server is **not** forced by the client-identity mechanism.

The short version:

- CIMD is **SHOULD**, not MUST, for both authorization servers and MCP clients. DCR is **MAY** and is formally *deprecated*. So even an AS with no CIMD at all is spec-conformant — the *hard* MUSTs land on the resource server (RFC 9728, audience validation), not on client identity.
- At least six authorization servers ship CIMD today: **Authlete** (since 3.0.22, implementation completed Nov 2025), **Stytch** (Oct 2025, beta), **WorkOS AuthKit** (Dec 2025), **Descope** (GA, Jan 2026), **Scalekit**, and **Keycloak** behind the `--features=cimd` flag. oauth.net's roster lists Auth0 as "coming soon" while Auth0's own docs already describe a `Client ID Metadata Document Registration` tenant toggle — treat Auth0 as in-flight, not settled.
- **Keycloak is the free, self-hostable option that works.** Issue [#45106](https://github.com/keycloak/keycloak/issues/45106) ("Experimental Support for OAuth Client ID Metadata Document") closed 2026-06-23; the one known blocker for real clients — [#49730](https://github.com/keycloak/keycloak/issues/49730), where the discovery document advertised `client_id_metadata_document_supported: true` but omitted `"none"` from `token_endpoint_auth_methods_supported`, which made Claude fall back to DCR — closed 2026-06-16 and shipped in **26.7.0 on 2026-07-09**. Keycloak ≥ 26.7.0 with `--features=cimd` is the concrete recommendation.
- **The real client already speaks it.** Anthropic's connector docs list `oauth_cimd` as "Supported out of the box" across Claude.ai, Desktop, mobile, Claude Code and Cowork. Claude Code publishes its own CIMD at `https://claude.ai/oauth/claude-code-client-metadata`. oauth.net additionally lists VS Code, MCPJam and ChatGPT as CIMD clients.
- **The one hard gate to get right:** Claude selects CIMD *only* when AS metadata advertises **both** `"client_id_metadata_document_supported": true` **and** `"none"` in `token_endpoint_auth_methods_supported`. Miss either and Claude silently falls back to DCR.

**Where an off-the-shelf IdP does *not* help:** Microsoft Entra ID supports neither CIMD nor DCR (pre-registration only, and community analysis reports this as a deliberate SSRF/attestation posture, not an oversight). Okta has DCR but no CIMD. **Ory Hydra has an open, unimplemented feature request** ([#4061](https://github.com/ory/hydra/issues/4061), opened 2026-01-17, still open 2026-07-30). If the exhibit were pinned to Entra, Okta or Hydra, CIMD would have to be proxied or self-authored.

**Secondary risk worth naming:** if you self-author an AS *in Python*, the MCP Python SDK gives you nothing — [python-sdk#1801](https://github.com/modelcontextprotocol/python-sdk/issues/1801) ("Implement server-side support for CIMD") has been open since 2025-12-18 and lists fetching, validation, caching and SSRF protection as all missing. Client-side CIMD exists in the SDK; server-side does not. That asymmetry is the strongest argument for putting a real IdP in front rather than hand-rolling.

---

## 1. Client identity

### 1.1 Normative strength

From [`basic/authorization` §Overview](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization):

> 2. Authorization servers and MCP clients **SHOULD** support [OAuth Client ID Metadata Documents](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration#client-id-metadata-documents) ([draft-ietf-oauth-client-id-metadata-document-00](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00)).
>
> 3. Authorization servers and MCP clients **MAY** support the OAuth 2.0 Dynamic Client Registration Protocol ([RFC7591](https://datatracker.ietf.org/doc/html/rfc7591)). Note that [Dynamic Client Registration](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration#dynamic-client-registration) is deprecated and retained for backwards compatibility with authorization servers that do not support Client ID Metadata Documents.

And from [`client-registration`](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration):

> MCP clients and authorization servers **SHOULD** support OAuth Client ID Metadata Documents as specified in [OAuth Client ID Metadata Document](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-client-id-metadata-document-00) for client registration.

So: **SHOULD for both sides, symmetric.** There is no MUST anywhere on CIMD. The only MUST in the client-identity area is on the *client*:

> Before initiating the authorization flow, MCP clients **MUST** obtain a client ID through one of three registration mechanisms: Client ID Metadata Documents, pre-registration, or Dynamic Client Registration […]

**What a server/AS MUST support:** nothing, in client-identity terms. An AS that supports only pre-registration is conformant. The MUSTs are conditional — *if* you implement CIMD, then the validation rules in §1.3 bind.

### 1.2 Selection priority (client side)

> Clients supporting all options **SHOULD** use the following priority order:
>
> 1. Use pre-registered client information for the server if the client has it available
> 2. Use Client ID Metadata Documents if the Authorization Server indicates that it supports them (via `client_id_metadata_document_supported` in OAuth Authorization Server Metadata)
> 3. Use Dynamic Client Registration as a fallback if the Authorization Server supports it (via `registration_endpoint` in OAuth Authorization Server Metadata)
> 4. Prompt the user to enter the client information if no other option is available

Note the ordering consequence: **pre-registration outranks CIMD.** A client that already holds credentials for your AS will not exercise the CIMD path at all.

### 1.3 Exact document shape and dereferencing

MCP's client-side requirements, verbatim:

> * Clients **MUST** host their metadata document at an HTTPS URL following RFC requirements
> * The `client_id` URL **MUST** use the "https" scheme and contain a path component, e.g. `https://example.com/client.json`
> * The metadata document **MUST** include at least the following properties: `client_id`, `client_name`, `redirect_uris`
> * Clients **MUST** ensure the `client_id` value in the metadata matches the document URL exactly
> * Clients **MAY** use `private_key_jwt` for client authentication (e.g., for requests to the token endpoint) with appropriate JWKS configuration […]

MCP's AS-side requirements, verbatim:

> * **SHOULD** fetch metadata documents when encountering URL-formatted client\_ids
> * **MUST** validate that the fetched document's `client_id` matches the URL exactly
> * **SHOULD** cache metadata respecting HTTP cache headers
> * **MUST** validate redirect URIs presented in an authorization request against those in the metadata document
> * **MUST** validate the document structure is valid JSON and contains required fields
> * **SHOULD** follow the security considerations in [Section 6 of Client ID Metadata Document] and in [Client ID Metadata Document Security]

Note a **discrepancy worth flagging**: MCP says the document **MUST** include `client_id`, `client_name`, `redirect_uris`. The CIMD draft `-00` itself only requires `client_id` (matching the URL by simple string comparison); `client_name` and `redirect_uris` are MCP-level tightenings. If you validate to the draft alone you will accept documents MCP considers invalid.

The spec's canonical example document:

```json
{
  "client_id": "https://app.example.com/oauth/client-metadata.json",
  "client_name": "Example MCP Client",
  "client_uri": "https://app.example.com",
  "logo_uri": "https://app.example.com/logo.png",
  "redirect_uris": [
    "http://127.0.0.1:3000/callback",
    "http://localhost:3000/callback"
  ],
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "token_endpoint_auth_method": "none"
}
```

Additional constraints from the **CIMD draft `-00` §3** (the version MCP cites), quoted via datatracker:

> MUST have an 'https' scheme, MUST contain a path component, MUST NOT contain single-dot or double-dot path segments, MUST NOT contain a fragment component and MUST NOT contain a username or password

Query strings: **SHOULD NOT** be included. Ports are permitted.

**Prohibited fields** (draft §4.1):

> the `token_endpoint_auth_method` property MUST NOT include `client_secret_post`, `client_secret_basic`, `client_secret_jwt`, or any other method based around a shared symmetric secret

> `client_secret` and `client_secret_expires_at` properties MUST NOT be used

**Caching** (draft §4.4): the AS **MAY** cache; **SHOULD** respect HTTP cache headers; **MAY** impose its own upper/lower bounds; **MUST NOT** cache error responses; **MUST NOT** cache invalid or malformed documents.

**Fetch failure** (draft §4.3): "the authorization server SHOULD abort the authorization request".

Draft `-01` (2026-03-02) added: mandated HTTP 200 responses when fetching metadata, expanded SSRF considerations, guidance for servers supporting both registered and unregistered clients, and security considerations for changes in client metadata. **MCP 2026-07-28 cites `-00`, not `-01` or `-02` — see [Open ambiguities](#open-ambiguities).**

### 1.4 Relationship to Dynamic Client Registration

**Coexistence with a stated migration direction — not a hard replacement.** The changelog is explicit:

> Deprecate the OAuth 2.0 Dynamic Client Registration Protocol ([RFC7591]) as a client registration mechanism in favor of [Client ID Metadata Documents] ([PR #2858](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2858)). It remains available for backwards compatibility with authorization servers that do not support Client ID Metadata Documents.

Under the [feature lifecycle policy](https://modelcontextprotocol.io/community/feature-lifecycle), a Deprecated feature remains in the spec for **at least twelve months** (or ninety days under expedited removal) before becoming eligible for removal. So DCR is safe through at least 2027-07-28.

One durable advantage the spec calls out for CIMD:

> Client IDs based on Client ID Metadata Documents are portable across authorization servers, since they are self-hosted HTTPS URLs resolved by the authorization server on demand. No re-registration is needed when the authorization server changes.

Versus, for pre-registered and DCR-derived credentials:

> Clients that use pre-registered credentials, or persist client credentials obtained via Dynamic Client Registration, **MUST** associate those credentials with the specific authorization server that issued them, keyed by the authorization server's `issuer` identifier. […] clients **MUST NOT** reuse client credentials from a different authorization server and **MUST** re-register with the new authorization server.

DCR also picked up a new MUST in this revision:

> MCP clients **MUST** specify an appropriate `application_type` during Dynamic Client Registration. Omitting it defaults to `"web"` under OIDC, which can conflict with native-style redirect URIs; non-OIDC servers safely ignore the parameter.

---

## 2. Discovery

### 2.1 What the resource server must publish

From [`authorization-server-discovery`](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/authorization-server-discovery):

> MCP servers **MUST** implement the OAuth 2.0 Protected Resource Metadata ([RFC9728](https://datatracker.ietf.org/doc/html/rfc9728)) specification to indicate the locations of authorization servers. The Protected Resource Metadata document returned by the MCP server **MUST** include the `authorization_servers` field containing at least one authorization server.

This is the hardest requirement in the whole authorization surface for a resource server, and it is echoed in the core page:

> 4. MCP servers **MUST** implement OAuth 2.0 Protected Resource Metadata ([RFC9728]). MCP clients **MUST** use OAuth 2.0 Protected Resource Metadata for [authorization server discovery].

### 2.2 Exact paths and the path-insertion rule

> MCP servers **MUST** implement one of the following discovery mechanisms […]
>
> 1. **WWW-Authenticate Header**: Include the resource metadata URL in the `WWW-Authenticate` HTTP header under `resource_metadata` when returning `401 Unauthorized` responses, as described in [RFC9728 Section 5.1].
>
> 2. **Well-Known URI**: Serve metadata at a well-known URI as specified in [RFC9728]. This can be either:
>    * At the path of the server's MCP endpoint: `https://example.com/public/mcp` could host metadata at `https://example.com/.well-known/oauth-protected-resource/public/mcp`
>    * At the root: `https://example.com/.well-known/oauth-protected-resource`

Note carefully: the server MUST implement **one of** these. The client, however, MUST support **both**:

> MCP clients **MUST** support both discovery mechanisms and use the resource metadata URL from the parsed `WWW-Authenticate` headers when present; otherwise, they **MUST** fall back to constructing and requesting the well-known URIs in the order listed above.
>
> MCP clients **MUST** be able to parse `WWW-Authenticate` headers and respond appropriately to `HTTP 401 Unauthorized` responses from the MCP server.

The underlying rule is **RFC 9728 §3.1** — path insertion, *not* appending:

> any terminating slash (`/`) following the host component MUST be removed before inserting `/.well-known/` and the well-known URI path suffix between the host component and the path and/or query components.

So for a resource `https://mcp.example.com/erp`, the metadata lives at `https://mcp.example.com/.well-known/oauth-protected-resource/erp` — **not** `https://mcp.example.com/erp/.well-known/...`. This is the single most commonly mis-implemented line in the whole discovery chain.

### 2.3 What the AS must make discoverable

> 5. MCP authorization servers **MUST** provide at least one of the following discovery mechanisms:
>    * OAuth 2.0 Authorization Server Metadata ([RFC8414])
>    * [OpenID Connect Discovery 1.0]
>
>    MCP clients **MUST** support both [discovery mechanisms] to obtain the information required to interact with the authorization server.

MCP uses the **default** RFC 8414 well-known suffix and defines no MCP-specific suffix:

> MCP uses the default `oauth-authorization-server` well-known URI suffix defined in [RFC 8414 Section 3.1] for authorization server metadata discovery. MCP does not define an application-specific well-known URI suffix.

Client probe order, **for issuer URLs with a path component** (e.g. `https://auth.example.com/tenant1`) — clients **MUST** try, in order:

1. `https://auth.example.com/.well-known/oauth-authorization-server/tenant1`
2. `https://auth.example.com/.well-known/openid-configuration/tenant1`
3. `https://auth.example.com/tenant1/.well-known/openid-configuration`

**For issuer URLs without a path component** — clients **MUST** try:

1. `https://auth.example.com/.well-known/oauth-authorization-server`
2. `https://auth.example.com/.well-known/openid-configuration`

Validation is a MUST, and its failure mode is spelled out with an example:

> After retrieving a metadata document, MCP clients **MUST** validate it as required by [RFC8414 Section 3.3] or [OpenID Connect Discovery Section 4.3]: the `issuer` value in the document **MUST** be identical to the issuer identifier used to construct the well-known URL. If they differ, the client **MUST NOT** use the metadata. For example, a document fetched from `https://attacker.example/.well-known/oauth-authorization-server` that contains `"issuer": "https://honest.example"` **MUST** be rejected.

Also required for PKCE discoverability:

> **OAuth 2.0 Authorization Server Metadata**: If `code_challenge_methods_supported` is absent, the authorization server does not support PKCE and MCP clients **MUST** refuse to proceed.
>
> Authorization servers providing OpenID Connect Discovery 1.0 **MUST** include `code_challenge_methods_supported` in their metadata to ensure MCP compatibility.

### 2.4 Exact `WWW-Authenticate` parameters

**On 401 (unauthenticated / invalid token):**

- `resource_metadata` — **required in practice** if the server chose mechanism 1. RFC 9728 §5.1 defines it as "The URL of the protected resource metadata."
- `scope` — **SHOULD**:

> MCP servers **SHOULD** include a `scope` parameter in the `WWW-Authenticate` header as defined in [RFC 6750 Section 3] to indicate the scopes required for accessing the resource.

Spec's example 401:

```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource",
                         scope="files:read"
```

**On 403 (insufficient scope)** — the server **SHOULD** respond with:

> * `HTTP 403 Forbidden` status code (per [RFC 6750 Section 3.1])
> * `WWW-Authenticate` header with the `Bearer` scheme and additional parameters:
>   * `error="insufficient_scope"` […]
>   * `scope="required_scope1 required_scope2"` […]
>   * `resource_metadata` - the URI of the Protected Resource Metadata document (for consistency with 401 responses)
>   * `error_description` (optional) - human-readable description of the error

The full HTTP status table:

| Status Code | Description | Usage |
| --- | --- | --- |
| 401 | Unauthorized | Authorization required or token invalid |
| 403 | Forbidden | Invalid scopes or insufficient permissions |
| 400 | Bad Request | Malformed authorization request |

Scope semantics carry two client-side MUSTs that constrain how a server may design its scope vocabulary:

> Clients **MUST NOT** assume any particular set relationship between the challenged scope set and `scopes_supported`. Clients **MUST** treat the scopes provided in the challenge as authoritative for the current operation.

And one server-side MUST that is easy to miss:

> Servers **MUST** account for scope hierarchies, where a broader scope implies narrower ones, when deciding whether a token is sufficient for an operation.

Plus a resource-server SHOULD NOT about refresh scope:

> **MCP Servers** (Protected Resources) **SHOULD NOT** include `offline_access` in `WWW-Authenticate` scope or Protected Resource Metadata `scopes_supported`, as refresh tokens are not a resource requirement.

---

## 3. Audience binding

### 3.1 Required, and on both requests

> MCP clients **MUST** implement Resource Indicators for OAuth 2.0 as defined in [RFC 8707] to explicitly specify the target resource for which the token is being requested. The `resource` parameter:
>
> 1. **MUST** be included in both authorization requests and token requests.
> 2. **MUST** identify the MCP server that the client intends to use the token with.
> 3. **MUST** use the canonical URI of the MCP server as defined in [RFC 8707 Section 2].

Crucially, this is unconditional on AS support:

> MCP clients **MUST** send this parameter regardless of whether authorization servers support it.

Canonical URI rules (spec's own examples):

- Valid: `https://mcp.example.com/mcp`, `https://mcp.example.com`, `https://mcp.example.com:8443`, `https://mcp.example.com/server/mcp`
- Invalid: `mcp.example.com` (missing scheme), `https://mcp.example.com#fragment` (contains fragment)
- Trailing slash: implementations **SHOULD** consistently use the form *without* the trailing slash.
- Case: "While the canonical form uses lowercase scheme and host components, implementations **SHOULD** accept uppercase scheme and host components for robustness and interoperability."

RFC 8707 §2 itself: the value "MUST be an absolute URI, as specified by Section 4.3 of [RFC3986]. The URI MUST NOT include a fragment component." An AS that cannot honour the value "should reject the request with an error response using the error code `invalid_target`".

Note the asymmetry the security page states plainly — RFC 8707 binds tokens **"when the Authorization Server supports the capability"**. The client MUST always send it; whether it actually produces an audience-restricted token depends on the AS. This is why the resource-server-side validation below is the load-bearing control, not the `resource` parameter.

### 3.2 What the resource server MUST reject

From [`basic/authorization` §Token Handling](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization):

> MCP servers, acting in their role as an OAuth 2.1 resource server, **MUST** validate access tokens as described in [OAuth 2.1 Section 5.2]. MCP servers **MUST** validate that access tokens were issued specifically for them as the intended audience, according to [RFC 8707 Section 2]. If validation fails, servers **MUST** respond according to [OAuth 2.1 Section 5.3] error handling requirements. Invalid or expired tokens **MUST** receive a HTTP 401 response.
>
> MCP clients **MUST NOT** send tokens to the MCP server other than ones issued by the MCP server's authorization server.
>
> MCP servers **MUST** only accept tokens that are valid for use with their own resources.
>
> MCP servers **MUST NOT** accept or transit any other tokens.

From [`security-considerations` §Access Token Privilege Restriction](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations):

> MCP servers **MUST** validate access tokens before processing the request, ensuring the access token is issued specifically for the MCP server, and take all necessary steps to ensure no data is returned to unauthorized parties.
>
> MCP servers **MUST** only accept tokens specifically intended for themselves and **MUST** reject tokens that do not include them in the audience claim or otherwise verify that they are the intended recipient of the token.
>
> If the MCP server makes requests to upstream APIs, it may act as an OAuth client to them. The access token used at the upstream API is a separate token, issued by the upstream authorization server. The MCP server **MUST NOT** pass through the token it received from the MCP client.

From [Security Best Practices §Token Passthrough](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices#token-passthrough):

> MCP servers **MUST NOT** accept any tokens that were not explicitly issued for the MCP server.

**Confused deputy** — the one MUST that applies only to proxy-shaped servers:

> MCP proxy servers using static client IDs **MUST** obtain user consent for each [dynamically registered client] before forwarding to third-party authorization servers (which may require additional consent).

The best-practices page expands this into a set of MUSTs for proxy servers: maintain a per-user registry of approved `client_id` values and check it *before* forwarding; exact-string-match `redirect_uri` against the registered URI with no wildcards; reject callbacks where `state` is missing or mismatched; and — critically — "The consent cookie or session containing the `state` value **MUST NOT** be set until **after** the user has approved the consent screen."

---

## 4. Statelessness and header-based routing

### 4.1 What is mandated

Statelessness is a hard protocol property, not a deployment style. From [`basic/index` §Statelessness](https://modelcontextprotocol.io/specification/2026-07-28/basic/index):

> The Model Context Protocol (MCP) is a **stateless protocol**: all the information needed to process a request is contained in the request itself. A server processes each request independently; no state should be inferred from previous requests, even those on the same connection or stream.
>
> * Servers **MUST NOT** rely on prior requests over the same connection to establish context (e.g., capabilities, protocol version, client identity). Every request supplies this metadata in its `_meta` field.
> * Servers **SHOULD** be prepared to handle requests associated with multiple tasks, threads, or conversations.
> * Servers **SHOULD NOT** require that a client reuse the same connection or process to perform related operations.
> * Clients **SHOULD NOT** use an individual task, thread, or conversation as the lifetime boundary for the stdio process.
> * State that needs to span multiple requests (e.g., long-running tasks, application-level handles) **MUST** be referenced by an explicit identifier the client passes on each request.

The `initialize` / `notifications/initialized` handshake is gone. Per-request `_meta` fields replace it:

| Key | Required |
| --- | --- |
| `io.modelcontextprotocol/protocolVersion` | **Yes** |
| `io.modelcontextprotocol/clientCapabilities` | **Yes** |
| `io.modelcontextprotocol/clientInfo` | No (SHOULD) |
| `io.modelcontextprotocol/logLevel` | No |

> A request missing any required field is malformed; the server **MUST** reject it with JSON-RPC error code `-32602` (Invalid params). On HTTP, the response status **MUST** be `400 Bad Request`.

And a security-relevant caveat on identity fields:

> `io.modelcontextprotocol/clientInfo` and `io.modelcontextprotocol/serverInfo` are self-reported by the sender and are not verified by the protocol. […] Implementations **SHOULD NOT** use them to change the behavior of the client or server, and **SHOULD NOT** rely on them for security decisions.

### 4.2 The headers

| Header | Status | Notes |
| --- | --- | --- |
| `MCP-Protocol-Version` | **MUST** on every POST | "Every POST request to the MCP endpoint **MUST** include an `MCP-Protocol-Version` header." Value **MUST** match `_meta` protocolVersion or the server **MUST** return 400 + `HeaderMismatch`. |
| `Mcp-Method` | **REQUIRED**, all requests | Mirrors `method` |
| `Mcp-Name` | **REQUIRED** for `tools/call`, `resources/read`, `prompts/get` | Mirrors `params.name` or `params.uri`; Base64 sentinel `=?base64?…?=` when not ASCII-safe |
| `Mcp-Param-{Name}` | Server **MAY** designate via `x-mcp-header`; clients **MUST** support the feature | Mirrors annotated tool parameters into headers |
| `Accept` | **MUST** list both `application/json` and `text/event-stream` | |
| `Origin` | Servers **MUST** validate; invalid → **403 Forbidden** | DNS-rebinding defence |
| `X-Accel-Buffering: no` | **SHOULD** on SSE responses | Disables proxy buffering |
| `Mcp-Session-Id` | **Removed.** Server "**SHOULD** … ignore it, and do not mint or echo session IDs" | |
| `Last-Event-ID` | **Removed.** "ignore it; streams are not resumable" | |

The rationale is explicitly routing:

> The Streamable HTTP transport mirrors selected JSON-RPC body fields into HTTP headers so that intermediaries (load balancers, gateways, observability tooling) can route and inspect requests without parsing the body.

So header-based routing is **mandated on the wire** (the headers are REQUIRED and validated), while *acting on* those headers at an intermediary is merely enabled. There is no new dedicated routing header beyond `Mcp-Method` / `Mcp-Name` / `Mcp-Param-*`.

Server-side validation is a MUST with a specific error:

> Servers that process the request body **MUST** reject requests where the values specified in the headers do not match the corresponding values in the request body. […] When rejecting a request due to header validation failure, servers **MUST** return HTTP status `400 Bad Request` and **MUST** include a JSON-RPC error response using the following error code: `-32020` `HeaderMismatch`.

Failure conditions listed: a required standard header missing; a header value not matching the body (after Base64 decode where applicable); a header value containing invalid characters.

### 4.3 Standalone server-initiated SSE (`GET` on the MCP endpoint)

**Removed, not merely discouraged.** The transport page's own banner:

> Revision 2026-07-28 changed the behavior of Streamable HTTP. […] Changes included:
> * Removal of the GET stream endpoint.
> * Removal of protocol-level sessions.

The endpoint requirement is now POST-only:

> The server **MUST** provide a single HTTP endpoint path (hereafter referred to as the **MCP endpoint**) that supports POST.

And for legacy traffic:

> A server that supports only this revision and receives such traffic from an older client **SHOULD** respond as follows:
> * HTTP GET or DELETE to the MCP endpoint: respond with `405 Method Not Allowed`.

Server-initiated JSON-RPC *requests* are gone entirely:

> The server **MUST NOT** send independent JSON-RPC *requests* on this stream. Server-to-client interactions (sampling, elicitation, list-roots) are embedded as input requests inside an `InputRequiredResult` per MRTR […] This is a change from Streamable HTTP in protocol versions `2025-03-26` through `2025-11-25`, where servers could send such requests on SSE streams.

**Does statelessness foreclose server-initiated streams? No — it re-homes them.** Long-lived server-to-client notification streams still exist; they are now the *response stream of a POST*:

> Long-lived notification streams are obtained by sending a `subscriptions/listen` request. The server's response is itself an SSE stream that stays open and delivers the change notifications the client opted in to […]

> Long-lived requests like `subscriptions/listen` remain request/response; the response is just an open stream of notifications. Their state is scoped to the request itself, not to the connection underneath.

Cancellation is now purely transport-level:

> Closing the SSE response stream **MUST** be treated by the server as cancellation of that request. […] The server **SHOULD** stop work on the cancelled request as soon as practical and **MUST NOT** send any further messages for it.

For a stateless FastAPI server this is good news: no session table, no GET stream to manage, no resumability buffer. The only genuinely long-lived thing is a `subscriptions/listen` POST response, and even that is optional (it is a `subscriptions` capability, not a transport mandate).

---

## 5. Delta from the previous revision

**The immediately preceding revision is `2025-11-25`.** Confirmed from the spec's own changelog opening line — "changes made to the Model Context Protocol (MCP) specification since the previous revision, [2025-11-25]" — and from the transport page's compatibility section, which describes "Protocol versions `2025-03-26` through `2025-11-25`". (Note: `2025-06-18` is *not* the predecessor; a lot of secondary commentary gets this wrong.)

Full diff link the spec itself provides: <https://github.com/modelcontextprotocol/specification/compare/2025-11-25...2026-07-28>

### Breaking changes a pinned older client will hit

| # | Change | Impact on a `2025-11-25` client |
| --- | --- | --- |
| 1 | Protocol-level sessions and `Mcp-Session-Id` removed (SEP-2567) | Client sends `Mcp-Session-Id`; server ignores it. Non-fatal. |
| 2 | `initialize` / `notifications/initialized` handshake removed; per-request `_meta` (SEP-2575) | **Fatal.** Old client's `initialize` is an unknown method → `404` + `-32601`. |
| 3 | `server/discover` added; servers **MUST** implement it | New capability; old clients don't call it. |
| 4 | GET stream + `resources/subscribe`/`unsubscribe` replaced by `subscriptions/listen` (SEP-2575) | **Fatal for subscriptions.** GET → `405`. |
| 5 | `ping`, `logging/setLevel`, `notifications/roots/list_changed` removed | Old client calls fail. |
| 6 | Tasks moved out of core into the `io.modelcontextprotocol/tasks` extension (SEP-2663) | Fatal if the client used core tasks. |
| 7 | MRTR replaces server-initiated `roots/list` / `sampling/createMessage` / `elicitation/create` (SEP-2322) | **Fatal.** Old client waits for a server request that never arrives. |
| 8 | All results carry a required `resultType` | Old client ignores it; forward direction requires treating absent as `"complete"`. |
| 9 | SSE resumability and `Last-Event-ID` removed (SEP-2575) | Broken stream loses the request; client **MUST** re-issue with a new ID. |

### Non-breaking-but-required additions

- `Mcp-Method` and `Mcp-Name` headers now REQUIRED; `x-mcp-header` custom parameter mirroring added (SEP-2243).
- `ttlMs` and `cacheScope` REQUIRED on `tools/list`, `prompts/list`, `resources/list`, `resources/read`, `resources/templates/list` via `CacheableResult` (SEP-2549).
- Resource-not-found error code changed `-32002` → `-32602`.
- Error code range policy: `-32020`…`-32099` reserved for the spec; `HeaderMismatch` `-32001`→`-32020`, `MissingRequiredClientCapability` `-32003`→`-32021`, `UnsupportedProtocolVersion` `-32004`→`-32022`.
- `extensions` field on `ClientCapabilities` / `ServerCapabilities`.
- OpenTelemetry `traceparent` / `tracestate` / `baggage` in `_meta` (SEP-414).

### Authorization-specific delta

| Change | SEP/PR | Direction |
| --- | --- | --- |
| RFC 9207 `iss`: AS **SHOULD** emit; clients **MUST** validate a present `iss` before redeeming | [SEP-2468](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2468) | New MUST for clients |
| DCR deprecated in favour of CIMD | [PR #2858](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2858) | Lifecycle change, no behaviour break |
| `application_type` required during DCR | [SEP-837](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/837) | New MUST for clients |
| Client credentials bound to issuing AS; MUST re-register on AS change | [SEP-2352](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2352) | New MUST for clients |

Note the spec flags a *future* tightening on `iss`:

> A future revision of this specification is expected to upgrade authorization server inclusion of `iss` from **SHOULD** to **MUST**. Implementers are encouraged to emit and validate `iss` now to ease that transition […]

**Deprecated in this revision:** Roots, Sampling, Logging (SEP-2577); HTTP+SSE transport reclassified as Deprecated (SEP-2596); `includeContext` values `"thisServer"` / `"allServers"`; DCR.

### How far is a `2025-11-25` client from working?

**Far.** Items 2 and 7 alone mean an old client cannot complete a single tool call: it will attempt `initialize` and get `404` + `-32601`. There is no graceful degradation path — the two eras are distinguished by probing, not negotiated:

> A client that supports both modern (per-request-metadata) MCP versions and a legacy version that requires an `initialize` handshake **MAY** detect which era the server implements by attempting a modern request first. On `400 Bad Request`, the client **SHOULD** inspect the response body before falling back […]

For a compatibility section: dual-era support means implementing *both* the handshake era and the stateless era side by side, not a shim. Given this is a portfolio exhibit, the defensible position is to implement `2026-07-28` only and return `UnsupportedProtocolVersionError` (`-32022`) with the supported list, which is exactly what the spec prescribes.

---

## Does CIMD require a publicly dereferenceable HTTPS document?

**Yes — but read carefully who has to publish it, because it probably isn't you.**

**The document itself must be public HTTPS.** There is no carve-out in the spec or the draft:

- MCP: "Clients **MUST** host their metadata document at an HTTPS URL"; "The `client_id` URL **MUST** use the "https" scheme and contain a path component".
- CIMD draft `-00` §3: "MUST have an 'https' scheme, MUST contain a path component […]".
- The draft's SSRF guidance actively works *against* a localhost carve-out: "Authorization servers SHOULD avoid fetching any URLs using private or loopback addresses and consider network policies or other measures to prevent making requests to these addresses." (§6.5)
- MCP's own security best practices repeat this for the AS side, listing `127.0.0.0/8`, `::1`, `169.254.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`, `fe80::/10` as ranges to block.

**The only dev accommodations are out-of-band or vendor-specific:**

- Draft §4.2 addresses the developer problem head-on — it names it verbatim ("how do I serve a Client ID Metadata Document at a publicly accessible https URL whilst developing my application on my localhost?") — and its answer is a **Client ID Metadata Document Service**: "a web service through which developers can acquire a stable URL to a Client ID Metadata Document." Providing one is **RECOMMENDED**, and an AS that restricts `redirect_uris` (e.g. to the `client_id` origin) **SHOULD** provide at least one service exempt from those restrictions. This is a hosted place to park a document — **not** a relaxation of the `https` scheme rule. The document is still public HTTPS; someone else just hosts it.
- Authlete implements a vendor-specific localhost carve-out (optional HTTP scheme, 600-second cache cap for localhost, forced re-retrieval for development). **This is a vendor extension, not spec-sanctioned.**

**The asymmetry that matters for this project.** CIMD documents are hosted by the **client**, not the resource server, and the *authorization server* is what dereferences them. `redirect_uris` inside a CIMD document are separately allowed to be loopback — the spec's own example lists `http://127.0.0.1:3000/callback` and `http://localhost:3000/callback`, and OAuth 2.1 permits "either `localhost` or use HTTPS" for redirect URIs. So:

- If your MCP client is **Claude Code**, the CIMD is already published by Anthropic at `https://claude.ai/oauth/claude-code-client-metadata`, and it declares `http://localhost/callback` and `http://127.0.0.1/callback`. You publish nothing.
- Your **authorization server** needs *outbound* HTTPS to `claude.ai` — that works from a laptop behind NAT.
- Your **MCP server** needs to be *inbound*-reachable only if you use a hosted Claude surface (Claude.ai web/Desktop/mobile), which reaches you from `160.79.104.0/21`. Claude Code running locally can hit `http://localhost:PORT/mcp` directly.

**Practical read for the exhibit:** public HTTPS deployment is **additive, not required**, for a CIMD demo driven by Claude Code against a locally-run Keycloak + local MCP server. It becomes **required** the moment you want a hosted Claude surface to connect, or the moment you write your own MCP *client* that must publish its own CIMD.

One real interop trap, worth a test case: Anthropic's docs state that Claude Code "declares `http://localhost/callback` and `http://127.0.0.1/callback` […] so your authorization server must accept both **with the port component ignored**." [RFC 8252 §7.3](https://datatracker.ietf.org/doc/html/rfc8252#section-7.3) requires port-agnostic matching for the IP-literal form; Anthropic asks for the same treatment of `localhost`, which RFC 8252 §8.3 discourages. This exact mismatch produced a real regression — [claude-code#37747](https://github.com/anthropics/claude-code/issues/37747), "client metadata document redirect_uris missing port causes auth failure for providers supporting CIMD" (opened 2026-03-23, closed 2026-05-24).

---

## Clause list for the attack suite

Fifteen "server MUST reject X" clauses, each citable as a one-liner in a named negative scenario. The first nine target the MCP resource server (this project); the last six target the authorization server (relevant if you self-author one, or as conformance probes against Keycloak).

| # | Scenario name | What the server must reject | Citation |
| --- | --- | --- | --- |
| 1 | `audience_confusion` | An access token whose audience is another resource server. → 401 | "MCP servers **MUST** only accept tokens specifically intended for themselves and **MUST** reject tokens that do not include them in the audience claim" — [authz/security-considerations §Access Token Privilege Restriction](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations#access-token-privilege-restriction) |
| 2 | `token_passthrough` | A token minted by an upstream API's AS, presented to the MCP server. → 401 | "MCP servers **MUST NOT** accept any tokens that were not explicitly issued for the MCP server." — [Security Best Practices §Token Passthrough](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices#token-passthrough) |
| 3 | `foreign_issuer_token` | A structurally valid token from an issuer not listed in this server's PRM. → 401 | "MCP servers **MUST NOT** accept or transit any other tokens." — [authz §Token Handling](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-handling) |
| 4 | `expired_token` | An expired or otherwise invalid token. → 401 (not 403, not 500) | "Invalid or expired tokens **MUST** receive a HTTP 401 response." — [authz §Token Handling](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-handling) |
| 5 | `token_in_query_string` | `?access_token=…` on the MCP endpoint. → reject; never honour | "Access tokens **MUST NOT** be included in the URI query string" — [authz §Token Requirements](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-requirements) |
| 6 | `insufficient_scope` | A valid token lacking the operation's scope. → 403 + `WWW-Authenticate: Bearer error="insufficient_scope", scope=…, resource_metadata=…` | [authz §Runtime Insufficient Scope Errors](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#runtime-insufficient-scope-errors); RFC 6750 §3.1 |
| 7 | `header_body_mismatch` | `Mcp-Name: foo` with body `params.name = "bar"` (after Base64 decode). → 400 + `-32020` | "Servers … **MUST** reject requests where the values specified in the headers do not match the corresponding values in the request body." — [streamable-http §Server Validation](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#server-validation) |
| 8 | `missing_required_header` | POST omitting `MCP-Protocol-Version`, `Mcp-Method`, or (where applicable) `Mcp-Name`. → 400 + `-32020` | "A required standard header (`MCP-Protocol-Version`, `Mcp-Method`, `Mcp-Name`) is missing." — [streamable-http §Server Validation](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#server-validation) |
| 9 | `protocol_version_skew` | `MCP-Protocol-Version: 2026-07-28` with `_meta` protocolVersion `2025-11-25`. → 400 + `HeaderMismatch` | "If the values do not match, the server **MUST** reject the request with `400 Bad Request` and a `HeaderMismatch` JSON-RPC error" — [streamable-http §Protocol Version Header](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#protocol-version-header) |
| 10 | `dns_rebinding_origin` | Request bearing an untrusted `Origin`. → **403 Forbidden** | "Servers **MUST** validate the `Origin` header on all incoming connections… servers **MUST** respond with HTTP 403 Forbidden." — [streamable-http §Security & Endpoint](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#security-endpoint) |
| 11 | `malformed_meta` | POST missing `io.modelcontextprotocol/protocolVersion` or `clientCapabilities` in `_meta`. → 400 + `-32602` | "A request missing any required field is malformed; the server **MUST** reject it with JSON-RPC error code `-32602`… the response status **MUST** be `400 Bad Request`." — [basic/index §`_meta`](https://modelcontextprotocol.io/specification/2026-07-28/basic/index#_meta) |
| 12 | `state_handle_hijack` | A valid token for user B presenting a state handle minted for user A. → reject | "MCP servers **MUST NOT** treat possession of a state handle as authentication." — [Security Best Practices §State Handle Hijacking](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices#state-handle-hijacking) |
| 13 | `cimd_id_url_mismatch` *(AS)* | A CIMD whose `client_id` differs from the URL it was fetched from. → `invalid_client` | "**MUST** validate that the fetched document's `client_id` matches the URL exactly" — [client-registration §Implementation Requirements](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration#implementation-requirements); CIMD draft-00 §4.1 |
| 14 | `cimd_redirect_uri_injection` *(AS)* | An authorization request whose `redirect_uri` is absent from the CIMD's `redirect_uris`, or matches only as a prefix/substring. → reject | "**MUST** validate redirect URIs presented in an authorization request against those in the metadata document" — [client-registration §Implementation Requirements](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/client-registration#implementation-requirements). Stronger RFC-level cite, **verified raw**: CIMD draft-00 §4.5 — "According to [RFC9700], the authorization server MUST require registration of redirect URIs, and MUST ensure that the redirect URI in a request is an exact match of a registered redirect URI." |
| 15 | `cimd_symmetric_secret` *(AS)* | A CIMD declaring `client_secret_basic`/`client_secret_post`/`client_secret_jwt`, or carrying `client_secret`. → reject | "the `token_endpoint_auth_method` property MUST NOT include `client_secret_post`, `client_secret_basic`, `client_secret_jwt`, or any other method based around a shared symmetric secret"; "`client_secret` and `client_secret_expires_at` properties MUST NOT be used" — CIMD draft-00 §4.1 |

Three more worth adding if the suite has room, all authorization-server-side:

| # | Scenario name | What must be rejected | Citation |
| --- | --- | --- | --- |
| 16 | `cimd_ssrf_loopback` *(AS)* | A `client_id` URL resolving to a loopback/link-local/private address (e.g. `http://169.254.169.254/…`). → refuse to fetch | CIMD draft-00 §6.5: "Authorization servers SHOULD avoid fetching any URLs using private or loopback addresses"; [MCP Security Best Practices §SSRF Against Authorization Servers](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices#ssrf-against-authorization-servers) |
| 17 | `as_metadata_issuer_spoof` *(client)* | Metadata fetched from `https://attacker.example/.well-known/oauth-authorization-server` declaring `"issuer": "https://honest.example"`. → **MUST** be rejected | [authorization-server-discovery §AS Metadata Discovery](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/authorization-server-discovery#authorization-server-metadata-discovery) |
| 18 | `mixup_iss_mismatch` *(client)* | An authorization response whose `iss` differs from the recorded issuer — including on error responses, where the client "**MUST NOT** act on or display `error`, `error_description`, or `error_uri`" | [authz §Authorization Response Validation](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#authorization-response-validation), RFC 9207 §2.4 |

---

## Open ambiguities

Things the spec genuinely does not settle. These are flagged as ambiguity, not resolved by inference.

1. **CIMD draft version lag.** MCP `2026-07-28` (published 2026-07-28) normatively cites `draft-ietf-oauth-client-id-metadata-document-**00**` (2025-10-08). But `-01` shipped 2026-03-02 and `-02` shipped **2026-07-06 — three weeks before the MCP revision**. `-01` added a mandate that metadata fetches return HTTP 200, expanded SSRF considerations, and added handling for client-metadata changes. The spec does not say whether implementations should track the latest draft or pin to `-00`. **An AS that enforces the `-01` HTTP-200 rule and an AS that follows `-00` will disagree about a `203`/`304` response.** Unresolved.

2. **`token_endpoint_auth_methods_supported` must contain `none` — but only per Anthropic, not per spec.** Claude selects CIMD only when AS metadata advertises *both* `client_id_metadata_document_supported: true` *and* `"none"` in `token_endpoint_auth_methods_supported`. The MCP spec nowhere states this. It is a real-world interop requirement that broke Keycloak ([#49730](https://github.com/keycloak/keycloak/issues/49730)) and is not derivable from the normative text. Treat as a client-specific constraint you must satisfy but cannot cite.

3. **Discovery-mechanism asymmetry.** The server MUST implement **one of** {`WWW-Authenticate` `resource_metadata`, well-known URI}; the client MUST support **both**. A server that publishes only the well-known URI and returns a bare 401 is conformant, but Anthropic's docs describe well-known probing as a "fallback" that "only works when your platform serves `/.well-known/*` paths". The spec does not say which a server *should* prefer.

4. **Which well-known path, when both could serve.** For a resource at `https://example.com/mcp`, the spec sanctions both `/.well-known/oauth-protected-resource/mcp` and `/.well-known/oauth-protected-resource` and specifies a *client* probe order, but does not say what a server should do if it serves both with different content, nor how a client should behave on a conflict.

5. **`resource` parameter enforcement is one-sided.** Clients **MUST** send `resource` "regardless of whether authorization servers support it," and servers **MUST** validate audience — but nothing says what a server does when the AS silently ignored `resource` and issued a token with no `aud`. Is an audience-less token "not issued specifically for them"? The text implies yes (reject), but never says so.

   **Verified raw, and it makes the gap worse rather than better:** RFC 8707 §2 makes audience restriction only a **SHOULD** on the AS ("The authorization server SHOULD audience-restrict issued access tokens to the resource(s) indicated by the `resource` parameter"), and §2.2 puts acceptable `resource` values "at its sole discretion based on local policy or configuration." So an AS that ignores `resource` outright is *conformant to RFC 8707*, while the MCP resource server is under a hard MUST to reject anything not issued for it. The two specs do not meet. **Live design question for this project, and it is not academic:** the choice of AS decides whether clause #1 of the attack suite is testable at all. Whichever AS is picked — Keycloak included — confirm it honours `resource` and emits a restricted `aud` *before* committing, because CIMD support and RFC 8707 support are independent features. Recommended resolution for our server: reject audience-less tokens (fail closed) and say so in the ADR, since the alternative is accepting any token the AS ever minted.

6. **CIMD required-field divergence.** MCP requires `client_id`, `client_name`, `redirect_uris`; the draft requires only `client_id`. An AS validating against the draft accepts documents an MCP-conformant AS rejects. Neither document acknowledges the other's list.

7. **Localhost `redirect_uri` port matching.** The spec acknowledges CIMD "cannot prevent `localhost` URL impersonation by themselves" and prescribes only UI countermeasures (warnings, hostname display). It does **not** specify port-agnostic matching for `localhost` — RFC 8252 §7.3 mandates it only for the IP-literal `127.0.0.1` form and §8.3 discourages `localhost` entirely. Anthropic requires port-agnostic matching for both. This gap caused a shipped regression.

8. **DCR removal timeline.** DCR is Deprecated with a ≥12-month window (so ≥ 2027-07-28), but no revision is named as its removal point. Planning a DCR fallback with a known sunset date is not possible from the spec.

9. **Notification POST header requirements are explicitly undefined.** The transport page states outright: "header requirements for notification POSTs are not defined by this revision." Combined with "This revision of the core protocol defines no client-to-server *notifications* over Streamable HTTP," this is dead code today — but an extension that adds one hits undefined behaviour.

---

## Confidence notes

**High confidence (raw page text retrieved; quotes are verbatim):** every quote attributed to `modelcontextprotocol.io` — the revision landing page, versioning, changelog, `basic/authorization`, `client-registration`, `authorization-server-discovery`, `security-considerations`, `basic/transports/streamable-http`, `basic/index`, and the security best-practices page. These fetches returned complete markdown, not summaries.

**High confidence (structured API data):** all GitHub issue numbers, titles, states, and dates — retrieved via `gh issue view --json`, not scraped.

**Verified verbatim against raw source (2026-08-06, follow-up pass — `curl` of the canonical plain-text documents, no summarising layer):**
- **RFC 9728 §3.1** path-insertion rule — quote is exact, from <https://www.rfc-editor.org/rfc/rfc9728.txt>. The RFC's own worked example confirms the direction: resource identifier `https://resource.example.com/resource1` → `GET /.well-known/oauth-protected-resource/resource1`. Insertion between host and path, *not* appending. Safe to implement from.
- **RFC 8707 §2 and §2.2** — quotes exact, from <https://www.rfc-editor.org/rfc/rfc8707.txt>. Two clauses that sharpen [Open ambiguity #5](#open-ambiguities) and were not in the first pass: audience restriction is only a **SHOULD** on the AS — "The authorization server SHOULD audience-restrict issued access tokens to the resource(s) indicated by the `resource` parameter" — and §2.2 makes acceptable `resource` values "at its sole discretion based on local policy or configuration." A conformant AS may therefore ignore `resource` entirely and still issue a token. This is *why* the resource-server-side audience MUST is the load-bearing control.
- **CIMD draft `-00` §3** (URL constraints), **§4.1** (required `client_id` + prohibited symmetric-secret fields), **§4.2** (Client ID Metadata Document Services), **§4.3** (abort on fetch failure), **§4.4** (caching), **§4.5** (exact-match redirect URI registration), **§6.2** (client authentication), **§6.5** (SSRF) — all quotes exact, from <https://www.ietf.org/archive/id/draft-ietf-oauth-client-id-metadata-document-00.txt>. Confirmed: the draft requires **only** `client_id`; `client_name` and `redirect_uris` are genuinely MCP-level tightenings, so [Open ambiguity #6](#open-ambiguities) stands.
- Also picked up in that pass, not previously recorded: **§6.6** recommends a **5 kilobyte** maximum response size for client metadata documents — which is exactly the limit Auth0's docs advertise, corroborating that their implementation tracks this draft.

**Medium confidence — quotes came through a summarising fetch, so wording may be lightly paraphrased even where quotation marks appear:**
- **RFC 9728** §5.1 `resource_metadata`, §7.4, §7.6, §7.7. (§3.1 has since been verified — see above.)
- **CIMD draft `-01`** change history and `-02` publication date (2026-07-06).
- The `invalid_target` "should reject the request" phrasing as rendered in §3.1 above. RFC 8707 §2 defines the error code verbatim as "The requested resource is invalid, missing, unknown, or malformed" and offers it for use "in response to an authorization request or access token request"; the surrounding obligation language was not located raw and may be looser than quoted.

**Not independently verified — cited only as the MCP spec references them:** RFC 7591, RFC 6749, RFC 6750, RFC 9207, RFC 9700, RFC 3986, RFC 8252, RFC 9110, and OAuth 2.1 `draft-ietf-oauth-v2-1-13`. Every claim about these in this document is a claim about *what MCP says about them*.

**Vendor claims — single-source, vendor-published:** Authlete (3.0.22 / Nov 2025), Stytch (2025-10-17, self-described beta), WorkOS AuthKit (2025-12-08), Descope (2026-01-27, "generally available"), Scalekit. These are announcements, not conformance tests. **None of them has been verified end-to-end against a real MCP client by this research.**

**Weakest link — Auth0's status is genuinely unclear.** oauth.net lists Auth0 as "coming soon," while Auth0's own docs page describes a live `Client ID Metadata Document Registration` tenant toggle with validation limits (5KB CIMD, 12KB JWKS) and notes rate limits are "future." The docs page carries no GA/EA badge and no date. Do not plan around Auth0 CIMD without confirming directly.

**Second-hand, flagged as such:** the claim that Microsoft Entra ID's refusal to support CIMD/DCR is a deliberate architectural decision on SSRF and attestation grounds comes from a community repository ([merill/mcp-entra-design](https://github.com/merill/mcp-entra-design/blob/main/docs/03-entra-no-dcr.md)), **not** from Microsoft documentation. The *observable* fact — Entra supports neither — is corroborated by Anthropic's own troubleshooting note about `AADSTS9010010` requiring an Application ID URI registration. The *reasoning* is not primary-sourced.

**Sources I could not fully resolve:**
- **Keycloak's CIMD stability level is not cleanly stated anywhere.** Issue [#45106](https://github.com/keycloak/keycloak/issues/45106) is titled "**Experimental** Support" and closed 2026-06-23, but is tagged to milestone **26.8.0** while the fix in [#49730](https://github.com/keycloak/keycloak/issues/49730) is labelled `release/26.7.0`. The 26.7.0 announcement discusses CIMD in prose without a preview/experimental badge in that section, yet the feature is gated behind `--features=cimd`, which in Keycloak conventionally denotes preview. **Treat as preview-quality.** The Keycloak release-notes fetch returned a summary rather than raw text; the exact wording should be re-read before you depend on it.
- **No conformance suite or interop report** for `2026-07-28` authorization was located. There is no primary source confirming any specific AS + MCP-server + Claude triple has been tested end to end against *this* revision — the vendor CIMD announcements all predate it and reference `2025-11-25`.
- **The `resource` parameter's treatment by each shipping IdP** was not checked. Supporting CIMD and supporting RFC 8707 audience restriction are independent; an IdP can do the first and not the second, which would leave clause #1 in the attack suite untestable against real tokens.

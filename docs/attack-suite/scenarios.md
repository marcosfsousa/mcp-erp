# The attack suite

<!-- Rendered from docs/attack-suite/scenarios.yaml by tests/attack_suite/scenario_table.py. Do not edit. -->
<!-- `Seed renders clean` re-renders this file and refuses a diff. -->

34 named scenarios: what each one stops, the clause or decision behind it, and the exact deletion that would let it through.

## What the rows are

| | Rows |
| --- | --- |
| basis `adr` | 12 |
| basis `clause` | 19 |
| basis `seam` | 3 |
| strength `MUST` | 11 |
| strength `MUST NOT` | 6 |
| strength `SHOULD` | 2 |
| **asserted** | 33 |
| **documented** | 1 |
| may never be downgraded | 11 |

## The scenarios

| Scenario | Basis | Strength | Status | Prevents |
| --- | --- | --- | --- | --- |
| [`audience_confusion`](#audience_confusion) | clause | `MUST` | asserted | A token legitimately issued for another resource server is replayed at us. |
| [`token_passthrough`](#token_passthrough) | clause | `MUST NOT` | asserted | A token minted by an upstream API's authorization server is presented to us. |
| [`foreign_issuer_token`](#foreign_issuer_token) | clause | `MUST NOT` | asserted | A structurally valid token from an issuer absent from our protected resource metadata. |
| [`token_expired`](#token_expired) | clause | `MUST` | asserted | An expired token is accepted after its lifetime ends. |
| [`signature_invalid`](#signature_invalid) | clause | `MUST` | asserted | A token whose payload was altered after signing is accepted. |
| [`unknown_key`](#unknown_key) | clause | `MUST` | asserted | A token signed with a key absent from the issuer's key set is accepted. |
| [`malformed_token`](#malformed_token) | clause | `MUST` | asserted | A structurally invalid credential produces a 500 rather than a 401. |
| [`audience_missing`](#audience_missing) | adr | *none* | asserted | A token the authorization server minted with no audience at all is accepted. |
| [`token_in_query_string`](#token_in_query_string) | clause | `MUST NOT` | asserted | A token supplied as `?access_token=` is honoured, putting it in logs and referrers. |
| [`insufficient_scope`](#insufficient_scope) | clause | `SHOULD` | asserted | A valid token lacking the operation's scope reaches the operation. |
| [`scope_exact_match`](#scope_exact_match) | adr | *none* | asserted | A token whose scope merely resembles the required one is accepted. |
| [`header_body_mismatch`](#header_body_mismatch) | clause | `MUST` | asserted | A header claiming one method or name while the body carries another. |
| [`missing_required_header`](#missing_required_header) | clause | `MUST` | asserted | A POST omitting a required standard header is processed anyway. |
| [`protocol_version_skew`](#protocol_version_skew) | clause | `MUST` | asserted | A version header disagreeing with the body's declared protocol version. |
| [`malformed_meta`](#malformed_meta) | clause | `MUST` | asserted | A POST missing a required `_meta` field is processed as well-formed. |
| [`dns_rebinding_origin`](#dns_rebinding_origin) | clause | `MUST` | asserted | A malicious page in a victim's browser reaching a server on their machine. |
| [`state_handle_hijack`](#state_handle_hijack) | clause | `MUST NOT` | asserted | Possession of another person's requisition identifier authorizing a write against it. |
| [`get_stream_removed`](#get_stream_removed) | clause | `SHOULD` | asserted | A standalone server-initiated stream surviving into the modern era. |
| [`pkce_downgrade_plain`](#pkce_downgrade_plain) | adr | *none* | asserted | A client downgrading its challenge method to `plain`. |
| [`password_grant_refused`](#password_grant_refused) | clause | `MUST NOT` | asserted | Username and password going straight to the token endpoint. |
| [`refresh_token_replay`](#refresh_token_replay) | clause | `MUST` | asserted | A stolen refresh token being redeemed twice. |
| [`mixup_iss_mismatch`](#mixup_iss_mismatch) | clause | `MUST NOT` | asserted | An attacker-controlled authorization server having our client redeem an honest server's code. |
| [`row_probe_indistinguishable`](#row_probe_indistinguishable) | adr | *none* | asserted | Probing for the existence of requisitions in another cost centre. |
| [`list_partition_scoped`](#list_partition_scoped) | adr | *none* | asserted | A listing returning rows from every cost centre because the caller cleared the whole-call gate. |
| [`auth_bypass_via_method_header_mismatch`](#auth_bypass_via_method_header_mismatch) | adr | *none* | asserted | Claiming `server/discover`'s unauthenticated exemption on a header while the body carries a tool call. |
| [`unsupported_protocol_version`](#unsupported_protocol_version) | adr | *none* | asserted | The supported-version list answering a caller who has presented no credential. |
| [`retry_after_role_denial`](#retry_after_role_denial) | adr | *none* | asserted | A refusal that instructs the client to acquire a scope it already holds, looping it. |
| [`retry_after_sod_denial_same_person`](#retry_after_sod_denial_same_person) | adr | *none* | asserted | A segregation-of-duties refusal that a blind retry by the same person satisfies. |
| [`retry_after_sod_denial_other_person`](#retry_after_sod_denial_other_person) | adr | *none* | asserted | A segregation-of-duties refusal whose stated remedy is false. |
| [`double_approval_via_batch_retry`](#double_approval_via_batch_retry) | adr | *none* | asserted | A model retrying a whole batch and approving an item twice. |
| [`threshold_split_evasion`](#threshold_split_evasion) | adr | *none* | documented | Nothing. Named because it works. |
| [`legacy_unauthenticated_refused`](#legacy_unauthenticated_refused) | seam | *none* | asserted | The always-on legacy leg accepting calls with no token. |
| [`legacy_underscoped_same_denial_class`](#legacy_underscoped_same_denial_class) | seam | *none* | asserted | The legacy leg producing a weaker refusal than its modern twin. |
| [`legacy_discover_exemption_unavailable`](#legacy_discover_exemption_unavailable) | seam | *none* | asserted | A legacy-era request claiming the unauthenticated `server/discover` exemption. |

## Each scenario, with its citation and its removal

### `audience_confusion`

A token legitimately issued for another resource server is replayed at us.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may never be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization/security-considerations#access-token-privilege-restriction>

> MCP servers MUST only accept tokens specifically intended for themselves and MUST reject tokens that do not include them in the audience claim

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Delete the `aud` comparison in token validation.

**Note** Testable only because ADR-0007 provisions `mcp-conformance-decoy`, a real client for another resource. Keycloak ignores RFC 8707 `resource`, so the resource server's own check is the load-bearing control.

### `token_passthrough`

A token minted by an upstream API's authorization server is presented to us.

**Basis** clause · **Strength** `MUST NOT` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices#token-passthrough>

> MCP servers MUST NOT accept any tokens that were not explicitly issued for the MCP server.

**Retrieved** 2026-08-12

**Removal that makes the attack succeed** Accept any token that verifies, regardless of which issuer minted it.

**Note** Uses the `mcp-erp-neighbour` realm — a real issuer with its own keys, not an invented token.

### `foreign_issuer_token`

A structurally valid token from an issuer absent from our protected resource metadata.

**Basis** clause · **Strength** `MUST NOT` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-handling>

> MCP servers MUST NOT accept or transit any other tokens.

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Skip the `iss` check against the configured issuer.

### `token_expired`

An expired token is accepted after its lifetime ends.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may never be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-handling>

> Invalid or expired tokens MUST receive a HTTP 401 response.

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Delete the `exp` comparison.

**Note** Real ten-second wait, not a fake clock — ADR-0007's `mcp-expiry-probe`. ADR-0006 pins zero leeway on `exp` precisely so this stays a ten-second test.

### `signature_invalid`

A token whose payload was altered after signing is accepted.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-handling>

> Invalid or expired tokens MUST receive a HTTP 401 response.

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Verify the token's claims without verifying its signature.

### `unknown_key`

A token signed with a key absent from the issuer's key set is accepted.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-handling>

> Invalid or expired tokens MUST receive a HTTP 401 response.

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** On an unknown key identifier, fall through to any cached key instead of refetching and failing closed.

**Note** The one scenario exercising ADR-0006's miss-driven key-set refetch and its cooldown.

### `malformed_token`

A structurally invalid credential produces a 500 rather than a 401.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-handling>

> Invalid or expired tokens MUST receive a HTTP 401 response.

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Let the parse error propagate instead of mapping it to a refusal.

### `audience_missing`

A token the authorization server minted with no audience at all is accepted.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may never be downgraded

**Decided by** ADR-0006 §Refusals disclose the caller's own token, and nothing else

**On the citation** Deliberately not a clause. Research 0003 ambiguity #5 establishes that nothing in the specification states what a server does with an audience-less token. Fail-closed is our decision, not a conformance tick.

**Removal that makes the attack succeed** Treat an absent `aud` as "not addressed to anyone else" and allow it.

**Note** Testable because ADR-0007 provisions `mcp-conformance-bare`, a client with no audience mapper.

### `token_in_query_string`

A token supplied as `?access_token=` is honoured, putting it in logs and referrers.

**Basis** clause · **Strength** `MUST NOT` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#token-requirements>

> Access tokens MUST NOT be included in the URI query string

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Read the bearer token from the query string when the header is absent.

**Note** ADR-0006 publishes `bearer_methods_supported: ["header"]`, which makes this a contract we keep rather than a behaviour we happen to exhibit.

### `insufficient_scope`

A valid token lacking the operation's scope reaches the operation.

**Basis** clause · **Strength** `SHOULD` · **Status** asserted · **Floor** may never be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#runtime-insufficient-scope-errors>

> When a client makes a request with an access token with insufficient scope during runtime operations, the server SHOULD respond with: HTTP 403 Forbidden status code (per RFC 6750 Section 3.1) … WWW-Authenticate header with the Bearer scheme and additional parameters: error="insufficient_scope" … scope="required_scope1 required_scope2" … resource_metadata - the URI of the Protected Resource Metadata document

*The quote above elides, where it reads ….*

**Retrieved** 2026-08-12

**Also** RFC 6750 §3.1

**Removal that makes the attack succeed** Return the tool result without intersecting granted scope first.

**Note** Asserts the challenge's shape, not just the 403 — `error="insufficient_scope"`, `scope=`, `resource_metadata=`. The `scope=` strings are `erp.read`, `erp.write` and `erp.decide`, settled by #11 (ADR-0012) on 2026-08-16 and derived from the capability each tool declares — never hand-written here. STRENGTH DISCREPANCY: research 0003 characterised the clause list as "server MUST reject X"; the actual text is SHOULD. The row is unchanged — ADR-0006 commits us to this shape regardless — but the table must not render it as a MUST. NAMING: this scenario's name is character-identical to the layer-2 Reason value `insufficient_scope` and is a different kind of thing — a stable test identifier, not a Reason.value. Nothing binds them and no drift check relates them. ADR-0013 split the reason vocabulary by layer; this name did not move with it. (Added 2026-08-18 by #12.)

### `scope_exact_match`

A token whose scope merely resembles the required one is accepted.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0012 §Unrecognised scopes are inert

*Context, and not the basis:*
> RFC 6749 §3.3 — "The value of the scope parameter is expressed as a list of space-delimited, case-sensitive strings." (retrieved 2026-08-16)

**On the citation** The RFC sentence is definitional and carries no normative keyword, so it cannot be this row's basis without asserting a strength its quote does not contain. It also governs how the authorization server represents the parameter, not how a resource server compares it. Exact case-sensitive membership is our decision; the clause is context.

**Removal that makes the attack succeed** Replace exact case-sensitive set membership with any laxer comparison.

**Note** One row, not two: the deletion is a single site — the comparison expression — so the test asserts both variants against it. `ERP.READ` must not satisfy `erp.read` (case), and `hr.read` must not satisfy `erp.read` (namespace). Splits from insufficient_scope, whose removal skips the intersection entirely rather than running it wrongly. ~~Testable without new realm state: ADR-0007's `mcp-conformance-decoy` already holds another resource's scope.~~ NOT TESTABLE WITHOUT NEW REALM STATE — found 2026-08-20 by #44, running it. The decoy's token carries somebody else's audience by construction, which is exactly what makes it `audience_confusion`'s instrument, so it is refused at gate 4 and never reaches the comparison this row is about. Nor can the ordinary client mint a lookalike: Keycloak validates requested scopes against the client's own assignments and answers `invalid_scope`, so `ERP.READ` cannot be asked for where it is not registered. ADR-0007 grew a fifth client for it, `mcp-scope-lookalike` — our audience, and two optional scopes that are not capability scopes of ours — on the same terms as the other three: one client, one refusal it makes reachable. The row is unchanged; what was wrong was the sentence about how to reach it, which was written before the server existed.

### `header_body_mismatch`

A header claiming one method or name while the body carries another.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may never be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#server-validation>

> Servers … MUST reject requests where the values specified in the headers do not match the corresponding values in the request body.

*The quote above elides, where it reads ….*

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Route on the header without comparing it to the body.

**Note** Includes the Base64 sentinel form of `Mcp-Name`, which is where a naive comparison passes wrongly.

### `missing_required_header`

A POST omitting a required standard header is processed anyway.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#server-validation>

> These headers are REQUIRED for compliance. … When rejecting a request due to header validation failure, servers MUST return HTTP status 400 Bad Request and MUST include a JSON-RPC error response … Validation failure conditions include: … A required standard header (MCP-Protocol-Version, Mcp-Method, Mcp-Name) is missing.

*The quote above elides, where it reads ….*

**On the quote, corrected** Spot-check 2026-08-12: the original quote was the failure-condition bullet alone, which is descriptive rather than normative. Paired with the REQUIRED statement and the MUST-return sentence that make it binding.

**Retrieved** 2026-08-12

**Removal that makes the attack succeed** Default a missing header from the body instead of refusing.

### `protocol_version_skew`

A version header disagreeing with the body's declared protocol version.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#protocol-version-header>

> If the values do not match, the server MUST reject the request with 400 Bad Request and a HeaderMismatch JSON-RPC error

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Read the version from the header and ignore `_meta`.

### `malformed_meta`

A POST missing a required `_meta` field is processed as well-formed.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/index#_meta>

> A request missing any required field is malformed; the server MUST reject it with JSON-RPC error code -32602 … the response status MUST be 400 Bad Request.

*The quote above elides, where it reads ….*

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Make `_meta` optional in the request model.

### `dns_rebinding_origin`

A malicious page in a victim's browser reaching a server on their machine.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may never be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#security-endpoint>

> Servers MUST validate the Origin header on all incoming connections … servers MUST respond with HTTP 403 Forbidden.

*The quote above elides, where it reads ….*

**Retrieved** 2026-08-06

**Removal that makes the attack succeed** Skip the allow-list check when `Origin` is present.

**Note** ADR-0006's honest limit — no client in this exhibit sends `Origin`, so this negative scenario is the only thing that exercises the check at all.

### `state_handle_hijack`

Possession of another person's requisition identifier authorizing a write against it.

**Basis** clause · **Strength** `MUST NOT` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices#state-handle-hijacking>

> MCP servers MUST NOT treat possession of a state handle as authentication.

**Retrieved** 2026-08-12

**Removal that makes the attack succeed** Take the decision before the chain has permitted it, so a guessed identifier reaches the write.

**Note** Write path. Asserts the refusal AND that state is unmodified — the only row in the suite asserting a refused write changed nothing. Splits from row_probe_indistinguishable, which is the read path. See ADR-0003's amendment: identifiers are deliberately guessable, so this is reached by guessing rather than by being handed the identifier. Removal corrected 2026-08-19 by #40, which built the write it names and asserted it. It read "Look the requisition up by identifier alone, without the cost-centre predicate" — written at #9, before ADR-0013 made that the design rather than the removal: the store loads by identifier alone and layer 2 refuses, so the empty join and the foreign row converge at one return site instead of in SQL. Pushing the predicate down would reach the same answer by a mechanism no test in tests/authorization can see. The deletion that makes this attack succeed against the shipped code is deciding before the chain permits. Same clause, same split, same count.

### `get_stream_removed`

A standalone server-initiated stream surviving into the modern era.

**Basis** clause · **Strength** `SHOULD` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http#earlier-streamable-http-revisions>

> A server that supports only this revision and receives such traffic from an older client SHOULD respond as follows: … HTTP GET or DELETE to the MCP endpoint: respond with 405 Method Not Allowed.

*The quote above elides, where it reads ….*

**Retrieved** 2026-08-12

**Removal that makes the attack succeed** Route a GET carrying a modern `MCP-Protocol-Version` to the handshake-era transport, which answers it with a stream.

**Note** From ADR-0001's attack-suite input — 405 on GET and DELETE. STRENGTH DISCREPANCY: SHOULD, not MUST. The hard MUST on this page is narrower — "The server MUST provide a single HTTP endpoint path … that supports POST" — and does not forbid GET. The revision's own change note ("Removal of the GET stream endpoint") is descriptive, not normative. TWO DEFECTS CLOSED 2026-08-20 by #44, both raised from #37 and neither a consequence of that cut. (1) The row carried `status: asserted` with nothing behind it — no request in any suite issued a GET at all — which is a second `documented` row wearing the wrong label. It has a test now, `tests/attack_suite/test_get_stream_removed.py`, and the bijection check that landed with it is what would catch the next one. (2) THE 405 IS REACHABLE ONLY WITH A TOKEN ON THE MODERN LEG. Executed against Compose: unauthenticated GET answers `401` + challenge, because ADR-0006's gate 4 precedes the transport; GET with a token and a version header answers `405` + `Allow: POST`; GET with a token and no version header opens a legacy `text/event-stream`; DELETE with a token answers `405`. The citation describes the second line, so the test carries a real token, and map constraint `#6` was amended to say the 405/401 split out loud. The legacy stream is not a defect of this row: ADR-0008 records that the substrate offers no way to switch it off and ADR-0009 authorises it, which is why `prevents` scopes itself to the modern era. REMOVAL REWORDED in the same commit. It read "Register a GET route on the MCP endpoint", which named a deletion nothing could observe: `app.py` mounts the transport under a Starlette `Route` with no method restriction, so GET already reaches the package on both legs and a second registration could never be reached. Same defect #38 found on legacy_underscoped_same_denial_class, same rule — a removal nobody can perform is a row nobody can falsify — and the deletion recorded now is the one the assertion actually rests on: era routing sends a version-bearing GET to the modern entry, where it is refused, instead of to the transport that would open the stream.

### `pkce_downgrade_plain`

A client downgrading its challenge method to `plain`.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0007 §Every client is public, and the weak challenge method is refused

*Context, and not the basis:*
> MCP Security Considerations 2026-07-28 §Authorization Code Protection — "MCP clients MUST use the S256 code challenge method when technically capable, as required by OAuth 2.1 Section 4.1.1"; OAuth 2.1 draft-ietf-oauth-v2-1-13 §4.1.1 — "If the client is capable of using S256, it MUST use S256, as S256 is Mandatory To Implement (MTI) on the server." Both retrieved 2026-08-12. CITED AS CONTEXT, NOT BASIS: the MUST governs clients, and this row asserts a SERVER refusal. Nothing in either document requires an authorization server to reject `plain`. Rewording the row could not fix the mismatch, because the clause simply does not govern what we assert — the obligation is ADR-0007's per-client realm pin.

**Removal that makes the attack succeed** Clear the per-client challenge-method pin **and** the `proof-key-for-code-exchange` client policy in the realm file. Either alone still refuses for the five clients the realm file declares, which is what this row's own test loops over. It is not true of the client the realm provisions from the hosted identity document: that one carries no attributes, so the policy is the whole of its refusal and clearing the policy alone is enough. That half is performed in tests/conformance/test_the_realm_refuses_the_provisioned_client_too.py.

**Note** ADR-0007's caveat is binding: the realm advertises both `plain` and `S256` because the pin is per client and discovery does not reflect per-client policy. This asserts the server REFUSES a plain challenge for our client — not that the metadata omits `plain`, which it will not. REMOVAL WIDENED 2026-08-20 by #44, on merging #46. The pin was one thing when this row was written and is two now: #46 found that a per-client attribute cannot reach a client the realm does not contain — its conformance client is provisioned from a hosted document and carries no attributes, so it accepted `plain` and accepted no challenge at all — and added a `proof-key-for-code-exchange` client policy conditioned on `client-access-type: public`, carrying the `pkce-enforcer` executor. Both are live, so clearing either one leaves the other refusing, and a removal naming only the attribute would be a deletion somebody could perform with nothing to show for it. REMOVAL HALVED 2026-08-21 by #85, and the removal above says so since #80. *Either alone still refuses* holds for THE FIVE CLIENTS THE REALM FILE DECLARES, which is what this row's test loops over. The policy half alone is falsifiable against the client provisioned from the hosted identity document, and that client is in no file — so clearing the policy leaves every assertion in tests/attack_suite/ green. #85 wrote that falsifier, in tests/conformance/test_the_realm_refuses_the_provisioned_client_too.py, because minting that client needs egress and the attack suite job takes none. The row stays here and one of its two removals is performed there.

### `password_grant_refused`

Username and password going straight to the token endpoint.

**Basis** clause · **Strength** `MUST NOT` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://datatracker.ietf.org/doc/html/rfc9700#section-2.4>

> The resource owner password credentials grant [RFC6749] MUST NOT be used.

**Retrieved** 2026-08-12

**Removal that makes the attack succeed** Enable Direct Access Grants on any client in the realm file.

**Note** Turns a flow we did not use into a flow the realm refuses. Source is RFC 9700 rather than the obvious document, deliberately: **OAuth 2.1 draft-13 removes this grant by omission.** It defines the flow nowhere, so there is no sentence in it to quote — an absence cannot be cited. RFC 9700 §2.4 carries the only explicit prohibition at a pinned revision, and ADR-0007 already cites RFC 9700 for refresh rotation. Recorded so a reader does not wonder why OAuth 2.1 was skipped.

### `refresh_token_replay`

A stolen refresh token being redeemed twice.

**Basis** clause · **Strength** `MUST` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://datatracker.ietf.org/doc/html/rfc9700#section-4.14.2>

> Authorization servers MUST utilize one of these methods to detect refresh token replay by malicious actors for public clients: sender-constrained refresh tokens … refresh token rotation.

*The quote above elides, where it reads ….*

**Retrieved** 2026-08-11

**Removal that makes the attack succeed** Turn off refresh token rotation, or allow reuse, in the realm file.

**Note** Binding because every client here is public. Asserts that a replayed refresh token revokes the grant. Not in the OAuth 2.1 draft — RFC 9700 is the citation, per ADR-0007's precision note.

### `mixup_iss_mismatch`

An attacker-controlled authorization server having our client redeem an honest server's code.

**Basis** clause · **Strength** `MUST NOT` · **Status** asserted · **Floor** may be downgraded

**Clause** <https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization#authorization-response-validation>

> MUST NOT act on or display error, error_description, or error_uri

**Retrieved** 2026-08-06

**Also** RFC 9207 §2.4

**Removal that makes the attack succeed** Skip comparing the response's `iss` against the issuer recorded before redirecting.

**Note** The suite's only client-side row, adopted because we author the conformance client. Rides the `mcp-erp-neighbour` realm. Covers the error-response case, which is the half implementations usually miss. `as_metadata_issuer_spoof` was refused on cost — a hostile metadata host for one row. THE REMOVAL IS A DELETION IN `tests/`, AND THAT IS WHAT A CLIENT-SIDE ROW MEANS HERE. Recorded 2026-08-20 by #44, which built the check: the party under this obligation is a client, the client this project authors today is the token helper `tests/tokens.py`, and the deletion is the `iss` comparison in its `authorization_code`. Every other row in this file names a deletion in `src/` or in a committed realm file, so a reader who assumed that uniformly would look for this one in the wrong tree. THE SECOND CLIENT KEEPS THE SAME CLAUSE, AND ITS FALSIFIER IS NOT IN THIS DIRECTORY. #78 put the attribution ahead of `redirect_error` in the conformance client's `_callback` — the package validates RFC 9207 `iss` on the success path, but a refusal carries no code and so never reaches it — and asserted it in `tests/conformance/test_a_refusal_is_attributed_before_it_is_repeated.py`. It lives there because the client under test is that directory's and the declarations collected here are read out of this directory's source, so the cross-reference is this sentence rather than a `@exercises` this row could count. Both clients, one clause, two falsifiers. THE ORDER IS THE ASSERTION: `iss` is compared before `error` is read, which is what the quoted MUST NOT amounts to — a client that reads the error first reports another server's words as though they answered its own request.

### `row_probe_indistinguishable`

Probing for the existence of requisitions in another cost centre.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0002 §Disclose the shape of the API; never the contents of the database

**Removal that makes the attack succeed** Return a distinguishable refusal for "exists but not yours" versus "never existed".

**Note** Read path, NAMED resource. Asserts byte-identical `not_found` for "exists but not yours" and "never existed". Constant time is not measured here and is not claimed. Splits from state_handle_hijack, which is the write path; splits from list_partition_scoped, which is the discovered half of the same contract.

**How this row was narrowed** Narrowed 2026-08-18 by #12: this note read "AND indistinguishable timing". Timing indistinguishability is unprovable over HTTP against Compose — container scheduling and garbage collection swamp the signal — and a flaky assertion in a required job gets disabled. What is asserted is byte-identity on the wire; the layer-2 counterpart is a single-return-site property asserted structurally in tests/authorization/. ADR-0002 is narrowed to match. This reverses a project commitment, not a normative clause, so no normative-register row is owed. See ADR-0013 §Indistinguishability is byte-identity, at two altitudes. Moved out of `note` 2026-08-20 by #92, which built the renderer: a cell carrying the withdrawn claim's own words can be skimmed as an assertion.

### `list_partition_scoped`

A listing returning rows from every cost centre because the caller cleared the whole-call gate.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0013 §Named versus discovered — the refusal contract

**Removal that makes the attack succeed** Return the unfiltered result set after the whole-call gate permits, without evaluating row scoping per row.

**Note** Read path, DISCOVERED resources — the other half of the contract row_probe_indistinguishable covers for named ones. Asserts set equality over returned identifiers for a principal without the bypass role, and the widened set for one holding `auditor`. Declared 2026-08-18 by #12 because nothing asserted it. ADR-0013 gives the policy function three entry points, and the type system closes accidental omission of the resource but NOT the wrong entry point: a handler that takes a whole-call permit and lists every partition type-checks cleanly. That residual is structurally untestable in tests/authorization/, since choosing the entry point is a handler obligation and handlers are layer 3, which ejection deletes. So the falsifier has to live at the wire. Splits from row_probe_indistinguishable: that row's removal makes a named refusal distinguishable; this row's removal skips per-row evaluation entirely. Different deletions, so different rows.

### `auth_bypass_via_method_header_mismatch`

Claiming `server/discover`'s unauthenticated exemption on a header while the body carries a tool call.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may never be downgraded

**Decided by** ADR-0006 §The gate order is a security property, not a style choice

**Removal that makes the attack succeed** Move the exemption check ahead of header/body validation.

**Note** Covers gate step 3, which is a branch rather than a refusal. ADR-0006 says this is worth a scenario whichever order had been chosen — the order makes the attack structurally impossible rather than defended against.

### `unsupported_protocol_version`

The supported-version list answering a caller who has presented no credential.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0009 §The gate chain is not uniform across the two legs, and the shape gate is where it breaks

**On the citation** NOT A CLAUSE, AND THE REASON IS THIS FILE'S OWN RULE. Research 0003 and 0004 both paraphrase the behaviour — "return UnsupportedProtocolVersionError (-32022) with the supported list, which is exactly what the spec prescribes" — and a paraphrase is not a citation: no verbatim sentence has been read from the pinned revision, and a row cannot be published on a citation whose sentence has not been harvested. What is decided here rather than quoted is where the refusal sits: ADR-0009 establishes that era routing precedes the gate chain and that an unrecognised version reaches the modern entry, and ADR-0006 puts gate 4 in front of it. It becomes a clause row if the sentence is harvested; nothing the row asserts changes when it is.

**Removal that makes the attack succeed** Exempt an unrecognised `MCP-Protocol-Version` from gate 4, so the classifier's supported-version list answers a caller holding no token.

**Note** HELD OUT FROM #9 UNTIL 2026-08-20, and minted here. ADR-0010 §One candidate is held outside the thirty-one made it conditional on ADR-0009's seam assertions showing that a modern-era request declaring an unsupported version still reaches the gate chain — ADR-0009 having voided the earlier -32022 observation, because era routing precedes that chain entirely. #38 met the condition by hand and declined to mint the row, for three reasons that all land here: it moves counts three documents track, it needs a test to stay in bijection with, and its basis and removal are judgement calls this ticket owns. Confirmed against Compose while minting it: `MCP-Protocol-Version: 1999-01-01` with a matching envelope version routes to the modern entry (the session manager sends the header to the legacy path only for values in HANDSHAKE_PROTOCOL_VERSIONS), is refused `401` + challenge with no token, and answers `-32022` with `supported: ["2026-07-28"]` and the requested value echoed once past the token gate. SPLITS FROM protocol_version_skew, whose removal reads the version from the header and ignores `_meta`: that row is a request disagreeing with itself and is answered `-32020`. Here both halves agree on a revision this server does not implement, and the answer is the other code. WHAT THIS ROW DEFENDS IS THE ORDERING, NOT THE CLASSIFIER. `prevents` was drafted as two clauses and narrowed to one in the same commit, on this file's rule that a row records the exact removal that makes it pass: the second clause — a revision we do not implement being negotiated by assertion — is refused by the substrate's own classifier, and the deletion that would undo it is a change to era routing inside `mcp` 2.0.0, which nobody here can perform. So that half is the row's *precondition* and is asserted as one, and what the row is about is that the answer sits behind gate 4 — which is ours to lose.

### `retry_after_role_denial`

A refusal that instructs the client to acquire a scope it already holds, looping it.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0002 §Refusal shape follows the remedy

**Removal that makes the attack succeed** Return 403 with a `WWW-Authenticate` challenge for the missing-ERP-role case.

**Note** Asserts -31010 and that an identical retry does not help. Reachable only because ADR-0007 gives Priya Raman `approver` in Keycloak and no ERP role.

### `retry_after_sod_denial_same_person`

A segregation-of-duties refusal that a blind retry by the same person satisfies.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0002 §Surviving contact with a retrying client

**Removal that makes the attack succeed** Check segregation of duties against roles held rather than positions occupied on the chain.

### `retry_after_sod_denial_other_person`

A segregation-of-duties refusal whose stated remedy is false.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may never be downgraded

**Decided by** ADR-0002 §Surviving contact with a retrying client

**Removal that makes the attack succeed** Set `retry_as_other_person_helps` from a constant instead of from the decision.

**Note** Covers gate step 6. The row that keeps segregation of duties distinct from every other refusal — it asserts the remedy is true by acting on it.

### `double_approval_via_batch_retry`

A model retrying a whole batch and approving an item twice.

**Basis** adr · **Strength** *none* · **Status** asserted · **Floor** may be downgraded

**Decided by** ADR-0002 §Surviving contact with a retrying client

**Removal that makes the attack succeed** Drop per-item idempotency and decide each item afresh.

**Note** Asserts `already_decided` per item, and that the second decision changed nothing.

### `threshold_split_evasion`

Nothing. Named because it works.

**Basis** adr · **Strength** *none* · **Status** documented · **Floor** may be downgraded

**Decided by** ADR-0003 §The rules the fields serve — time deliberately left unmodelled

**Note** Splitting €9,000 into two requisitions of €4,500 succeeds. Detection needs aggregation over a window; no entity carries a timestamp and there is no aggregation rule. The control that would stop it: same vendor and cost centre within a period, summed against the threshold. Adopted as a named accepted risk rather than omitted — it is the attack a purchase-to-pay reader thinks of unprompted. THE SUITE'S ONE ROW THAT ASSERTS NOTHING.

### `legacy_unauthenticated_refused`

The always-on legacy leg accepting calls with no token.

**Basis** seam · **Strength** *none* · **Status** asserted · **Floor** may never be downgraded

**Decided by** ADR-0009 §Three assertions, and they exist to falsify rather than to sample

**Removal that makes the attack succeed** Apply token verification inside the modern request path instead of ahead of era routing.

**Note** Value concentrated in the first run. If this goes red, token verification sits behind era routing and ADR-0009 REOPENS — refusing the era at the edge becomes live again.

### `legacy_underscoped_same_denial_class`

The legacy leg producing a weaker refusal than its modern twin.

**Basis** seam · **Strength** *none* · **Status** asserted · **Floor** may never be downgraded

**Decided by** ADR-0009 §Three assertions, and they exist to falsify rather than to sample

**Removal that makes the attack succeed** Run the scope gate on the modern leg alone, skipping it when no `MCP-Protocol-Version` header is present.

**Note** REMOVAL REWORDED 2026-08-19 (#38), on confirming it by hand. It read "resolve scope from the era-specific handler rather than the shared policy function", which was written against ADR-0013's original placement of gate 5 at dispatch. #37 moved gate 5 into middleware ahead of era routing, so there is no era-specific handler left for scope to be resolved from and the old wording names a deletion nothing can perform. The rule it protects is unchanged — one scope rule, one implementation, both legs — and the reworded deletion is the one that reaches it on the chain as built.

### `legacy_discover_exemption_unavailable`

A legacy-era request claiming the unauthenticated `server/discover` exemption.

**Basis** seam · **Strength** *none* · **Status** asserted · **Floor** may never be downgraded

**Decided by** ADR-0009 §Three assertions, and they exist to falsify rather than to sample

**Removal that makes the attack succeed** Key the exemption on a default method name when `Mcp-Method` is absent.

**Note** Asserts WHY, not just that. The refusal must follow from the legacy leg not carrying the header — absence — rather than from a default nobody would notice changing.

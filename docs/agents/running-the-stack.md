# Running the stack

How to bring the exhibit up locally without hitting the three failures that look like success.

## Every compose command selects the TLS profile

```
docker compose --env-file tls.env up -d
docker compose --env-file tls.env down --remove-orphans
```

Up and down alike, in every terminal, including a second one opened later. Run a profiled `down` before an `up` whenever the previous state is unknown.

An unselected profile never errors. It gives you the other stack, and all three symptoms surface far from the command that caused them:

- **A bare `down` strands the certificate container.** `keycloak-certificate` sits in the `tls` profile (`compose.yaml:303`), and `docker compose down` without the env file leaves services in an unselected profile alone. The network is deleted anyway, so the surviving container holds a reference to a network ID that no longer exists and the next `up` dies with `failed to set up container networking: network <id> not found` — naming an ID that appears nowhere you can look it up.
- **A bare `up` silently recreates Keycloak on plain HTTP.** Nothing fails at that moment. The symptom arrives minutes later as `httpcore2.ConnectError: [SSL: WRONG_VERSION_NUMBER]` at the bottom of a long traceback — a client offering a TLS handshake to a plain listener.
- **`--profile tls up` is not a substitute, and it is the most convincing of the three.** It starts `keycloak-certificate`, which runs and exits cleanly, and every other container comes up healthy, so the run looks right. `compose.yaml:132` and `:206` read the TLS options through `${MCP_TLS_SERVER_ENV:-…}` and `${MCP_TLS_KEYCLOAK_ENV:-…}`, which only `tls.env` sets — so Keycloak keeps its plain listener on 8081.

**Tell the two stacks apart in one line.** `curl https://localhost:8081/realms/mcp-erp/.well-known/openid-configuration` returns `000` on the downgraded stack and `200` on the real one.

## The certificate is per-checkout

`./keycloak/tls` is a bind mount **relative to whichever checkout runs compose**, and nothing is shared between checkouts. `generate.sh` re-mints only when *both* `authority.crt` and `keycloak.p12` are absent, so running the profile from a second location mints a second authority — and the browser trust installed for the first one silently stops matching.

Run compose from one checkout for the life of a session. A worktree that needs the TLS profile mints and trusts its own certificate.

## Driving Claude Code against the exhibit

The MCP server is plain HTTP but the authorization server is not, and the browser handoff needs steering. From a separate terminal — Claude Code cannot nest:

```powershell
$env:MCP_PROTOCOL_NEGOTIATION="modern"   # "auto" also works; modern pins the era
$env:NODE_EXTRA_CA_CERTS="<this checkout>\keycloak\tls\authority.crt"
$env:BROWSER="C:\Program Files\Mozilla Firefox\firefox.exe"
claude
```

Then `/mcp` → `mcp-erp` → Authenticate.

- **Point `NODE_EXTRA_CA_CERTS` at the checkout you ran compose from**, per the section above. Without it the run fails with `self signed certificate in certificate chain` *after* appearing to connect: it reaches the server on the legacy leg and dies on the TLS metadata fetch, so the error names certificates while the status says connected.
- **Without a negotiation value it falls back to legacy silently.** Neither failure is guessable from its text.
- **Registration is per project path.** `mcp-erp` is registered at local scope under the main-checkout path in `.claude.json`, so `/mcp` shows nothing when Claude Code is launched from a worktree. Register it there too. The gateway publishes `8080:8080` on the host, so the same URL works from either directory.
- **`BROWSER` is spawned as `<BROWSER> <url>`**, with the URL as the entire argument list — no flags can be passed. The auth screen prints the URL regardless, with a `c` chord to copy it; that is the recovery if the handoff misfires.

## Tokens for the conformance client

Scripts that mint a token through the real flow need the three variables `tests/tokens.py` documents. In PowerShell they persist for the whole window:

```powershell
$env:MCP_ISSUER="https://keycloak:8081/realms/mcp-erp"
$env:KEYCLOAK_BASE_URL="https://localhost:8081"
$env:SSL_CERT_FILE="keycloak/tls/authority.crt"
```

Keycloak remembers a grant per Person and client, so two flows run back to back consume each other: whichever runs second posts one form instead of two. Restart the profile between runs that each need a cold realm.

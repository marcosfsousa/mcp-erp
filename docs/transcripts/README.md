# Captured transcripts

Six wire exchanges, written by a run and committed verbatim. They are the
evidence half of the walkthrough [ADR-0014](../adr/0014-the-walkthrough-is-the-write-up-and-the-image-is-never-the-proof.md)
specified: the tables render from their sources, the prose is hand-written, and
these are captured — **a run writes them, the write-up includes them, and a check
refuses a diff.**

Nothing here is edited by hand. `Seed renders clean` and `Authorization code
flow` both re-derive from this directory, and a hand-edited file is a red check
rather than a surprise in a document.

| File | What it shows |
| --- | --- |
| [`the-flow-completes.txt`](the-flow-completes.txt) | A client registered nowhere in the realm identifies itself by a document GitHub Pages serves, a person logs in and consents, the code is redeemed, and the token reaches a tool. |
| [`tools-list-for-two-tokens.txt`](tools-list-for-two-tokens.txt) | The same endpoint answering two earned tokens with different tool sets. The root README's one embedded proof is derived from this file. |
| [`scope-without-role.txt`](scope-without-role.txt) | Priya Raman's consented `erp.decide` meeting a server that holds her no deciding role: `-31010`, where a `403` would tell a caller to fetch a token that cannot exist. |
| [`under-scoped-tool-absent.txt`](under-scoped-tool-absent.txt) | A token without `erp.decide`: `approve_requisition` is not in the listing, and calling it anyway is answered with a challenge naming the scope. |
| [`segregation-of-duties.txt`](segregation-of-duties.txt) | Every authorization gate passed, and the domain refusing anyway because the approver raised the requisition himself. |
| [`row-scoped-not-found.txt`](row-scoped-not-found.txt) | Another cost centre's row and an identifier no row carries, answered byte for byte the same. |

The first three are earned through a consent screen and are written by
`tests/conformance/test_authorization_code_flow.py`; the last three are written
by `tests/capture.py`. `tests/transcripts.py` is what they share.

## The committed bearer tokens are not secrets

Every transcript carries a real access token, and that is deliberate — a reader
can decode one and check `aud` and `scope` against what the write-up claims,
which a placeholder would make impossible.

**It is more than the access token, and the argument has to cover all of it.**
`the-flow-completes.txt` is a whole authorization code flow, so it holds the
refresh token and the session cookies too — and those outlive the access token by
a long way: the access token expires five minutes after it is issued
(`accessTokenLifespan: 300`), the refresh token thirty, and `KEYCLOAK_SESSION`
carries `Max-Age=36000`.

None of that matters, because none of them is redeemable anywhere. The realm is a
throwaway local one that re-imports from committed files into an in-memory
database on every boot and **mints fresh signing keys each time**, so every token
here was signed by a key that no longer exists and is refused by the only party
that could ever have honoured it. `KEYCLOAK_IDENTITY` is itself a JWT — HS512,
against a realm key minted on the same boot — so it is refused by the same party
for the same reason, and `KEYCLOAK_SESSION` is an opaque handle to a session that
went with the database that held it. They are issued to People whose shared
password is committed as `not-a-secret-demo-password`, and there is no deployment
for any of it to reach. Direct Access Grants are disabled on every client, and
`password_grant_refused` is the assertion of it.

## What the check masks, and what it must not

A re-capture cannot be compared byte for byte, because a fresh run mints a fresh
token. So the check masks the volatile fields on **both** sides and compares; the
file changes only when something substantive changed.

**Masked:** the bearer, identity and refresh tokens; `iat`, `exp`, `auth_time`,
`jti`, `sid` and Keycloak's `session_state`; the realm's per-boot key identifier;
the tool listing's `ttlMs`, which is the presented token's remaining lifetime,
and the token response's `expires_in` and `refresh_expires_in`, which are the
same countdown one entity along; `date`, `content-length` and the gateway's
`x-served-by`; the session cookies;
and every query-string or form parameter that is not on a named stable list —
which is what covers the authorization code, `state`, the code challenge and its
verifier, and Keycloak's own per-attempt identifiers.

**Never masked:** `sub`, `aud`, `iss`, the granted scopes, the ordinal
identifiers, list ordering, error codes and refusal shapes. Everything the
exhibit claims is on this side of the line.

Two things are **canonicalised rather than masked**, and both are the
specification's own reading: JSON object members are compared in sorted order,
because RFC 8259 defines an object as unordered, and a scope set is compared
sorted, because RFC 6749 §3.3 says *"the order of values does not matter"*. Their
values survive; only an order that carries no meaning does not. Keycloak
advertises the same scope set in a different order on each boot, and without this
a required check would go red on a difference the specification says is not one.

The rules reach a value wherever it is: an object body, an array body, and a JSON
document a beat carried inside a string — which is the shape an MCP text content
block uses, and the one place a volatile value can hide from a rule that reads
lines.

`tests/transcripts.py` holds the mask, and `tests/test_transcripts.py` is what
asserts that it covers each of these and none of those.

## What a red check prints

The step names the drifted file and then prints the diff **under this same
mask**, so the output is the comparison the verdict made rather than a second
opinion about it — a `git diff` would lead with fields the mask covers, and
`tests/transcript_drift.py` opens with what that costs a reader.

The drifted captures are also uploaded as a `drifted-transcripts` artifact, which
is what lets someone re-run the mask with different rules after the rerun that
overwrites them. `tests/test_transcript_drift.py` holds the printed diff and the
verdict in agreement.

## Two steps are envelopes rather than bodies

The login page and the consent screen are rendered as their media type and
nothing more. They are tens of kilobytes of markup carrying a fresh session
identifier per attempt, and ADR-0014 assigns them to a different artifact class
anyway: **the consent screen ships as a screenshot, beside the transcript that
proves what it claims.** What a transcript owes those two steps is the envelope.

JSON bodies are the wire's, re-serialised one member per line so that both a
reader and the mask can see the structure. Every key, value and ordering is what
came back.

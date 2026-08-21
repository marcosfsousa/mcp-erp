#!/usr/bin/env bash
#
# The opt-in TLS profile's certificate, minted on the reader's own machine.
#
#
# WHY NOTHING HERE IS COMMITTED
# -----------------------------
# The reader installs this authority into their operating system or browser
# trust store, which is a real grant: whoever holds its private key can present
# a valid certificate for any name, to that reader, for as long as it is
# trusted. A committed authority would hand that grant to everybody who has ever
# cloned this repository. So the key pair is generated here, on the machine that
# will trust it, and `.gitignore` beside this file refuses the output.
#
# The seed's password is committed and this is not, and the difference is not
# inconsistency: `not-a-secret-demo-password` unlocks a realm that is rebuilt
# from file into an in-memory database on every boot and is reachable from
# nowhere. A trusted certificate authority reaches every site the reader visits.
#
#
# THE AUTHORITY'S PRIVATE KEY IS DESTROYED. THE LEAF'S IS NOT
# -----------------------------------------------------------
# The authority's key exists for one `-gencert` and is deleted in the last line.
# What stays on disk is the authority's *certificate*, which is what the trust
# store needs. So the thing the reader installs has no usable private key
# anywhere — not in this repository, and not in the directory it wrote.
#
# **The leaf key stays, and after the trust step the reader's whole machine
# trusts what it signs.** `keycloak.p12` holds it, under the password below,
# which this repository
# commits. `keycloak/README.md` §*Trusting the certificate* sends the reader to
# the Windows **Local Machine** store, the macOS **System** keychain or
# `/usr/local/share/ca-certificates` — machine-wide, all three — and from that
# moment the certificate that key belongs to is accepted for `DNS:keycloak`
# **and `DNS:localhost`**, for 365 days. Concretely: whoever obtains that one
# file can present a valid `https://localhost` certificate to that reader for a
# year, against any local service they browse.
#
# Reaching the file needs local access to the reader's machine already, which is
# the whole of why an exhibit that runs nowhere else accepts it. It is written
# down because the two keys are not the same promise, and this header is where a
# reader looks for the difference.
#
# **Revoking the grant is two steps**, and re-minting is not one of them on its
# own: delete `keycloak/tls/` — which takes the leaf key with it — and remove
# *mcp-erp demo certificate authority* from the store it was added to. Minting
# again therefore means trusting again. That is the honest cost of the property
# above, and one year is the validity chosen against it.
#
#
# KEYTOOL RATHER THAN OPENSSL
# ---------------------------
# The Keycloak image is built on a micro base and carries neither `openssl` nor
# `curl`; it carries a JVM, so `keytool` is already there. Map constraint `#11`
# then costs nothing: this runs in the image `compose.yaml` already pins by
# exact tag and digest, so the profile adds no external image to keep honest.
set -euo pipefail

TLS_DIR=${TLS_DIR:-/tls}
PASSWORD=${TLS_PASSWORD:-not-a-secret-demo-password}

# `keycloak` is the name that matters: it is the issuer's authority, it resolves
# by Compose's own DNS inside the network and by one `127.0.0.1 keycloak` line
# outside it, and a certificate is checked against the name a caller used.
#
# `localhost` earns its place rather than being thrown in — it is the name
# `KEYCLOAK_BASE_URL=https://localhost:8081` uses, which is how host-side tooling
# reaches this stack without the hosts-file line, and `keycloak/README.md`
# documents that. Nothing else is here: every name on a certificate the reader
# installs as trusted is a name somebody could be answered for.
SAN="san=dns:keycloak,dns:localhost"

KEYSTORE="$TLS_DIR/keycloak.p12"
CA_KEYSTORE="$TLS_DIR/authority.p12"
CA_CERT="$TLS_DIR/authority.crt"
SIGNED="$TLS_DIR/keycloak.crt"
CHAIN="$TLS_DIR/chain.crt"

# Idempotent, because this runs on every `docker compose` invocation that
# selects the profile and a fresh certificate every time would mean trusting a
# fresh authority every time. Delete the directory's contents to start over.
if [ -f "$KEYSTORE" ] && [ -f "$CA_CERT" ]; then
  echo "certificate already present in $TLS_DIR — delete it to mint another"
  exit 0
fi

# A half-written directory is worse than an empty one: Keycloak would start
# against a keystore with no signed reply in it and fail on something several
# steps from the cause.
rm -f "$KEYSTORE" "$CA_KEYSTORE" "$CA_CERT" "$SIGNED" "$CHAIN"

keytool -genkeypair -alias authority -keyalg RSA -keysize 2048 -validity 365 \
  -dname "CN=mcp-erp demo certificate authority" \
  -ext "bc:c=ca:true,pathlen:0" -ext "ku:c=keyCertSign,cRLSign" \
  -keystore "$CA_KEYSTORE" -storetype PKCS12 -storepass "$PASSWORD" -keypass "$PASSWORD"

keytool -genkeypair -alias keycloak -keyalg RSA -keysize 2048 -validity 365 \
  -dname "CN=keycloak" -ext "$SAN" \
  -keystore "$KEYSTORE" -storetype PKCS12 -storepass "$PASSWORD" -keypass "$PASSWORD"

keytool -exportcert -alias authority -rfc \
  -keystore "$CA_KEYSTORE" -storepass "$PASSWORD" > "$CA_CERT"

# `eku=serverAuth` and a leaf that is not itself an authority, because a browser
# that accepts anything less is a browser this exhibit should not be teaching
# anybody to trust.
keytool -certreq -alias keycloak -keystore "$KEYSTORE" -storepass "$PASSWORD" \
  | keytool -gencert -alias authority -keystore "$CA_KEYSTORE" -storepass "$PASSWORD" \
      -ext "$SAN" -ext "bc=ca:false" \
      -ext "ku:c=digitalSignature,keyEncipherment" -ext "eku=serverAuth" \
      -validity 365 -rfc > "$SIGNED"

# The authority first, or `keytool` refuses the reply it cannot build a chain
# for. Both go in: Keycloak serves what the keystore holds, and a client that
# was handed only the leaf would have nothing to verify it against.
keytool -importcert -noprompt -alias authority -file "$CA_CERT" \
  -keystore "$KEYSTORE" -storepass "$PASSWORD"

cat "$SIGNED" "$CA_CERT" > "$CHAIN"

keytool -importcert -noprompt -alias keycloak -file "$CHAIN" \
  -keystore "$KEYSTORE" -storepass "$PASSWORD"

rm -f "$CA_KEYSTORE" "$SIGNED" "$CHAIN"

# Handed back to whoever owns the directory, because this runs as root and the
# directory is the reader's own checkout. A Linux bind mount carries host
# ownership straight through, so without this the reader would need `sudo` to
# delete files their own `docker compose` had just written. `|| true` because
# Docker Desktop's file sharing on macOS and Windows answers ownership questions
# its own way, and failing there would be a failure about nothing.
if OWNER=$(stat -c '%u:%g' "$TLS_DIR" 2>/dev/null); then
  chown "$OWNER" "$KEYSTORE" "$CA_CERT" 2>/dev/null || true
fi

echo "minted $KEYSTORE and $CA_CERT; the authority's private key is gone"

# The authorization server, built once so no boot pays for it.
#
#
# WHY THERE IS A DOCKERFILE AT ALL
# --------------------------------
# `cimd` — the Client Identity Metadata Document feature — is a **build-time**
# option in Keycloak. Either an image pays that cost once or every boot pays it,
# including every continuous-integration run. Once the build step exists,
# production mode costs three more words. ADR-0007 §How it runs, and where the
# file lives.
#
#
# PINNED BY EXACT TAG AND DIGEST
# ------------------------------
# Map constraint `#11`, and this image is the reason it exists. `--features=cimd`
# is a **preview** flag: preview features carry no compatibility guarantee and
# move between minor versions, so a floating tag would turn a preview regression
# into a suite going red one morning for a reason nothing in this repository
# changed. Pinned, a regression can only arrive inside the pull request that
# bumped the version — which is where a blocking check is doing its job rather
# than being a liability, and it is what let ADR-0008 accept a merge-gating job
# that depends on this container at all.
#
# The digest moves only in a pull request that does nothing else.
FROM quay.io/keycloak/keycloak:26.7.1@sha256:f1f1f01e472c8a78df40d8f2a49a925274eda4d3d80d5f6edbb5c880ee3c01c6

# `--db=dev-mem` is chosen for what it makes unreachable, not for being cheap.
# Keycloak's startup import *skips* when the realm already exists — there is no
# strategy knob on the flag, and the legacy OVERWRITE_EXISTING property cannot
# rescue it in 26.x because ExportImportManager sets IGNORE_EXISTING itself
# before the providers are constructed. With an empty in-memory database the
# realm never "already exists", so the trap is structurally unreachable rather
# than documented around, and "Keycloak is a pure function of the committed
# file" becomes provable rather than asserted.
#
# The accepted cost is an asset: an empty database means fresh signing keys on
# every boot, so the resource server meets a key identifier it has never seen
# and key rotation is exercised rather than asserted.
#
# `--health-enabled` exists so Compose can wait for readiness rather than for a
# number of seconds. Both are build options, so they belong here and not in the
# environment.
RUN /opt/keycloak/bin/kc.sh build \
      --features=cimd \
      --db=dev-mem \
      --health-enabled=true

# Baked in, and bind-mounted over in Compose from this same committed path. The
# mount wins locally, so editing the realm and restarting shows the change
# immediately — which is what makes the pure-function claim something a reader
# can *try*. The baked copy keeps the image runnable on its own, wherever it is
# run. The two cannot drift: they are the same file in the repository.
#
# Copied after the build so that editing the realm does not invalidate it.
COPY import/ /opt/keycloak/data/import/

# The base image's entrypoint is kc.sh, so this is its argument list.
# `--optimized` skips the re-build the build step above already did;
# `--import-realm` reads the directory, pairing mcp-erp-realm.json with the
# mcp-erp-users-0.json beside it exactly as a Keycloak export would.
CMD ["start", "--optimized", "--import-realm"]

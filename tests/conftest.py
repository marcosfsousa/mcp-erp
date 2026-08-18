"""What makes `tests/` importable, and deliberately nothing else.

pytest inserts a conftest's own directory onto the import path, so this file is
what lets a suite in `tests/matrix/` or `tests/attack_suite/` write
``from tokens import mint``. Making `tests/` a package instead would change how
every existing suite is imported — and mypy resolves the same layout — to buy a
dotted name nothing needs.

**It holds no fixtures on purpose.** The token helper caches within the run and
is called directly, so a fixture wrapping it would add a second place to look
and a second scope to reason about. When a wire suite needs shared setup that
the helper does not already own, it earns its lines here then.

**Nothing here connects to anything at import time.** Every job that runs pytest
collects this file — `Layer 2 ejects clean` with layer 3 deleted, `Seed renders
clean`, and the token-helper step inside `Lint and types`. A fixture that reached
Keycloak while being *defined* would turn all three into jobs that need Compose.
"""

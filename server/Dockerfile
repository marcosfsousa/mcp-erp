# The resource server. Two of these run behind no sticky routing, which is what
# makes map constraint `#5`'s statelessness falsifiable rather than asserted.
#
#
# PINNED BY EXACT TAG AND DIGEST, TWICE
# -------------------------------------
# Map constraint `#11`. Two images are pinned here and they pin different
# things. The base image fixes the **interpreter**, at the exact patch
# `.python-version` names and `pyproject.toml`'s `requires-python` bounds — a
# split there would leave continuous integration testing a runtime this image
# does not use, which is a green suite that proves nothing about the artifact.
# The `uv` image fixes the **resolver**, so the lockfile is read by the same
# version of the tool that wrote it.
#
# Python dependencies pin by lockfile rather than by tag: `uv.lock` is
# committed and `--locked` fails rather than re-resolving, so a dependency
# cannot move under a green suite. Both digests move only in a pull request
# that does nothing else.
FROM python:3.13.15-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a

# The resolver as a single binary, copied rather than installed, so it leaves
# nothing in the image's own Python environment to disagree with the lockfile.
COPY --from=ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 /uv /usr/local/bin/uv

# `UV_NO_MANAGED_PYTHON` and `UV_PYTHON` together keep uv on the interpreter the
# base image pins. Left to itself uv would happily download one, and the digest
# above would then be pinning a runtime nothing runs.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_MANAGED_PYTHON=1 \
    UV_PYTHON=/usr/local/bin/python3.13 \
    PATH=/srv/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /srv

# The manifest and the lockfile alone, so that editing a module does not
# re-resolve and re-download every dependency. `--no-dev` is the whole point of
# the dev group existing: a module the application imports but this image does
# not carry resolves fine on a runner and fails at container start, and
# installing a dev superset here would make continuous integration faithful to
# nothing.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# `CONTEXT.md` is the distribution's declared readme, so the build backend reads
# it. It is also the vocabulary this exhibit is written in, which is a reason to
# be glad it ships rather than a reason to work around it.
COPY CONTEXT.md ./
COPY src/ ./src/
RUN uv sync --locked --no-dev

# Not root. The server reaches a database and an authorization server and holds
# no secret of its own, so there is nothing here that needs the privilege — and
# an exhibit about authorization that runs its own process as root invites the
# obvious question.
# An explicit high identifier rather than `--system`, which warns that 10001 is
# above its own ceiling and then creates the account anyway. The number is fixed
# so that a bind mount's ownership is a property of this file rather than of
# whatever the base image had left unused.
RUN useradd --create-home --uid 10001 exhibit
USER exhibit

EXPOSE 8080

# A factory, so importing `mcp_erp.app` reads no environment and opens no
# socket — which is what keeps the *Every package imports* check in continuous
# integration a statement about the package tree rather than about a machine.
#
# `--host 0.0.0.0` because the only thing that reaches this port is the gateway,
# inside the Compose network; the published address is the gateway's.
CMD ["uvicorn", "--factory", "mcp_erp.app:create_app", "--host", "0.0.0.0", "--port", "8080"]

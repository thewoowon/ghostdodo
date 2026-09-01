# GhostDodo API — production image.
#
# Two stages so the runtime layer carries no build tooling. Dependencies are
# installed from the lockfile before the source is copied, so a code-only
# change reuses the dependency layer.

FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first: this layer is invalidated only by the lockfile.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY app ./app


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Runs unprivileged. The API writes nothing to disk — evidence goes to S3.
RUN useradd --create-home --uid 10001 ghostdodo
WORKDIR /app

COPY --from=builder --chown=ghostdodo:ghostdodo /app /app

USER ghostdodo
EXPOSE 8000

# Railway injects PORT.
#
# Deliberately no --proxy-headers: forwarding is interpreted in `client_ip`,
# which counts hops from the right of X-Forwarded-For using
# TRUSTED_PROXY_HOPS. Letting uvicorn rewrite the peer as well would leave
# two different rules for the same question. Nothing else in the app reads
# the request scheme, so there is nothing for --proxy-headers to fix.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-server-header"]

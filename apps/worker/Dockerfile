FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
COPY packages/shared packages/shared
COPY apps/worker apps/worker

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package cm-worker

CMD ["celery", "-A", "cm_worker.celery_app", "worker", "--loglevel=info"]

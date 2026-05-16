FROM node:24-alpine AS web-build

WORKDIR /app

COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci

COPY apps/web apps/web
RUN npm run build:web

FROM python:3.13-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY packages/shared packages/shared
COPY apps/api apps/api
COPY apps/beat apps/beat
COPY apps/worker apps/worker

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --all-packages && \
    groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid 1001 --no-create-home app && \
    chown -R app:app /app

COPY --from=web-build --chown=1001:1001 /app/apps/web/dist apps/web/dist

USER app

FROM node:24-alpine AS web-build

WORKDIR /app

COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package.json
RUN npm ci

COPY frontend frontend
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
COPY src src
COPY --from=web-build --chown=1001:1001 /app/frontend/dist src/page_crafter/api/static

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev && \
    groupadd --system --gid 1001 app && \
    useradd --system --uid 1001 --gid 1001 --no-create-home app && \
    chown -R app:app /app

USER app

EXPOSE 8000

CMD ["page-crafter", "api"]

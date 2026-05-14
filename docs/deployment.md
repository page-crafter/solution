# Deployment

## Prerequisites

- Docker 24+ and Docker Compose v2
- A running Atlassian Confluence Data Center instance
- An LLM provider: OpenAI API key **or** a local Ollama instance

## Quick start (Docker Compose)

```bash
cp .env.example .env
# Edit .env — at minimum set CONFLUENCE_PAT and OPENAI_API_KEY (or Ollama settings)

docker compose up -d postgres redis keycloak lightrag
docker compose build
docker compose up -d
```

Services available after startup:

| URL                        | Service                |
| -------------------------- | ---------------------- |
| http://localhost:8000      | Frontend               |
| http://localhost:8000/docs | API (Swagger UI)       |
| http://localhost:8080      | Keycloak admin console |
| http://localhost:9621      | LightRAG API           |

Default Keycloak users (all password: `password`):

| Username | Role   | Access           |
| -------- | ------ | ---------------- |
| `admin`  | admin  | Full access      |
| `editor` | editor | Page editor      |
| `reader` | reader | Read-only        |
| `chat`   | chat   | Chat widget only |

## Build commands

Build all images from workspace root (required — Dockerfiles use the monorepo root as context):

```bash
# Build all
docker compose build

# Build one service
docker compose build api
docker compose build worker
```

### Frontend runtime config

The Vue bundle reads browser-facing settings from `/config.json` at startup. Update `apps/web/public/config.json` before building to target a different API or Keycloak host.

The default `backend.baseUrl` is empty, so the browser calls `/api` on the same `http://localhost:8000` origin that serves the frontend.

## Local development (without Docker)

### Infrastructure only

```bash
docker compose up -d postgres redis keycloak lightrag
```

### Backend (API + worker)

```bash
uv sync --all-packages

# API (hot-reload)
uv run uvicorn cm_api.main:app --reload --app-dir apps/api/src

# Worker
uv run celery -A cm_worker.celery_app worker --loglevel=info

# Beat scheduler (optional — triggers nightly sync)
uv run celery -A cm_worker.celery_app beat --loglevel=info
```

### Frontend

```bash
npm install
npm run dev:web        # http://localhost:5173
```

## Dockerfile structure

The root `Dockerfile` uses the **workspace root as build context**. This is required because the Python apps depend on `packages/shared`, and the final image also embeds the built Vue app.

```
docker compose build
  context: .  (workspace root)
  └── Dockerfile
      ├── web-build stage  → node:24 build of apps/web
      └── runtime stage    → python:3.13-slim with cm-api, cm-worker, cm-shared, and Vue dist
```

### Unified app image

- Runtime base: `python:3.13-slim`
- uv copied from `ghcr.io/astral-sh/uv:latest`
- Dependencies installed with `uv sync --frozen --no-dev --all-packages`
- `UV_COMPILE_BYTECODE=1` — bytecode compiled at build time, not first import
- BuildKit cache mount on `/root/.cache/uv` — fast rebuilds when `uv.lock` unchanged
- `api` and `worker` both use `page-crafter:local`
- `api` runs Uvicorn and serves both `/api/*` and the compiled Vue SPA
- `worker` runs Celery from the same image with a different Compose command
- `/config.json` is served by FastAPI with `Cache-Control: no-store`

## Database migrations

Schema is created automatically on API startup via `create_database_schema()` (SQLAlchemy `metadata.create_all`). There is no migration tool — schema changes require manual table drops in development or ALTER TABLE in production.

## Keycloak realm

The realm is imported automatically from `docker/keycloak/page-crafter-realm.json` when the Keycloak container starts (`--import-realm` flag). Re-importing after changes requires removing the Keycloak container (it skips import if the realm already exists):

```bash
docker compose rm -sf keycloak
docker compose up -d keycloak
```

## Upgrading dependencies

```bash
# Python
uv lock --upgrade
uv sync --all-packages

# Node
npm update --workspaces
```

After upgrading, rebuild images:

```bash
docker compose build --no-cache
```

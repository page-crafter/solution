# Deployment

## Prerequisites

- Docker 24+ and Docker Compose v2
- A running Atlassian Confluence Data Center instance
- An LLM provider: OpenAI API key **or** a local Ollama instance

## Quick start (Docker Compose)

```bash
cp .env.example .env
# Edit .env — at minimum set CONFLUENCE_PAT and OPENAI_API_KEY (or Ollama settings)

docker compose up -d postgres redis keycloak
docker compose build
docker compose up -d
```

Services available after startup:

| URL                        | Service                |
| -------------------------- | ---------------------- |
| http://localhost           | Frontend               |
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
docker compose build front
```

### Frontend runtime config

The Vue bundle reads browser-facing settings from `config.json` at startup. Update `apps/web/public/config.json` before building, or replace/mount `/usr/share/nginx/html/config.json` in a running web image to target a different API or Keycloak host without rebuilding the JavaScript bundle.

The Docker Compose setup mounts `apps/web/public/config.json` into the nginx container so local changes are picked up on refresh.

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

All three Dockerfiles use the **workspace root as build context**. This is required because the Python apps depend on `packages/shared`, which lives outside their own directory.

```
docker compose build
  context: .  (workspace root)
  ├── apps/api/Dockerfile      → installs cm-api + cm-shared via uv
  ├── apps/worker/Dockerfile   → installs cm-worker + cm-shared via uv
  └── apps/web/Dockerfile      → node:24 build → nginx:alpine runtime
```

### Python images (api, worker)

- Base: `python:3.13-slim`
- uv copied from `ghcr.io/astral-sh/uv:latest`
- Dependencies installed with `uv sync --frozen --no-dev --package <name>`
- `UV_COMPILE_BYTECODE=1` — bytecode compiled at build time, not first import
- BuildKit cache mount on `/root/.cache/uv` — fast rebuilds when `uv.lock` unchanged

### Web image

- Stage 1 (`build`): `node:24-alpine` — runs `npm ci` then `npm run build:web`
- Stage 2 (`runtime`): `nginx:alpine` — serves `dist/` with SPA fallback routing
- `nginx.conf` sets `try_files $uri $uri/ /index.html` for Vue Router history mode
- Static assets (`.js`, `.css`, fonts) served with `Cache-Control: public, immutable`
- `config.json` is served with `Cache-Control: no-store`

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

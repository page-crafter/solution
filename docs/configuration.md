# Configuration

All backend configuration is loaded from environment variables (or a `.env` file at the workspace root) by `src/page_crafter/shared/settings/app.py` using `pydantic-settings`.

Copy `.env.example` to `.env` and fill in the required values before starting the stack.

## Required variables

These have no usable default and must be set:

| Variable         | Description                                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| `CONFLUENCE_PAT` | Confluence Data Center Personal Access Token. Used by the worker to read pages and publish.                        |
| `OPENAI_API_KEY` | OpenAI API key. Required when `LLM_PROVIDER=openai`. Leave empty when using Ollama or a compatible local endpoint. |

## Application

| Variable  | Default | Description                                                                       |
| --------- | ------- | --------------------------------------------------------------------------------- |
| `APP_ENV` | `local` | Runtime environment label (`local`, `staging`, `production`). Informational only. |

## Database

| Variable       | Default                                                                  | Description                                                       |
| -------------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| `DATABASE_URL` | `postgresql+psycopg://confluence:confluence@localhost:5432/page_crafter` | SQLAlchemy connection string for the main PostgreSQL database.    |
| `REDIS_URL`    | `redis://localhost:6379/0`                                               | Redis connection string used as Celery broker and result backend. |

## Keycloak

| Variable                | Default                 | Description                                                                                                                                                     |
| ----------------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `KEYCLOAK_URL`          | `http://localhost:8080` | Public Keycloak URL. Used by the frontend and to build JWT issuer URLs.                                                                                         |
| `KEYCLOAK_INTERNAL_URL` | _(empty)_               | Internal Keycloak URL for inter-container communication. Falls back to `KEYCLOAK_URL` when unset. Set to `http://keycloak:8080` when running in Docker Compose. |
| `KEYCLOAK_REALM`        | `page-crafter`          | Keycloak realm name.                                                                                                                                            |
| `KEYCLOAK_CLIENT_ID`    | `page-crafter-web`      | Keycloak client ID for the frontend.                                                                                                                            |
| `KEYCLOAK_AUDIENCE`     | `page-crafter-api`      | Expected `aud` claim in JWTs presented to the API.                                                                                                              |

## Confluence

| Variable                         | Default                 | Description                                            |
| -------------------------------- | ----------------------- | ------------------------------------------------------ |
| `CONFLUENCE_BASE_URL`            | `http://localhost:8090` | Base URL of the Confluence Data Center instance.       |
| `CONFLUENCE_SPACE_KEY`           | `DOC`                   | Space key to sync.                                     |
| `CONFLUENCE_PAT`                 | _(required)_            | Personal Access Token with read and write permissions. |
| `CONFLUENCE_API_TIMEOUT_SECONDS` | `30`                    | HTTP timeout for Confluence API calls.                 |

## LLM provider

| Variable                 | Default                     | Description                                                                             |
| ------------------------ | --------------------------- | --------------------------------------------------------------------------------------- |
| `LLM_PROVIDER`           | `openai`                    | Active LLM backend: `openai` or `ollama`.                                               |
| `OPENAI_API_KEY`         | _(empty)_                   | OpenAI API key. Not required for local-compatible endpoints.                            |
| `OPENAI_BASE_URL`        | `https://api.openai.com/v1` | OpenAI-compatible endpoint. Override to point at a local proxy or alternative provider. |
| `OPENAI_MODEL`           | `gpt-4o`                    | Chat model name.                                                                        |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small`    | Embedding model name.                                                                   |
| `OLLAMA_BASE_URL`        | `http://localhost:11434`    | Ollama server URL. Use `http://host.docker.internal:11434` when running in Docker.      |
| `OLLAMA_MODEL`           | `llama3.1`                  | Ollama chat model name.                                                                 |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text`          | Ollama embedding model name.                                                            |

## LightRAG

LightRAG is configured both via the app settings (for the API/worker to connect) and via its own environment variables in Docker Compose (for the LightRAG container itself).

### App / worker settings

| Variable                            | Default                 | Description                                                 |
| ----------------------------------- | ----------------------- | ----------------------------------------------------------- |
| `LIGHTRAG_BASE_URL`                 | `http://localhost:9621` | LightRAG service URL. Use `http://lightrag:9621` in Docker. |
| `LIGHTRAG_API_KEY`                  | _(empty)_               | API key for the LightRAG service when auth is enabled.      |
| `LIGHTRAG_CHAT_HISTORY_TURNS`       | `3`                     | Number of prior conversation turns included in RAG queries. |
| `LIGHTRAG_PIPELINE_TIMEOUT_SECONDS` | `900`                   | Timeout waiting for LightRAG indexing pipeline to complete. |

### LightRAG container settings (docker-compose.yml)

| Variable                             | Default                  | Description                                                                            |
| ------------------------------------ | ------------------------ | -------------------------------------------------------------------------------------- |
| `LIGHTRAG_LLM_BINDING`               | `openai`                 | LLM backend for LightRAG: `openai` or `ollama`.                                        |
| `LIGHTRAG_LLM_BINDING_HOST`          | OpenAI URL               | LLM endpoint for LightRAG.                                                             |
| `LIGHTRAG_LLM_BINDING_API_KEY`       | _(empty)_                | API key for LightRAG's LLM calls.                                                      |
| `LIGHTRAG_LLM_MODEL`                 | `gpt-5.2`                | Model used by LightRAG for graph extraction.                                           |
| `LIGHTRAG_EMBEDDING_BINDING`         | `openai`                 | Embedding backend: `openai` or `ollama`.                                               |
| `LIGHTRAG_EMBEDDING_BINDING_HOST`    | OpenAI URL               | Embedding endpoint.                                                                    |
| `LIGHTRAG_EMBEDDING_BINDING_API_KEY` | _(empty)_                | API key for embedding calls.                                                           |
| `LIGHTRAG_EMBEDDING_MODEL`           | `text-embedding-3-small` | Embedding model.                                                                       |
| `LIGHTRAG_EMBEDDING_DIM`             | `1536`                   | Embedding vector dimension. Must match model output. Use `768` for `nomic-embed-text`. |
| `LIGHTRAG_EMBEDDING_TOKEN_LIMIT`     | `8192`                   | Max tokens per embedding call.                                                         |

## Scheduler

| Variable    | Default     | Description                                                                 |
| ----------- | ----------- | --------------------------------------------------------------------------- |
| `SYNC_CRON` | `0 2 * * *` | Cron expression for automated Confluence sync. Default: daily at 02:00 UTC. |

`SYNC_CRON` is read by the scheduler Celery app. The worker consumes the scheduled
`page_crafter.scheduled_sync` task but does not own the Beat schedule.

## Frontend runtime config

Browser-facing frontend settings are loaded from `/config.json` at startup. The source file is `frontend/public/config.json` and is copied into the Vue build that FastAPI serves from the unified app image.

| JSON path                | Default                 | Description                                                                 |
| ------------------------ | ----------------------- | --------------------------------------------------------------------------- |
| `backend.baseUrl`        | _(empty)_               | API base URL used by the browser. Empty means same-origin `/api` requests. |
| `auth.keycloak.url`      | `http://localhost:8080` | Keycloak URL used for PKCE auth flow.                                      |
| `auth.keycloak.realm`    | `page-crafter`          | Keycloak realm.                                                            |
| `auth.keycloak.clientId` | `page-crafter-web`      | Keycloak public client ID.                                                 |

The previous `VITE_*` variables remain as development fallbacks only when `config.json` is not served.

## Local Ollama setup

When running with Ollama on the host machine and services in Docker:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

LIGHTRAG_LLM_BINDING=ollama
LIGHTRAG_LLM_BINDING_HOST=http://host.docker.internal:11434
LIGHTRAG_LLM_MODEL=llama3.1
LIGHTRAG_EMBEDDING_BINDING=ollama
LIGHTRAG_EMBEDDING_BINDING_HOST=http://host.docker.internal:11434
LIGHTRAG_EMBEDDING_MODEL=nomic-embed-text
LIGHTRAG_EMBEDDING_DIM=768
```

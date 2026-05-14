# Architecture

## Overview

Page Crafter is a documentation management tool for Atlassian Confluence Data Center. It syncs pages from Confluence, indexes them with LightRAG for semantic search, and provides an AI-assisted Markdown editor that publishes back to Confluence after human review.

## Services

```
Browser
  │
  ▼
┌─────────────────────┐        ┌──────────────────────┐
│  api (8000)         │        │  lightrag (9621)     │
│  FastAPI + Vue SPA  │◄──────►│  RAG pipeline        │
└─────────┬───────────┘        └──────────────────────┘
          │
          │ JWT validation / JWKS
          ▼
┌─────────────────────┐
│  keycloak (8080)    │
└─────────────────────┘
          │
          │ Celery tasks
          ▼
┌─────────────────────┐        ┌──────────────────────┐
│  worker             │        │  confluence (8090)   │
│  Celery             │◄──────►│  Atlassian DC        │
└─────────┬───────────┘        └──────────────────────┘
          │
     ┌────┴────┐
     ▼         ▼
┌─────────┐ ┌───────┐
│postgres │ │ redis │
│  5432   │ │ 6379  │
└─────────┘ └───────┘
```

### Component responsibilities

| Service | Image | Role |
|---------|-------|------|
| `api` | page-crafter:local | FastAPI. Serves the compiled Vue SPA, handles auth/read models, and queues long-running work to the worker via Celery. Never performs sync, RAG, or publish directly. |
| `worker` | page-crafter:local | Celery worker from the same image. Runs sync, Markdown generation, LLM proposals, preview rendering, and publish tasks. |
| `postgres` | postgres:16 | Stores all app state: synced pages, draft runs, proposals, chat sessions, job history. Embeddings stored as float arrays. |
| `redis` | redis:7-alpine | Celery broker and result backend. |
| `lightrag` | ghcr.io/hkuds/lightrag | Graph-based RAG engine. Receives documents on sync, answers queries from the chat feature. |
| `keycloak` | keycloak:26 | OIDC provider. Issues JWTs validated by the API on every request. |
| `confluence` | atlassian/confluence | Source of truth for pages. Worker reads XHTML and publishes back via REST API using a PAT. |
| `confluence-db` | postgres:16 | Dedicated database for Atlassian Confluence. |

## Data flow

### Sync

```
worker.sync_space
  → Confluence REST API  (fetch all pages in space)
  → postgres             (upsert ConfluencePage rows)
  → extract XHTML text
  → lightrag /documents  (index for RAG)
  → JobEvent rows        (progress tracking)
```

### Page editor

```
POST /editor/runs
  → api creates PageEditRun (status: pending)
  → queues worker.generate_markdown

worker.generate_markdown
  → reads ConfluencePage XHTML
  → LLM call (OpenAI / Ollama)  → Markdown draft
  → worker.convert_markdown     → Storage XHTML
  → worker.render_preview       → Confluence preview HTML
  → DraftVersion saved

User reviews diff in browser
  → PATCH /editor/runs/{id}/draft  (manual edits)
  → POST  /editor/runs/{id}/preview
  → POST  /editor/runs/{id}/publish

worker.publish_page
  → drift check against live Confluence version
  → PUT Confluence REST API
```

### Chat

```
POST /chat/sessions/{id}/stream
  → api streams response from lightrag /query
  → ChatMessage rows saved (question + answer)
```

## Package layout

```
confluenceManager2/
├── apps/
│   ├── api/          FastAPI application (cm-api)
│   ├── worker/       Celery worker (cm-worker)
│   └── web/          Vue 3 frontend
├── packages/
│   └── shared/       Shared Python package (cm-shared)
│       ├── db/       SQLAlchemy session, base, schema init
│       ├── models/   ORM models (ConfluencePage, PageEditRun, …)
│       ├── schemas/  Pydantic read/write schemas
│       ├── settings/ AppSettings (pydantic-settings)
│       └── jobs/     Job history utilities
├── docker/
│   ├── keycloak/     Realm import JSON
│   └── confluence/   atlassian-agent.jar
├── docs/             This documentation
├── Dockerfile        Unified app image for API, worker, and Vue dist
└── docker-compose.yml
```

## Authentication

All API routes (except `/api/auth/me` health probe) require a Bearer JWT issued by Keycloak. The API validates tokens by:

1. Fetching the JWKS from `{KEYCLOAK_INTERNAL_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs`
2. Verifying the `aud` claim contains `{KEYCLOAK_AUDIENCE}`
3. Extracting `roles` from the token (mapped by the `client-roles` protocol mapper)

Two roles are defined: `admin` (full access) and `chat` (chat widget only).

## Database schema (logical)

```
confluence_pages          — synced page metadata + XHTML
document_chunks           — embedding chunks (float[] column)

sync_runs                 — full-space sync executions
task_executions           — Celery task audit log
job_events                — granular progress events
audit_events              — publish audit trail

page_edit_runs            — editor session per page
draft_artifacts           — storage XHTML + preview HTML
draft_versions            — validated Markdown snapshots
page_proposals            — LLM-generated Markdown proposals

chat_sessions             — RAG chat sessions
chat_messages             — questions + answers
```

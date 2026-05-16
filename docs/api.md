# API Reference

Base URL: `http://localhost:8000/api`

All endpoints require a `Authorization: Bearer <token>` header except where noted. Tokens are issued by Keycloak via PKCE flow.

Interactive docs available at `http://localhost:8000/docs` (Swagger UI).

---

## Authentication

### `GET /auth/me`

Returns the authenticated user profile (username, email, roles). Useful as a health check for the auth flow.

---

## KPIs

### `GET /kpis`

Returns enriched dashboard KPI cards: total pages, synced pages, last sync time, pending drafts, etc.

---

## Spaces

### `GET /spaces`

Returns per-space aggregated metrics used by the dashboard space selector.

---

## Confluence pages

### `GET /confluence/pages`

Returns all non-deleted synced Confluence pages (id, title, space, last synced).

### `GET /confluence/pages/{page_id}`

Returns one synced page including the raw Storage XHTML and extracted plain text.

### `POST /confluence/pages`

Queues creation of a new empty Confluence page in the configured space.

**Body:**
```json
{
  "title": "string",
  "parent_id": "string | null"
}
```

### `POST /confluence/pages/{page_id}/refresh`

Queues a worker refresh for a single page (re-fetch from Confluence + re-index).

### `POST /confluence/pages/{page_id}/move`

Queues a worker move operation.

**Body:**

```json
{
  "new_parent_id": "string",
  "position": "before | after | append"
}
```

### `DELETE /confluence/pages/{page_id}`

Queues deletion of a Confluence page (both in Confluence and the local database).

---

## Sync

### `POST /sync/runs`

Queues a full-space Confluence sync. Returns a job ID for polling.

---

## Jobs

### `GET /jobs/history`

Returns recent worker task executions (task name, status, start/end time).

### `GET /jobs/{job_id}`

Returns the current status of a job (`pending`, `running`, `success`, `failed`, `cancelled`).

### `GET /jobs/{job_id}/events`

Returns chronological progress events for a job. Useful for progress display.

### `POST /jobs/{job_id}/cancel`

Cancels a queued or running job.

---

## Page editor

### `POST /editor/runs`

Creates an app-side draft and queues Markdown generation via LLM.

**Body:**
```json
{
  "page_id": "string",
  "instructions": "string"
}
```

### `GET /editor/runs/{run_id}`

Returns a page edit run with all associated artifacts (XHTML, preview HTML) and proposals.

### `GET /editor/runs/{run_id}/draft-versions`

Returns validated Markdown draft versions for a run, newest first.

### `GET /editor/pages/{page_id}/active`

Returns the newest active draft run for a page, if any.

### `POST /editor/pages/{page_id}/draft`

Creates a draft from manually typed Markdown (skips LLM generation).

**Body:**
```json
{
  "markdown": "string"
}
```

### `PATCH /editor/runs/{run_id}/draft`

Saves manual Markdown corrections and queues preview re-render.

**Body:**

```json
{
  "markdown": "string"
}
```

### `POST /editor/pages/{page_id}/proposals`

Creates an LLM-generated Markdown proposal without modifying the current draft.

**Body:**

```json
{
  "instructions": "string"
}
```

### `GET /editor/proposals/{proposal_id}`

Returns one Markdown proposal (content, status, diff against current draft).

### `POST /editor/proposals/{proposal_id}/apply`

Applies a ready proposal to the current draft and queues preview render.

### `POST /editor/proposals/{proposal_id}/reject`

Rejects a proposal without modifying any draft.

### `POST /editor/runs/{run_id}/draft-versions/{version_id}/restore`

Restores a previously validated draft version as the current draft.

### `POST /editor/runs/{run_id}/preview`

Queues Confluence-calculated preview rendering for the current draft.

### `POST /editor/runs/{run_id}/publish`

Queues publication. The worker performs a drift check against the live Confluence page before publishing.

### `POST /editor/pages/{page_id}/reset`

Cancels all active runs and deletes all draft versions for a page.

### `POST /editor/runs/{run_id}/cancel`

Cancels a single draft run.

---

## Chat

### `POST /chat/sessions`

Creates a new documentation chat session.

### `GET /chat/sessions/{session_id}/messages`

Returns all messages in a chat session.

### `POST /chat/sessions/{session_id}/messages`

Persists a question and queues a worker RAG answer (async, poll `/jobs/{id}` for result).

**Body:**
```json
{
  "question": "string",
  "settings": { "mode": "mix", "top_k": 40, ... }
}
```

### `POST /chat/sessions/{session_id}/stream`

Persists a question and streams a LightRAG-grounded answer via SSE.

**Body:** same as `/messages`

---

## LightRAG status

### `GET /lightrag/status`

Proxies LightRAG health, pipeline state, and document counts. Used by the dashboard.

---

## Worker tasks

The following Celery tasks are dispatched by the API. They are not directly callable via HTTP.

| Task | Triggered by |
|------|-------------|
| `cm_worker.sync_space` | `POST /sync/runs` |
| `cm_worker.scheduled_sync` | `cm-beat` Celery Beat scheduler (cron) |
| `cm_worker.refresh_page` | `POST /confluence/pages/{id}/refresh` |
| `cm_worker.create_empty_page` | `POST /confluence/pages` |
| `cm_worker.delete_page` | `DELETE /confluence/pages/{id}` |
| `cm_worker.move_page` | `POST /confluence/pages/{id}/move` |
| `cm_worker.generate_markdown` | `POST /editor/runs` |
| `cm_worker.render_draft` | `PATCH /editor/runs/{id}/draft` |
| `cm_worker.render_preview` | `POST /editor/runs/{id}/preview` |
| `cm_worker.publish_page` | `POST /editor/runs/{id}/publish` |
| `cm_worker.propose_markdown_update` | `POST /editor/pages/{id}/proposals` |
| `cm_worker.convert_markdown` | Internal (called by generate/render tasks) |
| `cm_worker.answer_question` | `POST /chat/sessions/{id}/messages` |

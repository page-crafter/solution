import json
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

from cm_shared.db.session import SessionLocal, get_session
from cm_shared.models.chat import ChatMessage, ChatSession
from cm_shared.models.confluence import ConfluencePage
from cm_shared.schemas.chat import (
    ChatMessageRead,
    ChatSessionRead,
    ChatStreamRequest,
    CreateChatSessionRequest,
)
from cm_shared.settings.app import get_settings
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from cm_api.auth.dependencies import get_current_user
from cm_api.auth.user import CurrentUser
from cm_api.services.lightrag import stream_lightrag_query

router = APIRouter(prefix="/chat", tags=["chat"])


def encode_ndjson(payload: dict[str, Any]) -> str:
    """Serialize one payload as an NDJSON line."""
    return f"{json.dumps(payload, ensure_ascii=False)}\n"


def full_conversation_history(
    messages: list[ChatMessage],
) -> list[dict[str, str]]:
    """Return all previous user/assistant messages in LightRAG history format."""
    relevant = [message for message in messages if message.role in {"user", "assistant"}]
    return [{"role": message.role, "content": message.content} for message in relevant]


def conversation_history_characters(history: list[dict[str, str]]) -> int:
    """Return the number of characters sent as conversation history."""
    return sum(len(item["content"]) for item in history)


def build_lightrag_query_payload(
    message_text: str,
    request: ChatStreamRequest,
    conversation_history: list[dict[str, str]],
) -> dict[str, Any]:
    """Build the LightRAG stream payload without duplicating the current question."""
    return {
        **request.settings.model_dump(exclude_none=True),
        "query": message_text,
        "response_type": "Multiple Paragraphs",
        "include_references": True,
        "include_chunk_content": True,
        "stream": True,
        "conversation_history": conversation_history,
    }


def reference_source(reference: dict[str, Any]) -> str:
    """Return the best available document source from a LightRAG reference."""
    for key in ("file_path", "file_source", "source", "document_id"):
        value = reference.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def confluence_id_from_reference(reference: dict[str, Any]) -> str | None:
    """Extract a Confluence id from the file source convention used for LightRAG."""
    source = reference_source(reference)
    parts = source.split(":")
    if len(parts) >= 3 and parts[0] == "confluence":
        return parts[-1]
    return None


def reference_snippet(reference: dict[str, Any]) -> str:
    """Extract a short snippet from a LightRAG reference."""
    content = reference.get("content")
    if isinstance(content, list):
        text = "\n\n".join(str(item) for item in content if item)
    elif isinstance(content, str):
        text = content
    else:
        text = ""
    return text[:220]


def absolute_confluence_url(value: str | None) -> str | None:
    """Return an absolute Confluence URL from a stored or REST-provided link."""
    if not value:
        return None
    if urlparse(value).scheme:
        return value

    base_url = get_settings().confluence_base_url.rstrip("/")
    return f"{base_url}/{value.lstrip('/')}"


def confluence_page_url(page: ConfluencePage | None, confluence_id: str | None) -> str | None:
    """Resolve the best Confluence browser URL for a citation."""
    if page:
        for value in (page.web_url, page.tiny_url, page.edit_url):
            if url := absolute_confluence_url(value):
                return url
    if confluence_id:
        return absolute_confluence_url(f"/pages/viewpage.action?pageId={confluence_id}")
    return None


def pages_by_confluence_id(
    session: Session,
    confluence_ids: set[str],
) -> dict[str, ConfluencePage]:
    """Load synced Confluence pages for a set of Confluence ids."""
    if not confluence_ids:
        return {}
    return {
        page.confluence_id: page
        for page in session.scalars(
            select(ConfluencePage).where(ConfluencePage.confluence_id.in_(confluence_ids))
        )
    }


def map_lightrag_references(
    session: Session,
    references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert LightRAG references into the citation shape used by the UI."""
    confluence_ids = {
        confluence_id
        for reference in references
        if (confluence_id := confluence_id_from_reference(reference))
    }
    pages = pages_by_confluence_id(session, confluence_ids)

    citations: list[dict[str, Any]] = []
    for reference in references:
        confluence_id = confluence_id_from_reference(reference)
        page = pages.get(confluence_id or "")
        citations.append(
            {
                "pageId": page.id if page else None,
                "confluenceId": confluence_id,
                "snippet": reference_snippet(reference),
                "filePath": reference_source(reference),
                "referenceId": reference.get("reference_id"),
                "title": page.title if page else None,
                "webUrl": confluence_page_url(page, confluence_id),
            }
        )
    return citations


def parse_citations_json(value: str) -> list[dict[str, Any]]:
    """Parse persisted citation JSON while ignoring malformed legacy values."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [citation for citation in parsed if isinstance(citation, dict)]


def hydrate_citations(
    session: Session,
    citations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Add Confluence browser links to persisted citations when possible."""
    confluence_ids = {
        str(citation["confluenceId"]) for citation in citations if citation.get("confluenceId")
    }
    pages = pages_by_confluence_id(session, confluence_ids)

    hydrated = []
    for citation in citations:
        next_citation = dict(citation)
        confluence_id = (
            str(next_citation["confluenceId"]) if next_citation.get("confluenceId") else None
        )
        page = pages.get(confluence_id or "")
        if page and not next_citation.get("pageId"):
            next_citation["pageId"] = page.id
        if page and not next_citation.get("title"):
            next_citation["title"] = page.title
        if not next_citation.get("webUrl"):
            next_citation["webUrl"] = confluence_page_url(page, confluence_id)
        hydrated.append(next_citation)
    return hydrated


def serialize_chat_message(session: Session, message: ChatMessage) -> ChatMessageRead:
    """Serialize a chat message and backfill citation links for older rows."""
    citations = hydrate_citations(session, parse_citations_json(message.citations_json))
    serialized = ChatMessageRead.model_validate(message)
    citations_json = json.dumps(citations, ensure_ascii=False)
    return serialized.model_copy(update={"citations_json": citations_json})


def integer_value(value: Any) -> int | None:
    """Return a positive integer from provider stats when one is available."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def extract_token_usage(event: dict[str, Any]) -> dict[str, int] | None:
    """Extract exact token usage from a provider event when LightRAG includes it."""
    usage_source = None
    for key in ("usage", "token_usage", "model_usage"):
        if isinstance(event.get(key), dict):
            usage_source = event[key]
            break
    if usage_source is None:
        usage_source = event

    token_usage: dict[str, int] = {}
    key_map = {
        "promptTokens": ("prompt_tokens", "input_tokens", "promptTokens", "inputTokens"),
        "completionTokens": (
            "completion_tokens",
            "output_tokens",
            "completionTokens",
            "outputTokens",
        ),
        "totalTokens": ("total_tokens", "totalTokens"),
    }
    for output_key, candidate_keys in key_map.items():
        for candidate_key in candidate_keys:
            if (value := integer_value(usage_source.get(candidate_key))) is not None:
                token_usage[output_key] = value
                break
    return token_usage or None


def public_stream_error(_error_message: str | None = None) -> str:
    """Return a backend-neutral error message safe for the chat UI."""
    return "Answer generation failed. Please retry."


def stream_stats_payload(
    phase: str,
    started_at: float,
    history_message_count: int,
    history_chars: int,
    response_chars: int,
    chunk_count: int,
    reference_count: int,
    stream_event_count: int,
    token_usage: dict[str, int] | None,
    error: str | None = None,
) -> dict[str, Any]:
    """Build the stats payload emitted through the chat stream."""
    payload: dict[str, Any] = {
        "phase": phase,
        "elapsedMs": round((perf_counter() - started_at) * 1000),
        "historyMessageCount": history_message_count,
        "historyChars": history_chars,
        "responseChars": response_chars,
        "chunkCount": chunk_count,
        "referenceCount": reference_count,
        "streamEventCount": stream_event_count,
        "tokenUsage": token_usage,
    }
    if error:
        payload["error"] = error
    return payload


async def chat_stream_events(
    session_id: str,
    query_payload: dict[str, Any],
    history_message_count: int = 0,
    history_chars: int = 0,
) -> AsyncIterator[str]:
    """Proxy LightRAG query stream and persist the final assistant message."""
    content_parts: list[str] = []
    references: list[dict[str, Any]] = []
    error_message: str | None = None
    started_at = perf_counter()
    chunk_count = 0
    stream_event_count = 0
    token_usage: dict[str, int] | None = None

    def stats_event(phase: str, error: str | None = None) -> str:
        return encode_ndjson(
            {
                "stats": stream_stats_payload(
                    phase=phase,
                    started_at=started_at,
                    history_message_count=history_message_count,
                    history_chars=history_chars,
                    response_chars=sum(len(part) for part in content_parts),
                    chunk_count=chunk_count,
                    reference_count=len(references),
                    stream_event_count=stream_event_count,
                    token_usage=token_usage,
                    error=error,
                )
            }
        )

    yield stats_event("started")

    try:
        async for event in stream_lightrag_query(query_payload):
            stream_event_count += 1
            if usage := extract_token_usage(event):
                token_usage = usage
            if raw_references := event.get("references"):
                references = list(raw_references)
                with SessionLocal() as session:
                    citations = map_lightrag_references(session, references)
                yield encode_ndjson({"references": citations})
                yield stats_event("streaming")
            if response := event.get("response"):
                chunk_count += 1
                response_text = str(response)
                content_parts.append(response_text)
                yield encode_ndjson({"delta": response_text})
                yield stats_event("streaming")
            if error := event.get("error"):
                error_message = str(error)
                public_error = public_stream_error(error_message)
                yield encode_ndjson({"error": public_error})
                yield stats_event("failed", public_error)
                break
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        public_error = public_stream_error(error_message)
        yield encode_ndjson({"error": public_error})
        yield stats_event("failed", public_error)

    answer = "".join(content_parts).strip()
    if not answer:
        if not error_message:
            yield stats_event("completed")
        return

    if error_message:
        answer = f"{answer}\n\n[Answer stream interrupted. Please retry.]"

    with SessionLocal() as session:
        citations = map_lightrag_references(session, references)
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            citations_json=json.dumps(citations, ensure_ascii=False),
        )
        session.add(assistant_message)
        session.commit()
        session.refresh(assistant_message)
        serialized_message = serialize_chat_message(session, assistant_message)
        yield encode_ndjson({"assistant_message": serialized_message.model_dump()})
        if not error_message:
            yield stats_event("completed")


@router.post("/sessions", response_model=ChatSessionRead)
def create_chat_session(
    request: CreateChatSessionRequest,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
) -> ChatSessionRead:
    """Create a documentation chat session."""
    chat_session = ChatSession(title=request.title)
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRead])
def list_messages(
    session_id: str,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
) -> list[ChatMessageRead]:
    """Return all messages for a chat session."""
    messages = session.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    return [serialize_chat_message(session, message) for message in messages]


@router.post("/sessions/{session_id}/stream")
def stream_question(
    session_id: str,
    request: ChatStreamRequest,
    session: Session = Depends(get_session),
    _user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """Persist a question and stream a LightRAG-grounded answer."""
    message_text = request.message.strip()
    if not message_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    chat_session = session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    previous_messages = list(
        session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        ).all()
    )
    message = ChatMessage(session_id=session_id, role="user", content=message_text)
    session.add(message)
    session.commit()

    conversation_history = full_conversation_history(previous_messages)
    query_payload = build_lightrag_query_payload(message_text, request, conversation_history)
    return StreamingResponse(
        chat_stream_events(
            session_id,
            query_payload,
            history_message_count=len(conversation_history),
            history_chars=conversation_history_characters(conversation_history),
        ),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

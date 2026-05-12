import asyncio
import json
from types import SimpleNamespace
from typing import Any

from cm_api.routers.chat import (
    build_lightrag_query_payload,
    chat_stream_events,
    confluence_page_url,
    full_conversation_history,
    map_lightrag_references,
)
from cm_shared.schemas.chat import ChatStreamRequest
from cm_shared.settings.app import get_settings


class FakeSession:
    def __init__(self, pages: list[Any]) -> None:
        self.pages = pages

    def scalars(self, _query: Any) -> list[Any]:
        return self.pages


def clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_confluence_page_url_resolves_relative_page_links(monkeypatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence.local/wiki")
    page = SimpleNamespace(web_url="/display/DOC/Setup", tiny_url=None, edit_url=None)

    assert confluence_page_url(page, "123") == "http://confluence.local/wiki/display/DOC/Setup"

    clear_settings_cache()


def test_map_lightrag_references_adds_confluence_links(monkeypatch) -> None:
    clear_settings_cache()
    monkeypatch.setenv("CONFLUENCE_BASE_URL", "http://confluence.local")
    page = SimpleNamespace(
        id=7,
        confluence_id="123",
        title="Setup Guide",
        web_url="/display/DOC/Setup",
        tiny_url=None,
        edit_url=None,
    )

    citations = map_lightrag_references(
        FakeSession([page]),
        [
            {
                "file_source": "confluence:DOC:123",
                "content": "Relevant paragraph",
                "reference_id": "ref-1",
            }
        ],
    )

    assert citations == [
        {
            "pageId": 7,
            "confluenceId": "123",
            "snippet": "Relevant paragraph",
            "filePath": "confluence:DOC:123",
            "referenceId": "ref-1",
            "title": "Setup Guide",
            "webUrl": "http://confluence.local/display/DOC/Setup",
        }
    ]

    clear_settings_cache()


def test_full_conversation_history_keeps_all_previous_chat_messages_in_order() -> None:
    messages = [
        SimpleNamespace(role="user", content="First question"),
        SimpleNamespace(role="assistant", content="First answer"),
        SimpleNamespace(role="system", content="Ignore me"),
        SimpleNamespace(role="user", content="Second question"),
        SimpleNamespace(role="assistant", content="Second answer"),
    ]

    assert full_conversation_history(messages) == [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Second question"},
        {"role": "assistant", "content": "Second answer"},
    ]


def test_lightrag_payload_sends_current_question_outside_history() -> None:
    previous_messages = [
        SimpleNamespace(role="user", content="Previous question"),
        SimpleNamespace(role="assistant", content="Previous answer"),
    ]
    request = ChatStreamRequest(message="Current question")
    history = full_conversation_history(previous_messages)

    payload = build_lightrag_query_payload(request.message, request, history)

    assert payload["query"] == "Current question"
    assert payload["conversation_history"] == [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    assert "Current question" not in [item["content"] for item in payload["conversation_history"]]


def test_chat_stream_events_emits_started_streaming_and_completed_stats(monkeypatch) -> None:
    async def fake_stream(_payload: dict[str, Any]):
        yield {"response": " ", "usage": {"total_tokens": 42}}

    monkeypatch.setattr("cm_api.routers.chat.stream_lightrag_query", fake_stream)

    async def collect_events() -> list[dict[str, Any]]:
        return [
            json.loads(line)
            async for line in chat_stream_events(
                "session-1",
                {},
                history_message_count=2,
                history_chars=29,
            )
        ]

    events = asyncio.run(collect_events())
    stats_events = [event["stats"] for event in events if "stats" in event]

    assert stats_events[0]["phase"] == "started"
    assert stats_events[0]["historyMessageCount"] == 2
    assert stats_events[0]["historyChars"] == 29
    assert stats_events[1]["phase"] == "streaming"
    assert stats_events[1]["chunkCount"] == 1
    assert stats_events[1]["responseChars"] == 1
    assert stats_events[1]["tokenUsage"] == {"totalTokens": 42}
    assert stats_events[-1]["phase"] == "completed"


def test_chat_stream_events_emits_failed_stats_on_lightrag_error(monkeypatch) -> None:
    async def fake_stream(_payload: dict[str, Any]):
        yield {"error": "LightRAG unavailable"}

    monkeypatch.setattr("cm_api.routers.chat.stream_lightrag_query", fake_stream)

    async def collect_events() -> list[dict[str, Any]]:
        return [json.loads(line) async for line in chat_stream_events("session-1", {})]

    events = asyncio.run(collect_events())

    assert {"error": "Answer generation failed. Please retry."} in events
    assert events[-1]["stats"]["phase"] == "failed"
    assert events[-1]["stats"]["error"] == "Answer generation failed. Please retry."

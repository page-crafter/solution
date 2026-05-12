from types import SimpleNamespace

from cm_worker.page_editor.generate_markdown import (
    AutoRoutedOpenAIChatModel,
    build_prompt,
    create_chat_model,
    generate_markdown_draft,
    should_omit_openai_model,
)
from cm_worker.page_editor.proposals import (
    build_proposal_prompt,
    fallback_proposal,
    parse_edit_response,
)


def test_generation_uses_only_target_page_and_instruction(monkeypatch) -> None:
    """Page editor generation must not depend on retrieved document chunks."""
    captured = {}

    class Graph:
        def invoke(self, state):
            captured.update(state)
            return {**state, "markdown": state["source_text"]}

    monkeypatch.setattr(
        "cm_worker.page_editor.generate_markdown.build_update_graph",
        lambda: Graph(),
    )

    markdown = generate_markdown_draft(
        session=SimpleNamespace(),
        run=SimpleNamespace(instruction="Add the game of life"),
        page=SimpleNamespace(id=3, extracted_text="Page 3 text"),
    )

    assert markdown == "Page 3 text"
    assert captured == {
        "instruction": "Add the game of life",
        "source_text": "Page 3 text",
        "markdown": "",
    }


def test_generation_prompt_forbids_other_page_sources() -> None:
    """The model prompt forbids vector search and other page sources."""
    prompt = build_prompt(
        {
            "instruction": "Add the game of life",
            "source_text": "Page 3 text",
            "markdown": "",
        }
    )

    assert "Use only the current page text" in prompt
    assert "Do not use retrieved context, vector search, or content from other pages" in prompt
    assert "Relevant same-page context" not in prompt


def test_auto_model_config_uses_client_that_omits_model(monkeypatch) -> None:
    """Proxy auto-routing requires leaving model out of the chat completions payload."""
    monkeypatch.setattr(
        "cm_worker.page_editor.generate_markdown.get_settings",
        lambda: SimpleNamespace(
            llm_provider="openai",
            effective_openai_api_key="test-key",
            openai_base_url="http://proxy.test/v1",
            openai_model="auto",
        ),
    )

    model = create_chat_model()

    assert isinstance(model, AutoRoutedOpenAIChatModel)
    assert "model" not in model._build_payload("hello")


def test_auto_routed_openai_client_posts_without_model(monkeypatch) -> None:
    """The auto-routed client sends a chat completions request without model."""
    captured = {}

    class Response:
        status_code = 200
        is_error = False

        def json(self):
            return {"choices": [{"message": {"content": "# Draft"}}]}

    class Client:
        def __init__(self, *, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def post(self, url, *, headers, json):
            captured.update({"url": url, "headers": headers, "json": json})
            return Response()

    monkeypatch.setattr("cm_worker.page_editor.generate_markdown.httpx.Client", Client)

    response = AutoRoutedOpenAIChatModel(
        api_key="test-key",
        base_url="http://proxy.test/v1/",
        temperature=0.2,
    ).invoke("hello")

    assert response.content == "# Draft"
    assert captured["url"] == "http://proxy.test/v1/chat/completions"
    assert captured["headers"] == {"Authorization": "Bearer test-key"}
    assert captured["json"] == {
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
        "temperature": 0.2,
    }
    assert "model" not in captured["json"]


def test_should_omit_openai_model_accepts_auto_aliases() -> None:
    """Auto aliases let compatible proxy endpoints route without a model field."""
    assert should_omit_openai_model("")
    assert should_omit_openai_model("auto")
    assert should_omit_openai_model("AUTO-ROUTE")
    assert not should_omit_openai_model("gpt-5.2")


def test_proposal_prompt_requests_complete_markdown_document() -> None:
    """Proposals must return a complete draft, not mutate the saved draft directly."""
    prompt = build_proposal_prompt("# Existing", "Add setup troubleshooting")

    assert "Return only JSON" in prompt
    assert "complete updated document" in prompt
    assert "Preserve all existing sections" in prompt
    assert "Add setup troubleshooting" in prompt
    assert "# Existing" in prompt


def test_proposal_parses_fenced_json_response() -> None:
    """The LLM response parser accepts the common fenced JSON response shape."""
    proposal = parse_edit_response(
        '```json\n{"summary": "Added setup", "markdown": "# Updated"}\n```'
    )

    assert proposal == {"summary": "Added setup", "markdown": "# Updated"}


def test_proposal_fallback_uses_current_page_as_base() -> None:
    """When no provider is configured, the fallback appends the requested update to the base."""
    proposal = fallback_proposal("Current page text", "Add setup steps")

    assert proposal["markdown"].startswith("Current page text")
    assert "Add setup steps" in proposal["markdown"]

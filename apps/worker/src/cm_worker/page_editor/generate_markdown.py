from dataclasses import dataclass
from typing import Any, TypedDict

import httpx
from cm_shared.models.confluence import ConfluencePage
from cm_shared.models.page_editor import PageEditRun
from cm_shared.settings.app import get_settings
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session


class UpdateState(TypedDict):
    """State passed through the documentation update LangGraph."""

    instruction: str
    source_text: str
    markdown: str


@dataclass
class ChatModelResponse:
    """Small response shape matching the part of LangChain responses we use."""

    content: str


class AutoRoutedOpenAIChatModel:
    """OpenAI-compatible chat client that omits model for auto-routing proxies."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        temperature: float,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def _build_payload(self, prompt: str) -> dict[str, Any]:
        return {
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": self.temperature,
        }

    def _extract_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("OpenAI-compatible response did not include choices")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ValueError("OpenAI-compatible response choice has an unexpected shape")

        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and isinstance(part.get("text"), str)
                ]
                if parts:
                    return "".join(parts)

        text = first_choice.get("text")
        if isinstance(text, str):
            return text

        raise ValueError("OpenAI-compatible response did not include message content")

    def _format_error(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if isinstance(message, str) and message:
                    return message

        return response.text or response.reason_phrase

    def invoke(self, prompt: str) -> ChatModelResponse:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=self._build_payload(prompt),
            )

        if response.is_error:
            raise RuntimeError(
                "OpenAI-compatible endpoint returned "
                f"{response.status_code}: {self._format_error(response)}"
            )

        return ChatModelResponse(content=self._extract_content(response.json()))


def should_omit_openai_model(model: str) -> bool:
    """Return whether the configured model asks the endpoint to auto-route."""
    return model.strip().lower() in {"", "auto", "auto-route"}


def build_prompt(state: UpdateState) -> str:
    """Build the LLM prompt for updating documentation as Markdown."""
    return (
        "You are updating product documentation. Write clear, accurate Markdown.\n"
        "Use only the current page text and the requested instruction as sources.\n"
        "Do not use retrieved context, vector search, or content from other pages.\n"
        "Preserve important facts from the source page and improve only what the instruction "
        "asks.\n\n"
        f"Instruction:\n{state['instruction']}\n\n"
        f"Current page text:\n{state['source_text']}\n"
    )


def create_chat_model():
    """Create the configured chat model or return None when credentials are absent."""
    settings = get_settings()
    openai_api_key = settings.effective_openai_api_key
    if settings.llm_provider == "openai" and openai_api_key:
        if should_omit_openai_model(settings.openai_model):
            return AutoRoutedOpenAIChatModel(
                api_key=openai_api_key,
                base_url=settings.openai_base_url,
                temperature=0.2,
            )

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.openai_model,
            temperature=0.2,
            api_key=openai_api_key,
            base_url=settings.openai_base_url,
        )
    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)
    return None


def fallback_markdown(state: UpdateState) -> str:
    """Generate a deterministic draft when no LLM provider is configured."""
    return (
        "# Documentation update draft\n\n"
        f"## Requested change\n\n{state['instruction']}\n\n"
        "## Updated content\n\n"
        f"{state['source_text'][:4000]}\n"
    )


def draft_node(state: UpdateState) -> UpdateState:
    """LangGraph node that produces the Markdown draft."""
    model = create_chat_model()
    if model is None:
        return {**state, "markdown": fallback_markdown(state)}
    response = model.invoke(build_prompt(state))
    return {**state, "markdown": str(response.content)}


def build_update_graph():
    """Compile the LangGraph used to produce documentation update drafts."""
    graph = StateGraph(UpdateState)
    graph.add_node("draft", draft_node)
    graph.add_edge(START, "draft")
    graph.add_edge("draft", END)
    return graph.compile()


def generate_markdown_draft(session: Session, run: PageEditRun, page: ConfluencePage) -> str:
    """Generate a page edit draft from only the target page and instruction."""
    graph = build_update_graph()
    result = graph.invoke(
        {
            "instruction": run.instruction,
            "source_text": page.extracted_text,
            "markdown": "",
        }
    )
    return str(result["markdown"])

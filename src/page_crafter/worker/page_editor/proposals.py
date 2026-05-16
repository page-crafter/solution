import json
import re
from typing import TypedDict

from page_crafter.worker.page_editor.generate_markdown import create_chat_model


class ProposalDraft(TypedDict):
    """Markdown proposal returned by the LLM."""

    markdown: str
    summary: str


def build_proposal_prompt(base_markdown: str, instruction: str) -> str:
    """Build a prompt that asks for a complete updated Markdown document."""
    return (
        "You are editing Confluence documentation represented as Markdown.\n"
        "Return only JSON with two string keys: summary and markdown.\n"
        "The markdown value must be the complete updated document, not a patch.\n"
        "Use only the current page content and the requested edit.\n"
        "Preserve all existing sections, wording, and prior edits "
        "unless the request explicitly changes them.\n"
        "Preserve existing facts unless the request explicitly changes them.\n\n"
        f"Requested edit:\n{instruction}\n\n"
        f"Current page Markdown or extracted text:\n{base_markdown}\n"
    )


def fallback_proposal(base_markdown: str, instruction: str) -> ProposalDraft:
    """Build a deterministic proposal when no LLM provider is configured."""
    proposed = base_markdown.strip()
    if proposed:
        proposed = f"{proposed}\n\n## Requested update\n\n{instruction.strip()}\n"
    else:
        proposed = f"# Documentation update\n\n{instruction.strip()}\n"
    return {
        "summary": "Prepared a deterministic draft from the requested edit.",
        "markdown": proposed,
    }


def strip_json_fence(value: str) -> str:
    """Remove common fenced-code wrapping around a JSON response."""
    stripped = value.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    return fence_match.group(1).strip() if fence_match else stripped


def parse_edit_response(value: str) -> ProposalDraft:
    """Parse a model response into a proposal, falling back to raw Markdown."""
    stripped = strip_json_fence(value)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return {"summary": "Prepared an updated Markdown draft.", "markdown": value.strip()}

    if not isinstance(payload, dict):
        return {"summary": "Prepared an updated Markdown draft.", "markdown": value.strip()}

    markdown = payload.get("markdown")
    summary = payload.get("summary")
    if not isinstance(markdown, str) or not markdown.strip():
        return {"summary": "Prepared an updated Markdown draft.", "markdown": value.strip()}

    return {
        "summary": summary
        if isinstance(summary, str) and summary.strip()
        else "Prepared an updated Markdown draft.",
        "markdown": markdown.strip(),
    }


def propose_markdown_update(base_markdown: str, instruction: str) -> ProposalDraft:
    """Ask the configured chat model to propose a complete Markdown update."""
    model = create_chat_model()
    if model is None:
        return fallback_proposal(base_markdown, instruction)
    response = model.invoke(build_proposal_prompt(base_markdown, instruction))
    return parse_edit_response(str(response.content))

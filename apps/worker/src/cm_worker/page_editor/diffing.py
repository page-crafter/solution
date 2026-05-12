from difflib import unified_diff

from bs4 import BeautifulSoup


def build_markdown_diff(source_text: str, markdown_draft: str) -> str:
    """Create a unified diff between synced text and generated Markdown."""
    return "".join(
        unified_diff(
            source_text.splitlines(keepends=True),
            markdown_draft.splitlines(keepends=True),
            fromfile="current-documentation.txt",
            tofile="generated-draft.md",
        )
    )


def format_storage_xhtml_for_diff(storage_xhtml: str) -> str:
    """Pretty-print Confluence Storage XHTML so diffs compare stable line units."""
    stripped = storage_xhtml.strip()
    if not stripped:
        return ""

    formatted = BeautifulSoup(stripped, "html.parser").prettify(formatter="minimal").strip()
    return f"{formatted}\n"


def build_storage_diff(source_storage_xhtml: str, generated_storage_xhtml: str) -> str:
    """Create a unified diff between current and generated Confluence Storage XHTML."""
    return "".join(
        unified_diff(
            format_storage_xhtml_for_diff(source_storage_xhtml).splitlines(keepends=True),
            format_storage_xhtml_for_diff(generated_storage_xhtml).splitlines(keepends=True),
            fromfile="current-storage.xhtml",
            tofile="generated-storage.xhtml",
        )
    )

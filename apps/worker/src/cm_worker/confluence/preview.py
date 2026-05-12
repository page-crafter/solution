from bs4 import BeautifulSoup

from cm_worker.confluence.client import ConfluenceClient

PREVIEW_NAMESPACE_WRAPPER = (
    '<div xmlns:ac="http://atlassian.com/content" '
    'xmlns:ri="http://atlassian.com/resource/identifier">{storage}</div>'
)


def storage_for_preview(storage_xhtml: str) -> str:
    """Wrap Storage XHTML with namespaces required by Confluence's preview action."""
    return PREVIEW_NAMESPACE_WRAPPER.format(storage=storage_xhtml)


def render_storage_preview(storage_xhtml: str, content_id: str) -> str:
    """Render generated Storage XHTML through Confluence's preview endpoint."""
    client = ConfluenceClient()
    return client.render_content_preview(storage_for_preview(storage_xhtml), content_id)


def preview_has_rendered_content(preview_html: str) -> bool:
    """Return whether Confluence actually rendered content inside the preview body."""
    soup = BeautifulSoup(preview_html, "html.parser")
    rendered = soup.select_one(".wiki-content")
    if rendered is None:
        return bool(preview_html.strip())
    return any(str(child).strip() for child in rendered.contents)

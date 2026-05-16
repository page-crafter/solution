from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from page_crafter.shared.models.confluence import ConfluencePage
from page_crafter.worker.confluence.client import ConfluenceClient
from page_crafter.worker.extract.xhtml_to_text import extract_text_from_storage
from page_crafter.worker.sync.reconcile_deleted import mark_missing_pages_deleted


@dataclass(frozen=True)
class PageUpsertResult:
    """A page update and whether its Confluence content version changed."""

    page: ConfluencePage
    content_changed: bool


@dataclass(frozen=True)
class SpaceSyncResult:
    """Summary of a Confluence space sync before external RAG submission."""

    page_count: int
    changed_pages: tuple[ConfluencePage, ...]
    unchanged_pages: tuple[ConfluencePage, ...]
    deleted_pages: tuple[ConfluencePage, ...]


def page_url(page: dict[str, Any], key: str) -> str | None:
    """Build an absolute Confluence link from a REST page payload."""
    links = page.get("_links", {})
    value = links.get(key)
    base = links.get("base", "")
    if not value:
        return None
    return f"{base}{value}" if value.startswith("/") else value


def page_parent_id(page: dict[str, Any]) -> str | None:
    """Return the immediate parent Confluence id from a REST page payload."""
    if "_tree_parent_id" in page:
        parent_id = page["_tree_parent_id"]
        return str(parent_id) if parent_id else None
    ancestors = page.get("ancestors", [])
    if not ancestors:
        return None
    parent_id = ancestors[-1].get("id")
    return str(parent_id) if parent_id else None


def page_sort_order(page: dict[str, Any], fallback: int) -> int:
    """Return Confluence's page position when present, otherwise the scan order."""
    if "_tree_sort_order" in page:
        try:
            return int(page["_tree_sort_order"])
        except (TypeError, ValueError):
            return fallback
    position = page.get("extensions", {}).get("position", page.get("position", fallback))
    try:
        return int(position)
    except (TypeError, ValueError):
        return fallback


def upsert_page(
    session: Session,
    page_payload: dict[str, Any],
    *,
    sort_order: int = 0,
) -> ConfluencePage:
    """Create or update one synced Confluence page record."""
    return upsert_page_with_status(session, page_payload, sort_order=sort_order).page


def upsert_page_with_status(
    session: Session,
    page_payload: dict[str, Any],
    *,
    sort_order: int = 0,
) -> PageUpsertResult:
    """Create or update one page and report whether its content version changed."""
    confluence_id = str(page_payload["id"])
    page = session.scalar(
        select(ConfluencePage).where(ConfluencePage.confluence_id == confluence_id)
    )
    version_number = int(page_payload.get("version", {}).get("number", 1))
    content_changed = (
        page is None or page.deleted_at is not None or page.version_number != version_number
    )
    if page is None:
        page = ConfluencePage(confluence_id=confluence_id, space_key="")
        session.add(page)

    storage_xhtml = page_payload.get("body", {}).get("storage", {}).get("value", "")
    page.space_key = page_payload.get("space", {}).get("key", "")
    page.space_name = page_payload.get("space", {}).get("name") or None
    page.parent_confluence_id = page_parent_id(page_payload)
    page.sort_order = page_sort_order(page_payload, sort_order)
    page.title = page_payload.get("title", "Untitled")
    page.status = page_payload.get("status", "current")
    page.version_number = version_number
    page.source_storage_xhtml = storage_xhtml
    page.extracted_text = extract_text_from_storage(storage_xhtml)
    page.web_url = page_url(page_payload, "webui")
    page.edit_url = page_url(page_payload, "edit")
    page.tiny_url = page_url(page_payload, "tinyui")
    page.is_placeholder = not page.extracted_text.strip()
    page.draft_state = "Published"
    page.last_synced_at = datetime.utcnow()
    page.deleted_at = None
    return PageUpsertResult(page=page, content_changed=content_changed)


def sync_space_pages(session: Session, client: ConfluenceClient | None = None) -> SpaceSyncResult:
    """Sync the configured Confluence space and return page counts."""
    confluence = client or ConfluenceClient()
    payloads = confluence.scan_space_pages()
    active_ids = {str(page["id"]) for page in payloads}
    changed_pages: list[ConfluencePage] = []
    unchanged_pages: list[ConfluencePage] = []
    for index, payload in enumerate(payloads):
        result = upsert_page_with_status(
            session,
            payload,
            sort_order=index,
        )
        if result.content_changed:
            changed_pages.append(result.page)
        else:
            unchanged_pages.append(result.page)
    deleted_pages = mark_missing_pages_deleted(session, active_ids)
    return SpaceSyncResult(
        page_count=len(payloads),
        changed_pages=tuple(changed_pages),
        unchanged_pages=tuple(unchanged_pages),
        deleted_pages=tuple(deleted_pages),
    )

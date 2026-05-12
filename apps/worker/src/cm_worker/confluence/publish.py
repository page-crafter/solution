from sqlalchemy.orm import Session

from cm_shared.models.confluence import ConfluencePage
from cm_shared.models.page_editor import PageEditRun
from cm_worker.confluence.client import ConfluenceClient


def publish_generated_page(session: Session, run: PageEditRun, page: ConfluencePage) -> None:
    """Publish generated Storage XHTML after checking Confluence version drift."""
    client = ConfluenceClient()
    latest = client.get_page(page.confluence_id)
    latest_version = int(latest.get("version", {}).get("number", page.version_number))
    if latest_version != run.source_version:
        run.status = "blocked"
        run.draft_status = "Publish blocked"
        run.error_message = "The Confluence page changed since this draft was created."
        return
    if not run.generated_storage_xhtml:
        run.status = "blocked"
        run.draft_status = "Publish blocked"
        run.error_message = "No generated XHTML is available to publish."
        return

    updated = client.update_page(
        page.confluence_id,
        page.title,
        latest_version,
        run.generated_storage_xhtml,
    )
    page.version_number = int(updated.get("version", {}).get("number", latest_version + 1))
    page.source_storage_xhtml = run.generated_storage_xhtml
    page.extracted_text = run.markdown_draft or page.extracted_text
    page.is_placeholder = False
    page.draft_state = "Published"
    run.status = "published"
    run.draft_status = "Published"
    run.error_message = None

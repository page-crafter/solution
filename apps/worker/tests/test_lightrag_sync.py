from types import SimpleNamespace

from cm_worker.rag.lightrag import (
    LightRagDocument,
    build_lightrag_document,
    lightrag_file_source,
    pages_missing_from_lightrag,
    sync_pages_to_lightrag,
)


class FakeLightRagClient:
    def __init__(self) -> None:
        self.cleared = False
        self.deleted_sources: list[str] = []
        self.inserted_batches: list[list[LightRagDocument]] = []

    def clear_documents(self) -> None:
        self.cleared = True

    def delete_file_sources(self, file_sources) -> int:
        self.deleted_sources.extend(file_sources)
        return len(file_sources)

    def insert_texts(self, documents) -> str:
        self.inserted_batches.append(list(documents))
        return "insert-track"


def test_lightrag_document_uses_stable_confluence_source() -> None:
    """LightRAG sources keep the Confluence id needed by chat citations."""
    page = SimpleNamespace(
        confluence_id="12345",
        space_key="DOC",
        space_name="Docs",
        title="Install guide",
        version_number=7,
        web_url="http://confluence/pages/12345",
        extracted_text="Install the app.",
    )

    document = build_lightrag_document(page)

    assert document is not None
    assert document.file_source == "confluence:DOC:12345"
    assert lightrag_file_source(page) == "confluence:DOC:12345"
    assert "# Install guide" in document.text
    assert "Confluence ID: 12345" in document.text
    assert "Install the app." in document.text


def test_sync_pages_to_lightrag_clears_then_submits_non_empty_pages() -> None:
    """Full space sync replaces the LightRAG workspace with current page text."""
    client = FakeLightRagClient()
    pages = [
        SimpleNamespace(
            confluence_id="1",
            space_key="DOC",
            title="Page 1",
            extracted_text="Useful text",
        ),
        SimpleNamespace(
            confluence_id="2",
            space_key="DOC",
            title="Empty page",
            extracted_text=" ",
        ),
    ]

    result = sync_pages_to_lightrag(pages, clear_existing=True, client=client)

    assert client.cleared is True
    assert client.deleted_sources == []
    assert result.submitted_count == 1
    assert result.skipped_count == 1
    assert result.track_ids == ("insert-track",)
    assert client.inserted_batches[0][0].file_source == "confluence:DOC:1"


def test_incremental_lightrag_sync_replaces_matching_sources() -> None:
    """Page refresh deletes the previous LightRAG source before submitting it again."""
    client = FakeLightRagClient()
    page = SimpleNamespace(
        confluence_id="42",
        space_key="DOC",
        title="Changed page",
        extracted_text="New text",
    )

    result = sync_pages_to_lightrag([page], clear_existing=False, client=client)

    assert client.cleared is False
    assert client.deleted_sources == ["confluence:DOC:42"]
    assert result.submitted_count == 1
    assert client.inserted_batches[0][0].text.endswith("New text")


def test_incremental_lightrag_sync_skips_empty_submission_without_delete_lookup() -> None:
    """Unchanged pages already present in LightRAG do not trigger replacement work."""
    client = FakeLightRagClient()

    result = sync_pages_to_lightrag([], clear_existing=False, client=client)

    assert client.cleared is False
    assert client.deleted_sources == []
    assert client.inserted_batches == []
    assert result.submitted_count == 0
    assert result.skipped_count == 0
    assert result.track_ids == ()


def test_pages_missing_from_lightrag_keeps_unchanged_pages_without_source() -> None:
    """An unchanged Confluence version is still submitted when LightRAG lacks the file."""
    present = SimpleNamespace(confluence_id="1", space_key="DOC")
    missing = SimpleNamespace(confluence_id="2", space_key="DOC")

    pages = pages_missing_from_lightrag(
        [present, missing],
        existing_sources={"confluence:DOC:1"},
    )

    assert pages == [missing]

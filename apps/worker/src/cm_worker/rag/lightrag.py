import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
from cm_shared.settings.app import get_settings


@dataclass(frozen=True)
class LightRagDocument:
    """Document payload submitted to LightRAG for external indexing."""

    file_source: str
    text: str


@dataclass(frozen=True)
class LightRagSyncResult:
    """Summary of a LightRAG ingestion operation."""

    submitted_count: int
    skipped_count: int
    track_ids: tuple[str, ...]


def lightrag_file_source(page: Any) -> str:
    """Build the stable source id used to map LightRAG references back to Confluence."""
    settings = get_settings()
    space_key = getattr(page, "space_key", "") or settings.confluence_space_key
    confluence_id = getattr(page, "confluence_id", "")
    return f"confluence:{space_key}:{confluence_id}"


def build_lightrag_document(page: Any) -> LightRagDocument | None:
    """Convert one synced Confluence page into a LightRAG text document."""
    body = (getattr(page, "extracted_text", "") or "").strip()
    if not body:
        return None

    title = getattr(page, "title", "") or "Untitled"
    space = getattr(page, "space_name", None) or getattr(page, "space_key", "") or "Unknown"
    version = getattr(page, "version_number", None)
    web_url = getattr(page, "web_url", None)

    metadata_lines = [
        f"# {title}",
        "",
        f"- Confluence ID: {getattr(page, 'confluence_id', '')}",
        f"- Space: {space}",
    ]
    if version is not None:
        metadata_lines.append(f"- Version: {version}")
    if web_url:
        metadata_lines.append(f"- URL: {web_url}")

    text = "\n".join([*metadata_lines, "", body])
    return LightRagDocument(file_source=lightrag_file_source(page), text=text)


def chunked[T](values: Sequence[T], size: int) -> Iterable[Sequence[T]]:
    """Yield fixed-size slices without requiring Python version-specific helpers."""
    for start in range(0, len(values), size):
        yield values[start : start + size]


class LightRagClient:
    """Synchronous LightRAG API client used by Celery worker tasks."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.lightrag_base_url.rstrip("/")
        self._client = client

    def headers(self) -> dict[str, str]:
        """Build JSON headers, including the optional LightRAG API key."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.settings.lightrag_api_key:
            headers["X-API-Key"] = self.settings.lightrag_api_key
        return headers

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Call LightRAG and return its JSON response or raise a clear error."""
        timeout = httpx.Timeout(connect=10.0, read=300.0, write=300.0, pool=10.0)
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=timeout)
        try:
            response = client.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers(),
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(f"LightRAG request failed: {exc}") from exc
        finally:
            if owns_client:
                client.close()

        if response.status_code >= 400:
            detail = response.text.strip()
            raise RuntimeError(detail or f"LightRAG returned HTTP {response.status_code}")
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(f"LightRAG returned a non-JSON response: {response.text}") from exc
        if not isinstance(data, dict):
            raise RuntimeError("LightRAG returned an unexpected response shape")
        return data

    def clear_documents(self) -> None:
        """Clear the dedicated LightRAG workspace before a full Confluence re-sync."""
        self.wait_until_idle()
        response = self.request_with_idle_retry("DELETE", "/documents")
        status = response.get("status")
        if status not in {"success", "partial_success"}:
            message = response.get("message") or "Unable to clear LightRAG documents"
            raise RuntimeError(str(message))

    def insert_texts(self, documents: Sequence[LightRagDocument]) -> str | None:
        """Submit one batch of text documents to LightRAG."""
        if not documents:
            return None
        response = self.request(
            "POST",
            "/documents/texts",
            json={
                "texts": [document.text for document in documents],
                "file_sources": [document.file_source for document in documents],
            },
        )
        status = response.get("status")
        if status not in {"success", "duplicated", "partial_success"}:
            message = response.get("message") or "Unable to submit documents to LightRAG"
            raise RuntimeError(str(message))
        track_id = response.get("track_id")
        return str(track_id) if track_id else None

    def list_documents(self) -> list[dict[str, Any]]:
        """Return all LightRAG document status rows."""
        page = 1
        documents: list[dict[str, Any]] = []
        while True:
            response = self.request(
                "POST",
                "/documents/paginated",
                json={
                    "page": page,
                    "page_size": 200,
                    "sort_field": "updated_at",
                    "sort_direction": "desc",
                },
            )
            page_documents = response.get("documents", [])
            if not isinstance(page_documents, list):
                raise RuntimeError("LightRAG returned invalid documents pagination data")
            documents.extend(
                document for document in page_documents if isinstance(document, dict)
            )
            pagination = response.get("pagination") or {}
            if not isinstance(pagination, dict) or not pagination.get("has_next"):
                return documents
            page += 1

    def file_sources(self) -> set[str]:
        """Return the source identifiers already present in LightRAG."""
        return {
            str(document["file_path"])
            for document in self.list_documents()
            if document.get("file_path")
        }

    def pipeline_status(self) -> dict[str, Any]:
        """Return the current LightRAG document pipeline state."""
        return self.request("GET", "/documents/pipeline_status")

    def wait_until_idle(self, timeout_seconds: int | None = None) -> None:
        """Wait until LightRAG accepts document mutations again."""
        timeout = timeout_seconds or self.settings.lightrag_pipeline_timeout_seconds
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status = self.pipeline_status()
            if not status.get("busy"):
                return
            time.sleep(2)
        raise RuntimeError("Timed out waiting for the LightRAG document pipeline")

    def request_with_idle_retry(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Retry once when LightRAG rejects a mutation because indexing is still running."""
        try:
            return self.request(method, path, **kwargs)
        except RuntimeError as exc:
            if "pipeline is busy" not in str(exc).lower():
                raise
            self.wait_until_idle()
            return self.request(method, path, **kwargs)

    def delete_documents(self, doc_ids: Sequence[str]) -> None:
        """Ask LightRAG to delete documents by id."""
        if not doc_ids:
            return
        self.wait_until_idle()
        response = self.request_with_idle_retry(
            "DELETE",
            "/documents/delete_document",
            json={
                "doc_ids": list(doc_ids),
                "delete_file": False,
                "delete_llm_cache": False,
            },
        )
        status = response.get("status")
        if status != "deletion_started":
            message = response.get("message") or "Unable to delete LightRAG documents"
            raise RuntimeError(str(message))

    def delete_file_sources(self, file_sources: Sequence[str], timeout_seconds: int = 60) -> int:
        """Delete existing LightRAG documents matching the given source identifiers."""
        source_set = set(file_sources)
        if not source_set:
            return 0
        documents = self.list_documents()
        doc_ids = [
            str(document["id"])
            for document in documents
            if document.get("file_path") in source_set and document.get("id")
        ]
        self.delete_documents(doc_ids)
        if doc_ids:
            self.wait_for_file_sources_absent(source_set, timeout_seconds=timeout_seconds)
        return len(doc_ids)

    def wait_for_file_sources_absent(
        self,
        file_sources: set[str],
        timeout_seconds: int,
    ) -> None:
        """Wait until asynchronous LightRAG deletion has removed matching sources."""
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            remaining = {
                str(document.get("file_path"))
                for document in self.list_documents()
                if document.get("file_path") in file_sources
            }
            if not remaining:
                return
            time.sleep(1)
        raise RuntimeError("Timed out waiting for LightRAG document deletion")


def sync_pages_to_lightrag(
    pages: Sequence[Any],
    *,
    clear_existing: bool,
    client: LightRagClient | None = None,
) -> LightRagSyncResult:
    """Submit synced Confluence pages to LightRAG."""
    lightrag = client or LightRagClient()
    documents: list[LightRagDocument] = []
    skipped_count = 0
    for page in pages:
        document = build_lightrag_document(page)
        if document is None:
            skipped_count += 1
            continue
        documents.append(document)

    if clear_existing:
        lightrag.clear_documents()
    elif documents:
        lightrag.delete_file_sources([document.file_source for document in documents])

    batch_size = 25
    track_ids: list[str] = []
    for batch in chunked(documents, batch_size):
        track_id = lightrag.insert_texts(batch)
        if track_id:
            track_ids.append(track_id)

    return LightRagSyncResult(
        submitted_count=len(documents),
        skipped_count=skipped_count,
        track_ids=tuple(track_ids),
    )


def pages_missing_from_lightrag(
    pages: Sequence[Any],
    existing_sources: set[str],
) -> list[Any]:
    """Return pages whose LightRAG source document is not present yet."""
    return [page for page in pages if lightrag_file_source(page) not in existing_sources]


def delete_pages_from_lightrag(
    pages: Sequence[Any],
    *,
    client: LightRagClient | None = None,
) -> int:
    """Delete LightRAG documents associated with Confluence pages."""
    lightrag = client or LightRagClient()
    file_sources = [lightrag_file_source(page) for page in pages]
    if not file_sources:
        return 0
    return lightrag.delete_file_sources(file_sources)

import json
from typing import Any

import httpx
from cm_shared.settings.app import get_settings

CONTENT_EXPAND = "body.storage,version,space,ancestors,extensions"
LEGACY_MOVE_POSITIONS = {
    "append": "append",
    "before": "above",
    "after": "below",
}


class ConfluenceClient:
    """Small Data Center REST client using PAT bearer authentication."""

    def __init__(self) -> None:
        """Initialize client configuration from environment settings."""
        self.settings = get_settings()
        self.base_url = self.settings.confluence_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.settings.confluence_pat}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Execute an authenticated Confluence REST request and return JSON data."""
        url = f"{self.base_url}{path}"
        timeout = self.settings.confluence_api_timeout_seconds
        request_headers = {**self.headers, **(headers or {})}
        with httpx.Client(timeout=timeout) as client:
            response = client.request(method, url, headers=request_headers, **kwargs)
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()

    def request_text(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> str:
        """Execute an authenticated Confluence request and return its text body."""
        url = f"{self.base_url}{path}"
        timeout = self.settings.confluence_api_timeout_seconds
        request_headers = {**self.headers, **(headers or {})}
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.request(method, url, headers=request_headers, **kwargs)
            response.raise_for_status()
            return response.text

    def scan_space_pages(self) -> list[dict[str, Any]]:
        """Fetch all current pages from the configured Confluence space."""
        pages: list[dict[str, Any]] = []
        start = 0
        limit = 50
        while True:
            data = self.request(
                "GET",
                (
                    "/rest/api/content"
                    f"?spaceKey={self.settings.confluence_space_key}"
                    "&type=page&status=current"
                    f"&expand={CONTENT_EXPAND},metadata.labels"
                    f"&limit={limit}&start={start}"
                ),
            )
            pages.extend(data.get("results", []))
            if len(data.get("results", [])) < limit:
                tree = self.scan_space_page_tree()
                return [self.enrich_page_tree_metadata(page, tree) for page in pages]
            start += limit

    def enrich_page_tree_metadata(
        self,
        page: dict[str, Any],
        tree: dict[str, tuple[str | None, int]],
    ) -> dict[str, Any]:
        """Attach hierarchy discovered from Confluence child endpoints to a page payload."""
        confluence_id = str(page["id"])
        if confluence_id not in tree:
            return page
        parent_id, sort_order = tree[confluence_id]
        return {
            **page,
            "_tree_parent_id": parent_id,
            "_tree_sort_order": sort_order,
        }

    def page_tree_position(self, page: dict[str, Any], fallback: int) -> int:
        """Return a child page position from Confluence, falling back to child list order."""
        position = page.get("extensions", {}).get("position", page.get("position", fallback))
        try:
            return int(position)
        except (TypeError, ValueError):
            return fallback

    def get_space(self) -> dict[str, Any]:
        """Fetch the configured space with its homepage reference."""
        return self.request(
            "GET",
            f"/rest/api/space/{self.settings.confluence_space_key}?expand=homepage",
        )

    def list_child_pages(self, parent_id: str) -> list[dict[str, Any]]:
        """Fetch direct child pages for a Confluence page."""
        pages: list[dict[str, Any]] = []
        start = 0
        limit = 50
        while True:
            data = self.request(
                "GET",
                (
                    f"/rest/api/content/{parent_id}/child/page"
                    f"?expand={CONTENT_EXPAND}"
                    f"&limit={limit}&start={start}"
                ),
            )
            results = data.get("results", [])
            pages.extend(results)
            if len(results) < limit:
                return pages
            start += limit

    def scan_space_page_tree(self) -> dict[str, tuple[str | None, int]]:
        """Walk Confluence's child-page tree and return parent/order metadata by page id."""
        homepage = self.get_space().get("homepage") or {}
        homepage_id = homepage.get("id")
        if not homepage_id:
            return {}

        tree: dict[str, tuple[str | None, int]] = {str(homepage_id): (None, 0)}
        visited = set[str]()

        def visit(parent_id: str) -> None:
            if parent_id in visited:
                return
            visited.add(parent_id)
            for index, child in enumerate(self.list_child_pages(parent_id)):
                child_id = str(child["id"])
                tree[child_id] = (parent_id, self.page_tree_position(child, index))
                visit(child_id)

        visit(str(homepage_id))
        return tree

    def get_page(self, confluence_id: str) -> dict[str, Any]:
        """Fetch a single page with storage body and version metadata."""
        return self.request(
            "GET",
            f"/rest/api/content/{confluence_id}?expand={CONTENT_EXPAND}",
        )

    def get_page_space_key(self, confluence_id: str) -> str | None:
        """Fetch the Confluence space key for a page id."""
        page = self.request("GET", f"/rest/api/content/{confluence_id}?expand=space")
        return page.get("space", {}).get("key")

    def create_empty_page(self, title: str, parent_id: str | None = None) -> dict[str, Any]:
        """Create an empty Confluence page that can be populated by a later page edit run."""
        payload: dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": self.settings.confluence_space_key},
            "body": {"storage": {"value": "<p></p>", "representation": "storage"}},
        }
        if parent_id:
            payload["ancestors"] = [{"id": parent_id}]
        return self.request("POST", "/rest/api/content", json=payload)

    def convert_storage(self, storage_xhtml: str, content_id: str, target: str) -> dict[str, Any]:
        """Ask Confluence to render Storage XHTML into a target body representation."""
        return self.request(
            "POST",
            f"/rest/api/contentbody/convert/{target}",
            json={
                "representation": "storage",
                "value": storage_xhtml,
                "content": {"id": content_id},
            },
        )

    def render_content_preview(self, storage_xhtml: str, content_id: str) -> str:
        """Render Storage XHTML through Confluence's page preview endpoint."""
        return self.request_text(
            "POST",
            "/pages/rendercontent.action",
            headers={
                "Accept": "text/html, */*",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Atlassian-Token": "no-check",
            },
            data={
                "contentId": content_id,
                "contentType": "page",
                "spaceKey": self.settings.confluence_space_key,
                "xHtml": storage_xhtml,
                "outputType": "display",
            },
        )

    def update_page(
        self,
        confluence_id: str,
        title: str,
        version: int,
        storage_xhtml: str,
    ) -> dict[str, Any]:
        """Publish new Storage XHTML to an existing Confluence page."""
        return self.request(
            "PUT",
            f"/rest/api/content/{confluence_id}",
            json={
                "id": confluence_id,
                "type": "page",
                "title": title,
                "space": {"key": self.settings.confluence_space_key},
                "body": {"storage": {"value": storage_xhtml, "representation": "storage"}},
                "version": {"number": version + 1, "minorEdit": False},
            },
        )

    def delete_page(self, confluence_id: str) -> None:
        """Delete a Confluence page by content id."""
        self.request("DELETE", f"/rest/api/content/{confluence_id}")

    def move_page(
        self,
        confluence_id: str,
        target_id: str,
        position: str = "append",
    ) -> dict[str, Any]:
        """Move a Confluence page under, before, or after another page."""
        legacy_position = LEGACY_MOVE_POSITIONS.get(position)
        if legacy_position is None:
            raise ValueError(f"Unsupported page move position: {position}")
        self.ensure_move_stays_in_configured_space(confluence_id, target_id)

        response_text = self.request_text(
            "POST",
            "/pages/movepage.action",
            headers={
                "Accept": "application/json, text/plain, */*",
                "X-Atlassian-Token": "no-check",
            },
            params={
                "pageId": confluence_id,
                "targetId": target_id,
                "position": legacy_position,
                "mode": "LEGACY",
            },
        )

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            return {"pageId": confluence_id}

        self.ensure_legacy_move_succeeded(data)
        return data

    def ensure_move_stays_in_configured_space(self, confluence_id: str, target_id: str) -> None:
        """Reject moves when either page is outside the configured Confluence space."""
        configured_space = self.settings.confluence_space_key
        page_space = self.get_page_space_key(confluence_id)
        target_space = self.get_page_space_key(target_id)
        if page_space != configured_space or target_space != configured_space:
            raise RuntimeError("Cannot move a page outside the configured Confluence space.")

    def ensure_legacy_move_succeeded(self, data: dict[str, Any]) -> None:
        """Raise when the legacy Data Center move action reports a rejected move."""
        progress = data.get("progressMeter")
        if data.get("valid") is False or data.get("authorized") is False:
            raise RuntimeError("Confluence rejected the page move.")
        if isinstance(progress, dict) and progress.get("completedSuccessfully") is False:
            message = progress.get("status") or progress.get("message") or "Page move failed."
            raise RuntimeError(str(message))

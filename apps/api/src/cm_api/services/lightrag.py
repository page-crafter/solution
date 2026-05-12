import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from cm_shared.settings.app import get_settings


def lightrag_headers() -> dict[str, str]:
    """Build LightRAG API headers from local settings."""
    settings = get_settings()
    headers = {
        "Accept": "application/x-ndjson",
        "Content-Type": "application/json",
    }
    if settings.lightrag_api_key:
        headers["X-API-Key"] = settings.lightrag_api_key
    return headers


async def stream_lightrag_query(payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    """Stream parsed NDJSON query events from the LightRAG API."""
    settings = get_settings()
    url = f"{settings.lightrag_base_url.rstrip('/')}/query/stream"
    timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, headers=lightrag_headers(), json=payload) as response:
            if response.status_code >= 400:
                detail = await response.aread()
                text = detail.decode("utf-8", errors="replace").strip()
                raise RuntimeError(text or f"LightRAG query failed with {response.status_code}")
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Invalid LightRAG stream event: {line}") from exc

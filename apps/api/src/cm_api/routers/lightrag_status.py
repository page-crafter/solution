import httpx
from fastapi import APIRouter

from cm_api.auth.dependencies import require_admin
from cm_api.services.lightrag import lightrag_headers
from cm_shared.schemas.kpis import LightRagDocCounts, LightRagPipelineStatus, LightRagStatus
from cm_shared.settings.app import get_settings

router = APIRouter(tags=["lightrag"])


@router.get("/lightrag/status", response_model=LightRagStatus)
async def get_lightrag_status(_user=require_admin) -> LightRagStatus:
    """Proxy LightRAG health, pipeline state, and document counts."""
    settings = get_settings()
    base = settings.lightrag_base_url.rstrip("/")
    headers = lightrag_headers()
    headers["Accept"] = "application/json"

    async with httpx.AsyncClient(timeout=10.0) as client:
        health_resp = await client.get(f"{base}/health", headers=headers)
        pipeline_resp = await client.get(f"{base}/documents/pipeline_status", headers=headers)
        counts_resp = await client.get(f"{base}/documents/status_counts", headers=headers)

    health = health_resp.json() if health_resp.is_success else {}
    pipeline_raw = pipeline_resp.json() if pipeline_resp.is_success else {}
    counts_raw = counts_resp.json().get("status_counts", {}) if counts_resp.is_success else {}

    cfg = health.get("configuration", {})

    return LightRagStatus(
        healthy=health.get("status") == "healthy",
        core_version=health.get("core_version", "unknown"),
        llm_model=cfg.get("llm_model", "unknown"),
        embedding_model=cfg.get("embedding_model", "unknown"),
        pipeline=LightRagPipelineStatus(
            busy=pipeline_raw.get("busy", False),
            job_name=pipeline_raw.get("job_name", "-"),
            docs=pipeline_raw.get("docs", 0),
            batchs=pipeline_raw.get("batchs", 0),
            cur_batch=pipeline_raw.get("cur_batch", 0),
            latest_message=pipeline_raw.get("latest_message", ""),
        ),
        doc_counts=LightRagDocCounts(
            pending=counts_raw.get("pending", 0),
            processing=counts_raw.get("processing", 0),
            preprocessed=counts_raw.get("preprocessed", 0),
            processed=counts_raw.get("processed", 0),
            failed=counts_raw.get("failed", 0),
            all=counts_raw.get("all", 0),
        ),
    )

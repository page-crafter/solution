from pydantic import BaseModel


class KpiCard(BaseModel):
    """Serialize one dashboard KPI card."""

    label: str
    value: str
    trend: str
    tone: str


class SpaceStat(BaseModel):
    """Per-space aggregated metrics for the dashboard spaces table."""

    space_key: str
    space_name: str
    page_count: int
    indexed_count: int
    coverage_pct: float
    open_drafts: int
    last_synced_at: str


class LightRagDocCounts(BaseModel):
    pending: int
    processing: int
    preprocessed: int
    processed: int
    failed: int
    all: int


class LightRagPipelineStatus(BaseModel):
    busy: bool
    job_name: str
    docs: int
    batchs: int
    cur_batch: int
    latest_message: str


class LightRagStatus(BaseModel):
    """Aggregated LightRAG health and pipeline state for the dashboard."""

    healthy: bool
    core_version: str
    llm_model: str
    embedding_model: str
    pipeline: LightRagPipelineStatus
    doc_counts: LightRagDocCounts

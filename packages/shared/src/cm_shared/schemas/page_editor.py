from datetime import datetime

from pydantic import BaseModel, Field

from cm_shared.schemas.common import OrmModel


class CreatePageEditRunRequest(BaseModel):
    """Request body for starting a documentation page editor."""

    page_id: int
    instruction: str = Field(..., max_length=2_000)


class UpdateDraftRequest(BaseModel):
    """Request body for saving manual Markdown draft corrections."""

    markdown_draft: str = Field(..., max_length=500_000)


class CreateProposalRequest(BaseModel):
    """Request body for asking the LLM to propose Markdown changes."""

    message: str = Field(..., max_length=2_000)
    base_proposal_id: str | None = Field(None, max_length=36)
    base_run_id: str | None = Field(None, max_length=36)
    base_markdown: str | None = Field(None, max_length=500_000)


class PageEditRunRead(OrmModel):
    """Serialize page edit state and generated artifacts for review."""

    id: str
    page_id: int
    instruction: str
    status: str
    draft_status: str
    preview_status: str
    source_version: int
    markdown_draft: str | None = None
    generated_storage_xhtml: str | None = None
    preview_html: str | None = None
    diff_text: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PageProposalRead(OrmModel):
    """Serialize one proposed Markdown update before application."""

    id: str
    page_id: int
    run_id: str | None = None
    instruction: str
    base_markdown: str
    base_source: str
    status: str
    proposed_markdown: str | None = None
    diff_text: str | None = None
    summary: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DraftVersionRead(OrmModel):
    """Serialize one validated Markdown draft version."""

    id: int
    run_id: str
    version_number: int
    markdown_draft: str
    change_source: str
    actor: str
    proposal_id: str | None = None
    restored_from_version_id: int | None = None
    created_at: datetime


class ApplyProposalResponse(BaseModel):
    """Serialize the applied proposal with the draft run it updated."""

    proposal: PageProposalRead
    run: PageEditRunRead

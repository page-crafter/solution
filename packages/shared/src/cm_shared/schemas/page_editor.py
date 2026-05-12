from datetime import datetime
from typing import Optional

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
    base_proposal_id: Optional[str] = Field(None, max_length=36)
    base_run_id: Optional[str] = Field(None, max_length=36)
    base_markdown: Optional[str] = Field(None, max_length=500_000)


class PageEditRunRead(OrmModel):
    """Serialize page edit state and generated artifacts for review."""

    id: str
    page_id: int
    instruction: str
    status: str
    draft_status: str
    preview_status: str
    source_version: int
    markdown_draft: Optional[str] = None
    generated_storage_xhtml: Optional[str] = None
    preview_html: Optional[str] = None
    diff_text: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PageProposalRead(OrmModel):
    """Serialize one proposed Markdown update before application."""

    id: str
    page_id: int
    run_id: Optional[str] = None
    instruction: str
    base_markdown: str
    base_source: str
    status: str
    proposed_markdown: Optional[str] = None
    diff_text: Optional[str] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
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
    proposal_id: Optional[str] = None
    restored_from_version_id: Optional[int] = None
    created_at: datetime


class ApplyProposalResponse(BaseModel):
    """Serialize the applied proposal with the draft run it updated."""

    proposal: PageProposalRead
    run: PageEditRunRead

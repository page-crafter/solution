from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

from cm_shared.schemas.common import OrmModel


class PageRead(OrmModel):
    """Serialize a synced Confluence page for tables and details."""

    id: int
    confluence_id: str
    space_key: str
    space_name: str | None = None
    parent_confluence_id: str | None = None
    sort_order: int = 0
    title: str
    status: str
    version_number: int
    web_url: str | None = None
    edit_url: str | None = None
    tiny_url: str | None = None
    is_placeholder: bool = False
    draft_state: str
    last_synced_at: datetime


class PageDetail(PageRead):
    """Serialize full page content used by the page editor workspace."""

    source_storage_xhtml: str
    source_markdown: str
    extracted_text: str


class MovePageRequest(BaseModel):
    """Describe a request to move a page relative to another Confluence page."""

    target_id: str | None = None
    target_parent_id: str | None = None
    position: Literal["append", "before", "after"] = "append"

    @field_validator("target_id", "target_parent_id")
    @classmethod
    def normalize_optional_id(cls, value: str | None) -> str | None:
        """Trim optional Confluence ids and convert blanks to None."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def require_target_id(self) -> "MovePageRequest":
        """Support the previous target_parent_id field while exposing target_id."""
        self.target_id = self.target_id or self.target_parent_id
        if self.target_id is None:
            raise ValueError("target_id is required")
        return self


class CreatePageRequest(BaseModel):
    """Describe an empty Confluence page to create for later processing."""

    title: str
    parent_id: str | None = None

    @field_validator("title")
    @classmethod
    def require_title(cls, value: str) -> str:
        """Reject blank page titles."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("title is required")
        return stripped

    @field_validator("parent_id")
    @classmethod
    def normalize_parent_id(cls, value: str | None) -> str | None:
        """Trim optional parent ids and convert blanks to None."""
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

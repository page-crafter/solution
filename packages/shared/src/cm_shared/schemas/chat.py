from typing import Any
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from cm_shared.schemas.common import OrmModel

ChatQueryMode = Literal["naive", "local", "global", "hybrid", "mix", "bypass"]


class CreateChatSessionRequest(BaseModel):
    """Request body for creating a documentation chat session."""

    title: str = "Documentation chat"


class ChatQuestionRequest(BaseModel):
    """Request body for asking a grounded documentation question."""

    message: str


class ChatQuerySettings(BaseModel):
    """User-adjustable query settings for chat requests."""

    mode: ChatQueryMode = "mix"
    user_prompt: str | None = None
    top_k: int = Field(default=40, ge=1)
    chunk_top_k: int = Field(default=20, ge=1)
    max_entity_tokens: int = Field(default=6000, ge=1)
    max_relation_tokens: int = Field(default=8000, ge=1)
    max_total_tokens: int = Field(default=30000, ge=1)
    enable_rerank: bool = True
    only_need_context: bool = False
    only_need_prompt: bool = False

    @model_validator(mode="after")
    def ensure_exclusive_output_modes(self) -> "ChatQuerySettings":
        """Only one of context-only and prompt-only may be enabled."""
        if self.only_need_context and self.only_need_prompt:
            raise ValueError("only_need_context and only_need_prompt cannot both be true")
        return self


class ChatStreamRequest(BaseModel):
    """Request body for a streamed chat answer."""

    message: str = Field(min_length=1)
    settings: ChatQuerySettings = Field(default_factory=ChatQuerySettings)


class ChatSessionRead(OrmModel):
    """Serialize a chat session identifier and title."""

    id: str
    title: str


class ChatMessageRead(OrmModel):
    """Serialize one persisted chat message."""

    id: int
    session_id: str
    role: str
    content: str
    citations_json: str


class ChatAnswer(BaseModel):
    """Serialize an assistant answer with source citations."""

    answer: str
    citations: list[dict[str, Any]]

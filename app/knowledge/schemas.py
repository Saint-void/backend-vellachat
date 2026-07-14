"""Schemas for knowledge documents."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KnowledgeTextCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=200_000)

    @field_validator("name", "content", mode="before")
    @classmethod
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class KnowledgeDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chatbot_id: UUID
    name: str
    source_type: str
    mime_type: str | None
    status: str
    error_message: str | None
    character_count: int
    chunk_count: int
    file_size: int
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkMatch(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    similarity: float

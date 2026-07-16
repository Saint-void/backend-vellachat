"""Request and response schemas for the chatbot module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatbotCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    business_name: str = Field(min_length=1, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    support_goal: str | None = Field(default=None, max_length=1000)
    website_domain: str | None = Field(default=None, max_length=255)
    tone: str = Field(default="friendly", min_length=1, max_length=50)
    greeting_message: str = Field(default="Hi! How can I help you today?", min_length=1, max_length=1000)
    brand_color: str = Field(default="#111111", min_length=4, max_length=20)
    logo_url: str | None = Field(default=None, max_length=2048)
    handoff_email: str | None = Field(default=None, max_length=255)

    @field_validator("*", mode="before")
    @classmethod
    def normalize_blank_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ChatbotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    business_name: str | None = Field(default=None, min_length=1, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    support_goal: str | None = Field(default=None, max_length=1000)
    website_domain: str | None = Field(default=None, max_length=255)
    tone: str | None = Field(default=None, min_length=1, max_length=50)
    greeting_message: str | None = Field(default=None, min_length=1, max_length=1000)
    brand_color: str | None = Field(default=None, min_length=4, max_length=20)
    logo_url: str | None = Field(default=None, max_length=2048)
    handoff_email: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("*", mode="before")
    @classmethod
    def normalize_blank_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class ChatbotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    business_name: str
    industry: str | None
    support_goal: str | None
    website_domain: str | None
    tone: str
    greeting_message: str
    brand_color: str
    logo_url: str | None
    handoff_email: str | None
    status: str
    created_at: datetime
    updated_at: datetime

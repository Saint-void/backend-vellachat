"""Schemas for the public chatbot widget."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WidgetConfigRead(BaseModel):
    chatbot_id: UUID
    name: str
    business_name: str
    industry: str | None
    support_goal: str | None
    greeting_message: str
    brand_color: str
    logo_url: str | None
    widget_settings: dict[str, Any]
    tone: str
    suggested_questions: list[str]


class WidgetConversationCreate(BaseModel):
    site_origin: str = Field(min_length=1, max_length=255)
    visitor_id: str | None = Field(default=None, max_length=255)


class WidgetMessageCreate(BaseModel):
    site_origin: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=4000)
    visitor_id: str | None = Field(default=None, max_length=255)


class WidgetMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class WidgetConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chatbot_id: UUID
    visitor_id: str | None
    site_origin: str
    status: str
    created_at: datetime
    updated_at: datetime
    messages: list[WidgetMessageRead]


class WidgetSendMessageRead(BaseModel):
    conversation_id: UUID
    assistant_message: WidgetMessageRead
    visitor_message: WidgetMessageRead

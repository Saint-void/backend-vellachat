"""Public widget API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.widget.widgetRepository import WidgetRepository
from app.widget.widgetSchemas import (
    WidgetConfigRead,
    WidgetConversationCreate,
    WidgetConversationRead,
    WidgetMessageCreate,
    WidgetSendMessageRead,
)
from app.widget.widgetService import WidgetService

router = APIRouter(prefix="/widget", tags=["widget"])


def get_widget_service(db: AsyncSession = Depends(get_db)) -> WidgetService:
    return WidgetService(WidgetRepository(db))


@router.get("/{chatbot_id}/config", response_model=WidgetConfigRead)
async def get_config(
    chatbot_id: UUID,
    site_origin: str,
    request: Request,
    service: WidgetService = Depends(get_widget_service),
):
    return await service.get_config(chatbot_id, site_origin, request)


@router.post("/{chatbot_id}/conversations", response_model=WidgetConversationRead)
async def create_conversation(
    chatbot_id: UUID,
    data: WidgetConversationCreate,
    request: Request,
    service: WidgetService = Depends(get_widget_service),
):
    return await service.create_conversation(chatbot_id, data, request)


@router.get("/{chatbot_id}/conversations/{conversation_id}", response_model=WidgetConversationRead)
async def read_conversation(
    chatbot_id: UUID,
    conversation_id: UUID,
    site_origin: str,
    visitor_id: str | None = None,
    service: WidgetService = Depends(get_widget_service),
):
    return await service.read_conversation(chatbot_id, conversation_id, site_origin, visitor_id)


@router.post("/{chatbot_id}/conversations/{conversation_id}/messages", response_model=WidgetSendMessageRead)
async def send_message(
    chatbot_id: UUID,
    conversation_id: UUID,
    data: WidgetMessageCreate,
    service: WidgetService = Depends(get_widget_service),
):
    return await service.send_message(chatbot_id, conversation_id, data)


@router.post("/{chatbot_id}/conversations/{conversation_id}/close", response_model=WidgetConversationRead)
async def close_conversation(
    chatbot_id: UUID,
    conversation_id: UUID,
    site_origin: str,
    visitor_id: str | None = None,
    service: WidgetService = Depends(get_widget_service),
):
    """Explicitly close a conversation from the client side."""
    return await service.close_conversation(chatbot_id, conversation_id, site_origin, visitor_id)

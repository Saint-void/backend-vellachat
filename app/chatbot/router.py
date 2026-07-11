"""Chatbot setup and manual FAQ endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db
from app.chatbot.repository import ChatbotRepository
from app.chatbot.schemas import (
    ChatbotCreate,
    ChatbotFAQCreate,
    ChatbotFAQRead,
    ChatbotFAQUpdate,
    ChatbotRead,
    ChatbotUpdate,
)
from app.chatbot.service import ChatbotService

router = APIRouter(prefix="/chatbots", tags=["chatbots"])


def get_chatbot_service(db: AsyncSession = Depends(get_db)) -> ChatbotService:
    return ChatbotService(ChatbotRepository(db))


@router.post("", response_model=ChatbotRead, status_code=status.HTTP_201_CREATED)
async def create_chatbot(
    data: ChatbotCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.create_chatbot(current_user.id, data)


@router.get("", response_model=list[ChatbotRead])
async def list_chatbots(
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.list_chatbots(current_user.id)


@router.get("/{chatbot_id}", response_model=ChatbotRead)
async def read_chatbot(
    chatbot_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.get_chatbot(chatbot_id, current_user.id)


@router.patch("/{chatbot_id}", response_model=ChatbotRead)
async def update_chatbot(
    chatbot_id: UUID,
    data: ChatbotUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.update_chatbot(chatbot_id, current_user.id, data)


@router.delete("/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot(
    chatbot_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    await service.delete_chatbot(chatbot_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{chatbot_id}/faqs", response_model=ChatbotFAQRead, status_code=status.HTTP_201_CREATED)
async def create_faq(
    chatbot_id: UUID,
    data: ChatbotFAQCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.create_faq(chatbot_id, current_user.id, data)


@router.get("/{chatbot_id}/faqs", response_model=list[ChatbotFAQRead])
async def list_faqs(
    chatbot_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.list_faqs(chatbot_id, current_user.id)


@router.patch("/{chatbot_id}/faqs/{faq_id}", response_model=ChatbotFAQRead)
async def update_faq(
    chatbot_id: UUID,
    faq_id: UUID,
    data: ChatbotFAQUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.update_faq(chatbot_id, faq_id, current_user.id, data)


@router.delete("/{chatbot_id}/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq(
    chatbot_id: UUID,
    faq_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    await service.delete_faq(chatbot_id, faq_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

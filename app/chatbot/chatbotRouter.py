"""Chatbot setup and manual FAQ endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db
from app.chatbot.chatbotLogoStorage import ChatbotLogoStorage
from app.chatbot.chatbotRepository import ChatbotRepository
from app.chatbot.chatbotSchemas import (
    ChatbotCreate,
    ChatbotRead,
    ChatbotUpdate,
)
from app.chatbot.chatbotService import ChatbotService
from app.core.coreConfig import settings
from app.core.coreExceptions import NotFoundError

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


@router.post("/{chatbot_id}/logo", response_model=ChatbotRead)
async def upload_chatbot_logo(
    chatbot_id: UUID,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.upload_logo(chatbot_id, current_user.id, file)


@router.delete("/{chatbot_id}/logo", response_model=ChatbotRead)
async def delete_chatbot_logo(
    chatbot_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: ChatbotService = Depends(get_chatbot_service),
):
    return await service.delete_logo(chatbot_id, current_user.id)


@router.get("/{chatbot_id}/logo")
async def get_chatbot_logo(chatbot_id: UUID):
    """Serve the logo image for a chatbot (public endpoint, no auth required)."""
    storage = ChatbotLogoStorage(settings.CHATBOT_LOGO_STORAGE_DIR, settings.CHATBOT_LOGO_MAX_UPLOAD_BYTES)
    logo_path = await storage.resolve(chatbot_id)

    if not logo_path:
        raise NotFoundError("Logo not found")

    content = await storage.read(str(logo_path))

    # Determine MIME type from file extension
    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
    }
    ext = logo_path.suffix.lstrip(".").lower()
    media_type = mime_types.get(ext, "application/octet-stream")

    return Response(content=content, media_type=media_type)

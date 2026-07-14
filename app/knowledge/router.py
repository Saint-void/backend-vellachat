"""Knowledge document endpoints."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.schemas import KnowledgeDocumentRead, KnowledgeTextCreate
from app.knowledge.service import KnowledgeService
from app.knowledge.tasks import process_knowledge_document

router = APIRouter(prefix="/chatbots/{chatbot_id}/knowledge", tags=["knowledge"])


def get_knowledge_service(db: AsyncSession = Depends(get_db)) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(db))


@router.get("/documents", response_model=list[KnowledgeDocumentRead])
async def list_documents(
    chatbot_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    return await service.list_documents(chatbot_id, current_user.id)


@router.post("/documents/text", response_model=KnowledgeDocumentRead, status_code=status.HTTP_201_CREATED)
async def create_text_document(
    chatbot_id: UUID,
    data: KnowledgeTextCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    document = await service.create_text_document(chatbot_id, current_user.id, data)
    background_tasks.add_task(process_knowledge_document, document.id)
    return document


@router.post("/documents/upload", response_model=KnowledgeDocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    chatbot_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    document = await service.create_upload_document(chatbot_id, current_user.id, file)
    background_tasks.add_task(process_knowledge_document, document.id)
    return document


# router.py — one-line change
@router.post("/documents/{document_id}/reprocess", response_model=KnowledgeDocumentRead)
async def reprocess_document(
    chatbot_id: UUID,
    document_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    document = await service.reprocess_document(chatbot_id, document_id, current_user.id)
    background_tasks.add_task(process_knowledge_document, document.id)
    return document


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    chatbot_id: UUID,
    document_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
):
    await service.delete_document(chatbot_id, document_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

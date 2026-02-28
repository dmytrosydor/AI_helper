from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.crud import chat as crud_chat
from app.crud import project as crud_project
from app.models.user import User
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services.chat_service import chat_service

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def ask_question(
    project_id: int,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = await crud_project.get_by_id_and_owner(
        db, owner_id=current_user.id, project_id=project_id
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return StreamingResponse(
        chat_service.stream_chat(db, project_id, current_user.id, request.query),
        media_type="text/event-stream",
    )


@router.get("/history", response_model=list[ChatHistoryResponse])
async def get_project_history(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 100,
    skip: int = 0,
):
    project = await crud_project.get_by_id_and_owner(
        db,
        owner_id=current_user.id,
        project_id=project_id,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return await crud_chat.get_chat_history(db, project_id, limit, skip)

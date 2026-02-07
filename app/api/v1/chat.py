from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse
from app.services.chat_service import chat_service
from app.crud import project as crud_project
from app.crud import chat as crud_chat

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["Chat"])

@router.post("/", response_model=ChatResponse)
def ask_question(
    project_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Перевіряємо, чи існує проєкт і чи має юзер до нього доступ
    project = crud_project.get_by_id_and_owner(db, owner_id=current_user.id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 2. Запускаємо логіку чату
    result = chat_service.chat(db, project_id, request.query)

    crud_chat.createChatHistory(
        db=db,
        project_id=project_id,
        user_id=current_user.id,
        question=request.query,
        answer=result["answer"]
    )
    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
    )


@router.get("/history",response_model=list[ChatHistoryResponse])
def get_project_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 100,
    skip: int = 0,
):
    project = crud_project.get_by_id_and_owner(
        db,
        owner_id=current_user.id,
        project_id=project_id,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return crud_chat.get_chat_history(db,project_id,limit,skip)
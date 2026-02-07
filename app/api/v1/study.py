from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import project as crud_project
from app.services.study_service import study_service
from app.schemas.study import StudyContentResponse, ExamResponse, UserQuestionsRequest, StudyRequest

router = APIRouter(prefix="/projects/{project_id}/study", tags=["Study Tools"])

# --- Helper function to avoid code duplication ---
def check_project(db: Session, user_id: int, project_id: int):
    project = crud_project.get_by_id_and_owner(db, owner_id=user_id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/summary", response_model=StudyContentResponse)
def get_summary(
        project_id: int,
        request: StudyRequest, # 👈 Додано request body
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    check_project(db, current_user.id, project_id)

    # 👇 Передаємо document_ids в сервіс
    content = study_service.get_summary(db, project_id, request.document_ids)
    return StudyContentResponse(content=content)


@router.post("/keypoints", response_model=StudyContentResponse)
def get_keypoints(
        project_id: int,
        request: StudyRequest, # 👈 Додано
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    check_project(db, current_user.id, project_id)

    # 👇 Передаємо document_ids
    content = study_service.get_keypoints(db, project_id, request.document_ids)
    return StudyContentResponse(content=content)

@router.post("/exam", response_model=ExamResponse)
def get_exam_questions(
        project_id: int,
        request: StudyRequest, # 👈 Додано
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    check_project(db, current_user.id, project_id)

    # 👇 Передаємо document_ids
    return study_service.get_exam_questions(db, project_id, request.document_ids)


@router.post("/answer_questions", response_model=StudyContentResponse)
def answer_questions(
        project_id: int,
        request: UserQuestionsRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    check_project(db, current_user.id, project_id)

    # 👇 Тепер передаємо document_ids і сюди (вони є в UserQuestionsRequest)
    content = study_service.answer_user_questions(
        db,
        project_id=project_id,
        questions=request.questions,
        document_ids=request.document_ids
    )
    return StudyContentResponse(content=content)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.crud import project as crud_project
from app.services.study_service import study_service
from app.schemas.study import StudyContentResponse, ExamResponse, UserQuestionsRequest


router = APIRouter(prefix="/projects/{project_id}/study", tags=["Study Tools"])


@router.post("/summary", response_model=StudyContentResponse)
def get_summary(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = crud_project.get_by_id_and_owner(db, owner_id=current_user.id, project_id=project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = study_service.generate_summary(db, project_id)
    return StudyContentResponse(content=content)


@router.post("/keypoints", response_model=StudyContentResponse)
def get_keypoints(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
   project = crud_project.get_by_id_and_owner(db, owner_id=current_user.id, project_id=project_id)
   if not project:
       raise HTTPException(status_code=404, detail="Project not found")
   content = study_service.generate_keypoints(db, project_id)
   return StudyContentResponse(content=content)
@router.post("/exam", response_model=ExamResponse)
def get_exam_questions(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = crud_project.get_by_id_and_owner(db, owner_id=current_user.id, project_id=project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return study_service.generate_exam_questions(db,project_id=project_id)


@router.post("/answer_questions",response_model = StudyContentResponse)
def answer_questions(
        project_id: int,
        request: UserQuestionsRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = crud_project.get_by_id_and_owner(db, owner_id=current_user.id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    content = study_service.answer_user_questions(db,project_id=project_id,questions=request.questions)
    return StudyContentResponse(content=content)


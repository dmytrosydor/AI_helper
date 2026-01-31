from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.deps import get_current_user
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.models.user import User

from app.crud import project as crud_project

router = APIRouter(prefix="/projects", tags=["Projects"])


# CREATE
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
        project_in: ProjectCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return crud_project.create(db=db, obj_in=project_in, owner_id=current_user.id)


# READ LIST

@router.get("/", response_model=list[ProjectResponse])
def read_projects(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return crud_project.get_multi_by_owner(db=db, owner_id=current_user.id, skip=skip, limit=limit)


# READ ONE

@router.get("/{project_id}", response_model=ProjectResponse)
def read_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = crud_project.get_by_id_and_owner(
        db=db,
        owner_id=current_user.id,
        project_id=project_id,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# UPDATE

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
        project_id: int,
        project_update: ProjectUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = crud_project.get_by_id_and_owner(
        db=db,
        owner_id=current_user.id,
        project_id=project_id,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project = crud_project.update(
        db=db,
        db_obj=project,
        obj_in=project_update,
    )
    return project


# DELETE

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
        project_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = crud_project.get_by_id_and_owner(
        db=db,
        owner_id=current_user.id,
        project_id=project_id,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    crud_project.delete(db=db, db_obj=project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
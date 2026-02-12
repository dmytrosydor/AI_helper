from fastapi import APIRouter, Depends, HTTPException, status, Response

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from app.api.deps import get_current_user
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.models.user import User

from app.crud import project as crud_project

router = APIRouter(prefix="/projects", tags=["Projects"])


# CREATE
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
        project_in: ProjectCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return await crud_project.create(db=db, obj_in=project_in, owner_id=current_user.id)


# READ LIST

@router.get("/", response_model=list[ProjectResponse])
async def read_projects(
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    return await crud_project.get_multi_by_owner(db=db, owner_id=current_user.id, skip=skip, limit=limit)


# READ ONE

@router.get("/{project_id}", response_model=ProjectResponse)
async def read_project(
        project_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = await crud_project.get_by_id_and_owner(
        db=db,
        owner_id=current_user.id,
        project_id=project_id,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# UPDATE

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
        project_id: int,
        project_update: ProjectUpdate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = await crud_project.get_by_id_and_owner(
        db=db,
        owner_id=current_user.id,
        project_id=project_id,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project = await crud_project.update(
        db=db,
        db_obj=project,
        obj_in=project_update,
    )
    return project


# DELETE

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
        project_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = await crud_project.get_by_id_and_owner(
        db=db,
        owner_id=current_user.id,
        project_id=project_id,
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await crud_project.delete(db=db, db_obj=project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
from typing import Any

from sqlalchemy.orm import Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Result
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create(
        db: AsyncSession,
        obj_in: ProjectCreate,
        owner_id: int
) -> Project:
    db_obj = Project(
        name=obj_in.name,
        description=obj_in.description,
        owner_id=owner_id,
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_multi_by_owner(
        db: AsyncSession,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
) -> list[Project]:
    stmt = select(Project).filter(Project.owner_id == owner_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_by_id_and_owner(
        db: AsyncSession,
        owner_id: int,
        project_id: int,
) -> type[Project] | None:
    stmt = select(Project).filter(Project.id == project_id, Project.owner_id == owner_id)
    result = await db.execute(stmt)
    return result.scalars().first()

async def update(
        db: AsyncSession,
        db_obj: Project,
        obj_in: ProjectUpdate,
) -> Project:
    """

    :rtype: Project
    """
    update_data = obj_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(
        db: AsyncSession,
        db_obj: Project
):
    await db.delete(db_obj)
    await db.commit()
    return db_obj

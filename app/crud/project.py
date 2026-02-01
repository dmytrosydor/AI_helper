from sqlalchemy.orm import Session, Query
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def create(
        db: Session,
        obj_in: ProjectCreate,
        owner_id: int
) -> Project:
    db_obj = Project(
        name=obj_in.name,
        description=obj_in.description,
        owner_id=owner_id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_multi_by_owner(
        db: Session,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
) -> Query[type[Project]]:
    return (
        db.query(Project)
        .filter(Project.owner_id == owner_id)
        .offset(skip)
        .limit(limit)
    )


def get_by_id_and_owner(
        db: Session,
        owner_id: int,
        project_id: int,
) -> type[Project] | None:
    return (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == owner_id)
        .first()
    )


def update(
        db: Session,
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
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete(
        db: Session,
        db_obj: Project
):
    db.delete(db_obj)
    db.commit()
    return db_obj

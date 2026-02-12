from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.schemas.document import DocumentCreate


async def create(
        db: AsyncSession,
        obj_in: DocumentCreate,
        file_path: str,
        project_id: int
) -> Document:
    db_obj = Document(
        filename=obj_in.filename,
        file_path=file_path,
        project_id=project_id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    return db_obj


async def get_by_id_and_project_id(
        db: AsyncSession,
        project_id: int,
        document_id: int
) -> type[Document]:
    stmt = select(Document).filter(Document.id == document_id, Document.project_id == project_id)
    result = await db.execute(stmt)
    return result.scalars().first()



async def get_multiple_documents_by_project_id(
        db: AsyncSession,
        project_id: int,
        skip: int = 0,
        limit: int = 100
)-> list[type[Document]]:
    stmt = select(Document).filter(Document.project_id == project_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def delete(
        db: AsyncSession,
        db_obj: Document
) -> Document:
    await db.delete(db_obj)
    await db.commit()
    return db_obj
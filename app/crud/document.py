from sqlalchemy.orm import Session, Query
from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate


def create(
        db: Session,
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
    db.commit()
    db.refresh(db_obj)

    return db_obj


def get_by_id_and_project_id(
        db: Session,
        project_id: int,
        document_id: int
) -> type[Document]:
    return (
        db.query(Document)
        .filter(
            Document.project_id == project_id, Document.id == document_id
        ).first()
    )

def get_multiple_documents_by_project_id(
        db: Session,
        project_id: int,
        skip: int = 0,
        limit: int = 100
)-> list[type[Document]]:
    return (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def delete(
        db: Session,
        db_obj: Document
) -> Document:
    db.delete(db_obj)
    db.commit()
    return db_obj
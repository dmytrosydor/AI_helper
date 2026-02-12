from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.db import get_db
from app.api.deps import get_current_user
from app.schemas.document import DocumentResponse, DocumentCreate
from app.models.user import User
from app.models.document import Document
from app.crud import document as crud_document
from app.crud import project as crud_project
from app.services.rag_service import rag_service
from app.utils.file_storage import save_upload_file, delete_file

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["Documents"])

# UPLOAD

@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
        background_tasks: BackgroundTasks,
        project_id: int,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = await crud_project.get_by_id_and_owner(
        db=db,
        project_id=project_id,
        owner_id=current_user.id
    )

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_NOT_FOUND, detail="Filename is missing")


    stmt = select(Document).where(
        Document.project_id == project_id,
        Document.filename == file.filename)
    result = await db.execute(stmt)
    existing_document = result.scalars().first()

    if existing_document:
        # 409 Conflict - стандартний код для дублікатів
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File '{file.filename}' already exists. Please delete it first."
        )
    try:
        file_path = save_upload_file(file)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    doc_in = DocumentCreate(filename=file.filename)

    document = await crud_document.create(
        db=db,
        obj_in=doc_in,
        file_path=file_path,
        project_id=project_id,
    )
    background_tasks.add_task(rag_service.process_document, document.id)
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
        project_id: int,
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = await crud_project.get_by_id_and_owner(db, owner_id=current_user.id, project_id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    document = await crud_document.get_by_id_and_project_id(db, project_id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return document
@router.get("/", response_model=list[DocumentResponse])
async def read_documents(
        project_id:int,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):

    project = await crud_project.get_by_id_and_owner(
        db=db,
        project_id=project_id,
        owner_id=current_user.id
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return await crud_document.get_multiple_documents_by_project_id(
        db=db,
        project_id=project_id,
    )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
        project_id: int,
        document_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    project = await crud_project.get_by_id_and_owner(
        db=db,
        project_id=project_id,
        owner_id=current_user.id
    )

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    document = await crud_document.get_by_id_and_project_id(
        db=db,
        project_id=project_id,
        document_id=document_id
    )
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    delete_file(document.file_path)

    await crud_document.delete(
        db=db,
        db_obj=document
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


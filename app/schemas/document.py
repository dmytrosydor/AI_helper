from datetime import datetime

from pydantic import BaseModel

class DocumentBase(BaseModel):
    filename: str

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    filename: str | None = None

class DocumentResponse(DocumentBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True
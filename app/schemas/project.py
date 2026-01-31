from pydantic import BaseModel
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: str | None = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True
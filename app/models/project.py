from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.db import Base
from app.models import ProjectAnalysisItem

if TYPE_CHECKING:
    from .analysis import ProjectAnalysis, ProjectAnalysisItem
    from .document import Document
    from .user import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(String(255), nullable=True)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    analysis: Mapped["ProjectAnalysis"] = relationship(
        "ProjectAnalysis",
        back_populates="project",
        uselist=False,  # Це зв'язок One-to-One
        cascade="all, delete-orphan",
    )

    analysis_items: Mapped[list["ProjectAnalysisItem"]] = relationship(
        "ProjectAnalysisItem", back_populates="project", cascade="all, delete-orphan"
    )


def __repr__(self: object) -> str:
    return f"<Project id={self.id} name={self.name}>"

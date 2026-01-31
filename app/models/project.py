from sqlalchemy import String, Boolean, Column, DateTime, ForeignKey, nulls_last
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime

from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(String(255), nullable=True)

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Project id={self.id} name={self.name}>"

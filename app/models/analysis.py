from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ProjectAnalysis(Base):
    __tablename__ = "project_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_questions: Mapped[str | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project", back_populates="analysis")


class ProjectAnalysisItem(Base):
    __tablename__ = "project_analysis_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))

    documents_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    exam_questions: Mapped[str | None] = mapped_column(JSONB, nullable=True)

    project = relationship("Project")

from sqlalchemy import String, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from pgvector.sqlalchemy import Vector

from app.core.db import Base
from app.models.project import Project


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(primary_key=True)

    filename: Mapped[str] = mapped_column(String(255))

    file_path: Mapped[str] = mapped_column(String(255))

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    processing_status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="documents")

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all,  delete-orphan"
    )

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}')>"


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)

    chunk_index: Mapped[int] = mapped_column(Integer)

    document_id: Mapped[int] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"))

    chunk_text: Mapped[str] = mapped_column(Text)

    embedding: Mapped[list[float]] = mapped_column(Vector(768))  # розмірність чанку

    document: Mapped["Document"] = relationship(back_populates="chunks")

    def __repr__(self):
        return f"<Chunk(id={self.id}, doc_id={self.document_id}, index={self.chunk_index})>"

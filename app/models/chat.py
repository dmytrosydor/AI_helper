from datetime import datetime
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


from app.core.db import Base

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    project = relationship("Project")
    user = relationship("User")

    def __repr__(self):
        return f"<Chat History id: {self.id}, question: {self.question}, answer: {self.answer}, created_at: {self.created_at}>"
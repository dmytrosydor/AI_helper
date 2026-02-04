from sqlalchemy.orm import Session
from app.models import ChatHistory


def createChatHistory(
        db: Session,
        project_id: int,
        user_id: int,
        question: str,
        answer: str,
)-> ChatHistory:
    db_obj = ChatHistory(
        project_id=project_id,
        user_id=user_id,
        question=question,
        answer=answer
    )

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_chat_history(
        db: Session,
        project_id: int,
        limit: int,
        skip: int
) -> list[type[ChatHistory]]:
    return(
        db.query(ChatHistory)
        .filter(ChatHistory.project_id == project_id)
        .order_by(ChatHistory.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
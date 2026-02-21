from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ChatHistory


async def createChatHistory(
        db: AsyncSession,
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
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_chat_history(
        db: AsyncSession,
        project_id: int,
        limit: int,
        skip: int
) -> list[type[ChatHistory]]:
    stmt =(
        select(ChatHistory)
        .filter(ChatHistory.project_id == project_id)
        .order_by(ChatHistory.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
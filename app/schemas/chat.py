from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []


class ChatHistoryResponse(BaseModel):
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attribute = True
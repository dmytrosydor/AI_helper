import json

from sqlalchemy.orm import Session
from sqlalchemy import select
from google import genai
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.chat import  ChatHistory
from app.crud.chat import get_chat_history
from app.models.document import DocumentChunk, Document
from app.services.rag_service import rag_service
from app.core.prompts import ChatPrompts
from app.crud.chat import createChatHistory
from langsmith import traceable

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class ChatService:
    @traceable(name="rewrite_question")
    def _reformat_question(self,db:Session, question:str,project_id: int ):
        last_messages = (
            db.query(ChatHistory)
            .filter(ChatHistory.project_id == project_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(3)
            .all()
        )
        if not last_messages:
            return question

        history_str = ""

        for item in (reversed(last_messages)):
            history_str += f"User: {item.question}\nAI: {item.answer}\n"

        prompt = ChatPrompts.REFORMAT_USER_QUESTION.format(
            history=history_str,
            question=question
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt
            )

            return response.text.strip()
        except Exception as e:
            print(f"Gemini Error: {e}")
            return question


    @traceable(name="chat_pipeline")
    def stream_chat(self, db: Session, project_id: int,user_id:int, query_text: str):
        query_reformat = self._reformat_question(db, query_text, project_id)
        query_vector = rag_service.get_embedding(query_reformat)

        if not query_vector:
            yield f'data: {json.dumps({"error":"Error creating embedding"})}\n\n'
            return

        # 2. Пошук схожих шматків у базі
        stmt = (
            select(DocumentChunk)
            .join(Document)
            .filter(Document.project_id == project_id)
            .order_by(DocumentChunk.embedding.l2_distance(query_vector))
            .limit(5)
        )
        chunks = db.scalars(stmt).all()

        chunks = db.scalars(stmt).all()

        context_text = ""
        sources = []

        if chunks:
            context_text = "\n\n".join([chunk.chunk_text for chunk in chunks])
            sources = list(set([chunk.document.filename for chunk in chunks]))


        yield f'data: {json.dumps({"type": "sources", "data": sources})}\n\n'


        if not chunks:
            yield f'data: {json.dumps({"type": "answer", "data": "Я не знайшов інформації в документах."})}\n\n'
            return

        prompt = ChatPrompts.MAIN_CHAT.format(
            context=context_text,
            query=query_reformat
        )

        try:
            response_stream = client.models._generate_content_stream(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )

            full_answer = ""

            for chunk in response_stream:
                if chunk.text:
                    yield f'data: {json.dumps({"type": "answer", "data": chunk.text})}\n\n'
                    full_answer += chunk.text

            createChatHistory(
                db=db,
                project_id=project_id,
                user_id=user_id,
                question=query_text,  # Зберігаємо оригінальне питання
                answer=full_answer
            )
        except Exception as e:
            print(f"Stream Error: {e}")
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

chat_service = ChatService()

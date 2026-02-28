import json

from google import genai
from langsmith import traceable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from app.core.config import settings
from app.core.prompts import ChatPrompts
from app.crud.chat import create_chat_history
from app.models.chat import ChatHistory
from app.models.document import Document, DocumentChunk
from app.services.rag_service import rag_service

client = genai.Client(api_key=settings.GEMINI_API_KEY)


class ChatService:
    @traceable(name="rewrite_question")
    async def _reformat_question(self, db: AsyncSession, question: str, project_id: int):
        stmt = (
            select(ChatHistory)
            .filter(ChatHistory.project_id == project_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(3)
        )
        result = await db.execute(stmt)
        last_messages = result.scalars().all()
        if not last_messages:
            return question

        history_str = ""

        for item in reversed(last_messages):
            history_str += f"User: {item.question}\nAI: {item.answer}\n"

        prompt = ChatPrompts.REFORMAT_USER_QUESTION.format(history=history_str, question=question)

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite", contents=prompt
            )

            return response.text.strip()
        except Exception as e:
            print(f"Gemini Error: {e}")
            return question

    def _rrf_merge(self, vector_results, keyword_results, k=60):
        scores = {}

        for rank, item in enumerate(vector_results):
            if item.id not in scores:
                scores[item.id] = {"item": item, "score": 0}
            scores[item.id]["score"] += 1 / (k + rank + 1)

        sorted_items = sorted(scores.values(), key=lambda x: x["score"], reverse=True)

        return [entry["item"] for entry in sorted_items]

    @traceable(name="chat_pipeline")
    async def stream_chat(self, db: AsyncSession, project_id: int, user_id: int, query_text: str):
        query_reformat = await self._reformat_question(db, query_text, project_id)
        query_vector = rag_service.get_embedding(query_reformat)

        if not query_vector:
            yield f"data: {json.dumps({'error': 'Error creating embedding'})}\n\n"
            return

        # 2. Пошук схожих шматків у базі
        vector_stmt = (
            select(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .join(Document)
            .filter(Document.project_id == project_id)
            .order_by(DocumentChunk.embedding.l2_distance(query_vector))
            .limit(5)
        )

        vector_result = await db.execute(vector_stmt)
        vector_chunks = vector_result.scalars().all()

        keyword_stmt = (
            select(DocumentChunk)
            .options(joinedload(DocumentChunk.document))
            .join(Document)
            .filter(Document.project_id == project_id)
            .filter(
                DocumentChunk.content_tsvector.op("@@")(
                    func.websearch_to_tsquery("simple", query_reformat)
                )
            )
            .limit(10)
        )

        result = await db.execute(keyword_stmt)
        keyword_chunks = result.scalars().all()

        final_chunks = self._rrf_merge(vector_chunks, keyword_chunks)

        final_chunks = final_chunks[:7]
        context_text = ""
        sources = []

        if final_chunks:
            context_text = "\n\n".join([chunk.chunk_text for chunk in final_chunks])
            sources = list(set([chunk.document.filename for chunk in final_chunks]))

        yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"

        if not final_chunks:
            yield f"data: {json.dumps({'type': 'answer', 'data': 'Я не знайшов інформації в документах.'})}\n\n"
            return

        prompt = ChatPrompts.MAIN_CHAT.format(context=context_text, query=query_reformat)

        try:
            response_stream = client.models.generate_content_stream(
                model=settings.GEMINI_MODEL, contents=prompt
            )

            full_answer = ""

            for chunk in response_stream:
                if chunk.text:
                    yield f"data: {json.dumps({'type': 'answer', 'data': chunk.text})}\n\n"
                    full_answer += chunk.text

            await create_chat_history(
                db=db,
                project_id=project_id,
                user_id=user_id,
                question=query_text,
                answer=full_answer,
            )
        except Exception as e:
            print(f"Stream Error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"


chat_service = ChatService()

from sqlalchemy.orm import Session
from sqlalchemy import select
from google import genai
from app.core.config import settings
from app.models.document import DocumentChunk, Document
from app.services.rag_service import rag_service, client

client = genai.Client(api_key=settings.GEMINI_API_KEY)


class ChatService:
    def chat(self,
             db: Session,
             project_id: int,
             query_text: str,
             ) -> str:
        query_vector = rag_service.get_embedding(query_text)
        if not query_vector:
            return "Sorry, I couldn't find anything."

        stmt = (
            select(DocumentChunk)
            .join(Document)
            .filter(Document.project_id == project_id)
            .order_by(DocumentChunk.embedding.l2_distance(query_vector))
            .limit(5)
        )

        chunks = db.scalars(stmt).all()

        if not chunks:
            return "Sorry, I couldn't find anything."

        context_text = "\n\n".join([chunk.chunk_text for chunk in chunks])

        prompt = f"""
                Ти - розумний асистент. Твоє завдання - відповідати на питання користувача,
                використовуючи ТІЛЬКИ наданий нижче контекст.
                Якщо в контексті немає відповіді, так і скажи: "Я не знаю відповіді на основі наданих документів".
                Не вигадуй нічого від себе.

                КОНТЕКСТ:
                {context_text}

                ПИТАННЯ КОРИСТУВАЧА:
                {query_text}
                """

        try:
            sources = list(set([chunk.document.filename for chunk in chunks]))
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            return {
                "answer": response.text,
                "sources": sources
            }
        except Exception as e:
            print(f"Geminin Geeration Error: {e}")
            return "Sorry, I generatio error."


chat_service = ChatService()

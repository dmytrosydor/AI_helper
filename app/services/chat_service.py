from sqlalchemy.orm import Session
from sqlalchemy import select
from google import genai
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.document import DocumentChunk, Document
from app.services.rag_service import rag_service
from app.core.prompts import ChatPrompts

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class ChatService:
    def chat(self, db: Session, project_id: int, query_text: str) -> dict:
        # 1. Перетворюємо питання на вектор
        query_vector = rag_service.get_embedding(query_text)

        # Якщо вектор пустий (наприклад, помилка API ключа при ембеддінгу)
        if not query_vector:
            return {
                "answer": "Помилка: Не вдалося обробити запит. Перевірте ваш GEMINI_API_KEY.",
                "sources": []
            }

        # 2. Пошук схожих шматків у базі
        stmt = (
            select(DocumentChunk)
            .join(Document)
            .filter(Document.project_id == project_id)
            .order_by(DocumentChunk.embedding.l2_distance(query_vector))
            .limit(10)
        )
        chunks = db.scalars(stmt).all()

        if not chunks:
            return {
                "answer": "Я не знайшов жодної інформації у ваших документах, яка б відповідала на це питання.",
                "sources": []
            }

        # 3. Формуємо контекст
        context_text = "\n\n".join([chunk.chunk_text for chunk in chunks])

        # Збираємо джерела (назви файлів)
        sources = []
        try:
            # Спробуємо отримати унікальні імена файлів
            sources = list(set([chunk.document.filename for chunk in chunks]))
        except Exception:
            pass

        prompt = ChatPrompts.MAIN_CHAT.format(
            context=context_text,
            query=query_text
        )

        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt
            )
            return {
                "answer": response.text,
                "sources": sources
            }
        except Exception as e:
            print(f"Gemini Error: {e}")
            # ВАЖЛИВО: Повертаємо словник навіть при помилці
            return {
                "answer": f"Виникла помилка при генерації відповіді: {str(e)}",
                "sources": []
            }

chat_service = ChatService()

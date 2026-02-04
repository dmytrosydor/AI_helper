from google import genai
from google.genai import types # <--- Додано імпорт types
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.document import Document, DocumentChunk
from app.services.pdf_service import pdf_service

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class RagService:
    def get_embedding(self, text: str) -> list[float]:
        try:
            # Використовуємо text-embedding-004
            result = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            print("Result:", result)
            # В SDK genai це зазвичай атрибут values, а не функція values()
            return result.embeddings[0].values
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return []

    def process_document(self, document_id: int): # <--- Приймаємо тільки ID
        # Відкриваємо власну сесію
        with SessionLocal() as db:
            print(f"--- 🚀 Start processing document ID {document_id} ---")

            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                print("❌ Document not found in DB")
                return

            try:
                full_text = pdf_service.extract_text(document.file_path)
            except Exception as e:
                print(f"❌ Error reading PDF: {e}")
                return

            if not full_text:
                print(f"⚠️ Document {document.id} has no text")
                return

            chunk_size = 1000
            overlap = 100
            chunks = []

            for i in range(0, len(full_text), chunk_size - overlap):
                chunk = full_text[i : i + chunk_size]
                # ВИПРАВЛЕНО: зберігаємо, якщо текст БІЛЬШИЙ за 50 символів
                if len(chunk) > 50:
                    chunks.append(chunk)

            print(f"✂️ Created {len(chunks)} chunks. Vectorizing...")

            new_chunks = []
            for idx, chunk_text in enumerate(chunks):
                vector = self.get_embedding(chunk_text)

                if vector:
                    db_chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=idx,
                        chunk_text=chunk_text,
                        embedding=vector,
                    )
                    new_chunks.append(db_chunk)

            if new_chunks:
                db.add_all(new_chunks)
                db.commit()
                print(f"✅ Successfully saved {len(new_chunks)} chunks")
            else:
                print(f"⚠️ No chunks were created/saved")

rag_service = RagService()

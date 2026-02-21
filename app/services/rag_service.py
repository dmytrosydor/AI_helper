from google import genai
from google.genai import types
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from sqlalchemy import select
from app.models.document import Document, DocumentChunk
from app.services.pdf_service import pdf_service

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class RagService:
    def get_embedding(self, text: str) -> list[float]:
        try:
            # Використовуємо text-embedding
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            print("Result:", result)

            return result.embeddings[0].values
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return []

    async def process_document(self, document_id: int):

        async with AsyncSessionLocal() as db:
            print(f"---Start processing document ID {document_id} ---")

            stmt = (
                select(Document)
                .filter(Document.id == document_id)
            )
            result = await db.execute(stmt)
            document = result.scalars().first()

            if not document:
                print("Document not found in DB")
                return

            # Ці статуси потрібні для того щоб UI розумів коли бд вже зберегла усі чанки і готова обробляти їх
            # 1. Починаємо обробку: статус "processing"
            document.processing_status = "processing"
            await db.commit()

            try:
                full_text = pdf_service.extract_text(document.file_path)

                if not full_text:
                    print(f"⚠️ Document {document.id} has no text")
                    # Помилка: пустий текст
                    document.processing_status = "failed"
                    await db.commit()
                    return

                chunk_size = 1000
                overlap = 100
                chunks = []

                for i in range(0, len(full_text), chunk_size - overlap):
                    chunk = full_text[i : i + chunk_size]
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
                    document.processing_status = "completed"
                    await db.commit()
                    print(f" Successfully saved {len(new_chunks)} chunks")
                else:
                    print(f" No chunks were created/saved")
                    document.processing_status = "failed"
                    await db.commit()

            except Exception as e:
                print(f"❌ Error processing document: {e}")
                document.processing_status = "failed"
                await db.commit()


rag_service = RagService()

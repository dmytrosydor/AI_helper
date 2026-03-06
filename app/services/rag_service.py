import asyncio
import re

from google import genai
from google.genai import types
from sqlalchemy import select

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.models.document import Document, DocumentChunk
from app.services.pdf_service import pdf_service

client = genai.Client(api_key=settings.GEMINI_API_KEY)


class RagService:
    def _semantic_chunking(self, text: str, max_size: int = 1000, overlap: int  = 150 ) -> list[str]:
        segments = re.split(r"(?<=[.!?])\s+|\n\n+", text)
        chunks = []
        current_chunk = []
        current_length = 0

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            segment_len = len(segment)

            if segment_len > max_size:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                for i in range(0, segment_len, max_size - overlap):
                    chunks.append(segment[i : i + max_size])
                continue

            if current_length + segment_len + 1 > max_size and current_chunk:
                chunks.append(" ".join(current_chunk))

                overlap_length = 0
                overlap_chunk = []
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= overlap:
                        overlap_chunk.insert(0, s)
                        overlap_length += len(s) + 1
                    else:
                        break

                current_chunk = overlap_chunk
                current_length = sum(len(s) + 1 for s in current_chunk)

            current_chunk.append(segment)
            current_length += segment_len + 1

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks






    def get_embedding(self, text: str) -> list[float]:
        try:
            # Використовуємо text-embedding
            result = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768),
            )
            print("Result:", result)

            return result.embeddings[0].values
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return []

    async def process_document(self, document_id: int):
        async with AsyncSessionLocal() as db:
            print(f"---Start processing document ID {document_id} ---")

            stmt = select(Document).filter(Document.id == document_id)
            result = await db.execute(stmt)
            document = result.scalars().first()

            if not document:
                print("Document not found in DB")
                return

            # Ці статуси потрібні для того, щоб UI розумів коли бд вже зберегла усі чанки і готова обробляти їх
            # 1. Починаємо обробку: статус "processing"
            document.processing_status = "processing"
            await db.commit()

            try:
                full_text = await asyncio.to_thread(pdf_service.extract_text, document.file_path)

                if not full_text:
                    print(f"Document {document.id} has no text")
                    # Помилка: пустий текст
                    document.processing_status = "failed"
                    await db.commit()
                    return

                chunk_size = 1000
                overlap = 150

                raw_chunks = self._semantic_chunking(full_text, max_size = chunk_size, overlap=overlap)

                chunks = [c for c in raw_chunks if len(c) > 50]
                print(f"Created {len(chunks)} chunks. Vectorizing...")

                new_chunks = []
                for idx, chunk_text in enumerate(chunks):
                    vector = await asyncio.to_thread(self.get_embedding, chunk_text)

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
                    print(" No chunks were created/saved")
                    document.processing_status = "failed"
                    await db.commit()

            except Exception as e:
                print(f"❌ Error processing document: {e}")
                document.processing_status = "failed"
                await db.commit()


rag_service = RagService()

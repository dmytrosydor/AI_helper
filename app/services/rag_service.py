from google import genai
from  sqlalchemy.orm import Session
from app.core.config import settings
from app.models.document import Document,DocumentChunk


from app.services.pdf_service import pdf_service

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class RagService:
    def get_embedding(self,text:str)-> list[float]:
        try:

            result = client.models.embed_content(
                model="text-embedding-004",
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=768)
            )
            return result.embeddings[0].values()
        except Exception as e:
            print(f"Gemini API Error {e}")
            return []

    def process_document(
            self,
            db: Session,
            document: Document,
    ):

        try:
            full_text = pdf_service.extract_text(document.file_path)
        except Exception as e:
            print(f"Error reading PDF {e}")
            return


        if not full_text:
            print(f"Document {document.file_path} has no text")
            return

        chunk_size = 1000
        overlap  = 100
        chunks = []

        for i in range(0,len(full_text),chunk_size-overlap):
            chunk = full_text[i:i+chunk_size]
            if len(chunk) < 50:
                chunks.append(chunk)


        new_chunks = []
        for idx, chunk_text in enumerate(chunks):
            vector = self.get_embedding(chunk_text)

            if vector:
                db_chunnk = DocumentChunk(
                    document_id=document.id,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    embedding=vector,
                )
                new_chunks.append(db_chunnk)

        if new_chunks:
            db.add_all(new_chunks)
            db.commit()
        else:
            print(f"No chunks were created/saved")


rag_service = RagService()

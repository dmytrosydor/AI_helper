import json
from sqlalchemy.orm import Session
from sqlalchemy import select
from google import genai
from google.genai import types

from app.core.config import settings
from app.models.document import Document, DocumentChunk
from app.models.analysis import ProjectAnalysis, ProjectAnalysisItem
from app.schemas.study import ExamResponse

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class StudyService:

    def _get_docs_hash(self, documents_ids: list[int]) -> str:
        return ','.join(map(str, sorted(documents_ids)))

    def _get_project_context(self,
                             db: Session,
                             project_id: int,
                             documents_ids: list[int] | None = None
                             ) -> str:
        """Витягує текст з доків проєкту, враховуючи фільтр по ID"""
        stmt = (
            select(DocumentChunk.chunk_text)
            .join(Document)
            .filter(Document.project_id == project_id)
            .order_by(Document.id, DocumentChunk.chunk_index)
        )

        # 🔥 ДОДАНО: Фільтрація, якої не вистачало
        if documents_ids:
            stmt = stmt.filter(Document.id.in_(documents_ids))

        chunks = db.scalars(stmt).all()
        return "\n\n".join(chunks)

    def _get_cached_or_generate(self,
                                db: Session,
                                project_id: int,
                                document_ids: list[int] | None,
                                field_name: str,
                                generator_func
                                ):
        # 1. Сценарій: "Весь проєкт" (кеш в ProjectAnalysis)
        if not document_ids:
            analysis = db.query(ProjectAnalysis).filter_by(project_id=project_id).first()
            if analysis and getattr(analysis, field_name):
                val = getattr(analysis, field_name)
                # Відновлюємо об'єкт для Екзамену
                if field_name == "exam_questions":
                    return ExamResponse(questions=val)
                return val

            context = self._get_project_context(db, project_id)
            if not context:
                return "Проект порожній" if field_name != "exam_questions" else ExamResponse(questions=[])

            # Генеруємо
            result = generator_func(context)

            if not analysis:
                analysis = ProjectAnalysis(project_id=project_id)
                db.add(analysis)

            # Зберігаємо (JSON для питань, текст для решти)
            val_to_save = [q.model_dump() for q in result.questions] if field_name == "exam_questions" else result
            setattr(analysis, field_name, val_to_save)
            db.commit()
            return result

        # 2. Сценарій: "Вибірка файлів" (кеш в ProjectAnalysisItem)
        else:
            docs_hash = self._get_docs_hash(document_ids)
            item = db.query(ProjectAnalysisItem).filter_by(project_id=project_id, documents_hash=docs_hash).first()

            if item and getattr(item, field_name):
                val = getattr(item, field_name)
                if field_name == "exam_questions":
                    return ExamResponse(questions=val)
                return val

            context = self._get_project_context(db, project_id, document_ids)
            if not context:
                return "Текст відсутній" if field_name != "exam_questions" else ExamResponse(questions=[])

            # Генеруємо
            result = generator_func(context)

            if not item:
                # Виправлено назву поля document_hash -> documents_hash
                item = ProjectAnalysisItem(project_id=project_id, documents_hash=docs_hash)
                db.add(item)

            val_to_save = [q.model_dump() for q in result.questions] if field_name == "exam_questions" else result
            setattr(item, field_name, val_to_save)
            db.commit()
            return result

    # --- ПУБЛІЧНІ МЕТОДИ (Entry Points) ---

    def get_summary(self, db: Session, project_id: int, document_ids: list[int] | None) -> str:
        return self._get_cached_or_generate(
            db, project_id, document_ids, "summary",
            lambda ctx: self._generate_ai_text(ctx, "Зроби детальний підсумок (Summary). Структура: Вступ, Основні ідеї, Висновки.")
        )

    def get_keypoints(self, db: Session, project_id: int, document_ids: list[int] | None) -> str:
        return self._get_cached_or_generate(
            db, project_id, document_ids, "key_points",
            lambda ctx: self._generate_ai_text(ctx, "Виділи ключові моменти (Key Points) маркованим списком.")
        )

    def get_exam_questions(self, db: Session, project_id: int, document_ids: list[int] | None) -> ExamResponse:
        return self._get_cached_or_generate(
            db, project_id, document_ids, "exam_questions",
            lambda ctx: self._generate_exam_json(ctx)
        )

    def answer_user_questions(self,
                              db: Session,
                              project_id: int,
                              questions: list[str],
                              document_ids: list[int] | None = None # 🔥 Додано параметр
                              ) -> str:
        text = self._get_project_context(db, project_id, document_ids) # 🔥 Передаємо фільтр
        if not text:
            return "Немає контексту для відповіді."

        questions_str = "\n".join([f"- {q}" for q in questions])
        prompt = f"""
        Дай чіткі відповіді на питання, використовуючи ТІЛЬКИ наданий контекст.
        ПИТАННЯ:
        {questions_str}
        КОНТЕКСТ:
        {text}
        """
        return self._generate_ai_text(prompt, "") # Другий аргумент пустий, бо промпт повний

    # --- ПРИВАТНІ ГЕНЕРАТОРИ ---

    def _generate_ai_text(self, text_or_prompt: str, instruction: str = "") -> str:
        """Універсальний генератор тексту"""
        content = f"{instruction}\n\nТЕКСТ:\n{text_or_prompt}" if instruction else text_or_prompt
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash", # Використовуй 1.5-flash, він стабільніший
                contents=content
            )
            return response.text
        except Exception as e:
            return f"Error: {e}"

    def _generate_exam_json(self, text: str) -> ExamResponse:
        """Генератор JSON для екзамену"""
        prompt = f"""
        Створи 5 тестових питань для підготовки до екзамену на основі тексту.
        Для кожного питання дай 4 варіанти відповіді та вкажи правильну.
        ТЕКСТ:
        {text[:50000]} 
        """
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExamResponse
                )
            )
            return ExamResponse.model_validate_json(response.text)
        except Exception as e:
            print(f"JSON Error: {e}")
            return ExamResponse(questions=[]) # Виправлено question -> questions

study_service = StudyService()

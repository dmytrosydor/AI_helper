import json
from sqlalchemy.orm import Session
from sqlalchemy import select
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.prompts import StudyPrompts  # 👈 Новий імпорт
from app.models.document import Document, DocumentChunk
from app.models.analysis import ProjectAnalysis, ProjectAnalysisItem
from app.schemas.study import ExamResponse

# Ініціалізація клієнта
client = genai.Client(api_key=settings.GEMINI_API_KEY)

class StudyService:

    # --- HELPER METHODS ---

    def _get_docs_hash(self, documents_ids: list[int]) -> str:
        """Створює унікальний підпис для набору файлів"""
        return ','.join(map(str, sorted(documents_ids)))

    def _get_context(self, db: Session, project_id: int, document_ids: list[int] | None = None) -> str:
        """Витягує текст з бази"""
        stmt = (
            select(DocumentChunk.chunk_text)
            .join(Document)
            .filter(Document.project_id == project_id)
            .order_by(Document.id, DocumentChunk.chunk_index)
        )
        if document_ids:
            stmt = stmt.filter(Document.id.in_(document_ids))

        chunks = db.scalars(stmt).all()
        return "\n\n".join(chunks)

    def _generate_ai(self, prompt: str, schema=None) -> str | ExamResponse:
        """Єдина точка входу для запитів до AI"""
        config = None
        if schema:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema
            )

        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=config
            )

            if schema:
                # Якщо очікуємо JSON/Schema, парсимо його
                return schema.model_validate_json(response.text)
            return response.text

        except Exception as e:
            print(f"AI Generation Error: {e}")
            return schema(questions=[]) if schema else "Виникла помилка при генерації."

    # --- CACHE LOGIC (Робота з БД) ---

    def _get_full_project_cache(self, db: Session, project_id: int, field: str):
        """Шукає кеш для всього проєкту"""
        analysis = db.query(ProjectAnalysis).filter_by(project_id=project_id).first()
        if analysis:
            return getattr(analysis, field)
        return None

    def _save_full_project_cache(self, db: Session, project_id: int, field: str, value):
        """Зберігає кеш для всього проєкту"""
        analysis = db.query(ProjectAnalysis).filter_by(project_id=project_id).first()
        if not analysis:
            analysis = ProjectAnalysis(project_id=project_id)
            db.add(analysis)

        # Для екзамену конвертуємо в dict, для тексту - лишаємо як є
        val_to_save = [q.model_dump() for q in value.questions] if field == "exam_questions" else value
        setattr(analysis, field, val_to_save)
        db.commit()

    def _get_partial_cache(self, db: Session, project_id: int, doc_hash: str, field: str):
        """Шукає кеш для вибірки файлів"""
        item = db.query(ProjectAnalysisItem).filter_by(project_id=project_id, documents_hash=doc_hash).first()
        if item:
            return getattr(item, field)
        return None

    def _save_partial_cache(self, db: Session, project_id: int, doc_hash: str, field: str, value):
        """Зберігає кеш для вибірки файлів"""
        item = db.query(ProjectAnalysisItem).filter_by(project_id=project_id, documents_hash=doc_hash).first()
        if not item:
            item = ProjectAnalysisItem(project_id=project_id, documents_hash=doc_hash)
            db.add(item)

        val_to_save = [q.model_dump() for q in value.questions] if field == "exam_questions" else value
        setattr(item, field, val_to_save)
        db.commit()

    def _is_valid_result(self, result) -> bool:
        """Перевіряє, чи варто зберігати цей результат у базу"""

        # 1. Якщо це Екзамен (об'єкт ExamResponse)
        if hasattr(result, "questions"):
            # Не зберігаємо, якщо питань немає
            return bool(result.questions)

        # 2. Якщо це Текст (Summary, Key Points)
        if isinstance(result, str):
            if not result.strip():
                return False  # Пустий рядок
            if "Виникла помилка" in result or result.startswith("Error:"):
                return False  # Повідомлення про помилку
            if len(result) < 50:
                return False  # Підозріло коротка відповідь
            return True

        return False
    # --- MAIN ORCHESTRATOR (Головна функція) ---

    def _process_request(self, db: Session, project_id: int, document_ids: list[int] | None, field_name: str, prompt_template: str, response_schema=None):
        """
        Універсальний метод, який:
        1. Перевіряє кеш (повний або частковий).
        2. Якщо пусто -> бере контекст.
        3. Генерує через AI.
        4. Зберігає в кеш.
        """

        # 1. Спроба взяти з кешу
        cached_data = None
        if not document_ids:
            cached_data = self._get_full_project_cache(db, project_id, field_name)
        else:
            doc_hash = self._get_docs_hash(document_ids)
            cached_data = self._get_partial_cache(db, project_id, doc_hash, field_name)

        if cached_data:
            # Якщо це екзамен, відновлюємо Pydantic модель з JSON
            if response_schema:
                return response_schema(questions=cached_data)
            return cached_data

        # 2. Генерація (якщо кешу немає)
        context = self._get_context(db, project_id, document_ids)
        if not context:
            return response_schema(questions=[]) if response_schema else "Текст відсутній."

        # Формуємо промпт через шаблон
        full_prompt = prompt_template.format(context=context)

        result = self._generate_ai(full_prompt, schema=response_schema)

        # 3. Збереження
        if self._is_valid_result(result):
            if not document_ids:
                self._save_full_project_cache(db, project_id, field_name, result)
            else:
                self._save_partial_cache(db, project_id, self._get_docs_hash(document_ids), field_name, result)
        else:
            print(f"Warning: Invalid result for {field_name}: {result}")

        return result

    # --- PUBLIC API METHODS (Тепер вони дуже прості) ---

    def get_summary(self, db: Session, project_id: int, document_ids: list[int] | None) -> str:
        return self._process_request(
            db, project_id, document_ids,
            field_name="summary",
            prompt_template=StudyPrompts.SUMMARY
        )

    def get_keypoints(self, db: Session, project_id: int, document_ids: list[int] | None) -> str:
        return self._process_request(
            db, project_id, document_ids,
            field_name="key_points",
            prompt_template=StudyPrompts.KEY_POINTS
        )

    def get_exam_questions(self, db: Session, project_id: int, document_ids: list[int] | None) -> ExamResponse:
        return self._process_request(
            db, project_id, document_ids,
            field_name="exam_questions",
            prompt_template=StudyPrompts.EXAM_GENERATION,
            response_schema=ExamResponse
        )

    def answer_user_questions(self, db: Session, project_id: int, questions: list[str], document_ids: list[int] | None) -> str:
        # Тут кешування не потрібне, тому викликаємо напряму
        context = self._get_context(db, project_id, document_ids)
        if not context: return "Немає контексту."

        q_list_str = "\n".join([f"- {q}" for q in questions])
        full_prompt = StudyPrompts.USER_QUESTION.format(questions_list=q_list_str, context=context)

        return self._generate_ai(full_prompt)

study_service = StudyService()
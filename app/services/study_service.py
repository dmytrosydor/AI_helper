import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google import genai
from google.genai import types
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.prompts import StudyPrompts
from app.models.document import Document, DocumentChunk
from app.models.analysis import ProjectAnalysis, ProjectAnalysisItem
from app.schemas.study import ExamResponse, KeyPointsResponse, UserQuestionsResponse

# Ініціалізація клієнта
ollama_client = AsyncOpenAI(base_url=settings.OLLAMA_BASE_URL, api_key="ollama")

class StudyService:

    # --- HELPER METHODS ---

    def _get_docs_hash(self, documents_ids: list[int]) -> str:
        """Створює унікальний підпис для набору файлів"""
        return ','.join(map(str, sorted(documents_ids)))

    async def _get_context(self, db: AsyncSession, project_id: int, document_ids: list[int] | None = None) -> str:
        """Витягує текст з бази"""
        stmt = (
            select(DocumentChunk.chunk_text)
            .join(Document)
            .filter(Document.project_id == project_id)
            .order_by(Document.id, DocumentChunk.chunk_index)
        )
        if document_ids:
            stmt = stmt.filter(Document.id.in_(document_ids))

        result = await db.execute(stmt)
        chunks = result.scalars().all()

        full_text = "\n\n".join(chunks)

        if len(full_text) > 200_000:
            return full_text[:200_000]
        return full_text




    async  def _generate_ai(self, prompt: str, schema=None) -> str | BaseModel:
        """Єдина точка входу для запитів до AI"""
        config = None
        if schema:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema
            )

        try:
            response = await ollama_client.chat.completions.create(
                model=settings.OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"} if schema else None
            )

            result_text = response.choices[0].message.content
            if schema:
                data_dict = json.loads(result_text)
                return schema(**data_dict)
            return response.text

        except Exception as e:
            print(f"AI Generation Error: {e}")
            # Повертаємо пустий об'єкт у випадку помилки, щоб фронтенд не падав
            if schema:
                if schema == ExamResponse:
                    return ExamResponse(questions=[])
                if schema == KeyPointsResponse:
                    return KeyPointsResponse(points=[])
            return "Виникла помилка при генерації."

    # --- CACHE LOGIC (Збереження та читання) ---

    def _save_data_to_db(self, db_obj, field: str, value):
        """Універсальне збереження даних в об'єкт БД"""
        data_to_save = value

        # 1. Якщо це Pydantic модель -> конвертуємо в dict
        if isinstance(value, BaseModel):
            data_to_save = value.model_dump()

        # 2. Специфічна логіка для типів колонок у БД
        # key_points у нас TEXT, тому треба перетворити dict -> str (JSON)
        if field == "key_points" and not isinstance(data_to_save, str):
            data_to_save = json.dumps(data_to_save, ensure_ascii=False)


        setattr(db_obj, field, data_to_save)

    async def _save_full_project_cache(self, db: AsyncSession, project_id: int, field: str, value):
        stmt = (
            select(ProjectAnalysisItem)
            .filter_by(project_id=project_id)
        )
        result = await db.execute(stmt)
        analysis = result.scalars().first()
        if not analysis:
            analysis = ProjectAnalysis(project_id=project_id)
            db.add(analysis)

        self._save_data_to_db(analysis, field, value)
        await db.commit()

    async def _save_partial_cache(self, db: AsyncSession, project_id: int, doc_hash: str, field: str, value):
        stmt = (
            select(ProjectAnalysisItem)
            .filter_by(project_id=project_id, documents_hash=doc_hash)
        )
        result = await db.execute(stmt)
        item = result.scalars().first()
        if not item:
            item = ProjectAnalysisItem(project_id=project_id, documents_hash=doc_hash)
            db.add(item)

        self._save_data_to_db(item, field, value)
        await db.commit()

    def _is_valid_result(self, result) -> bool:
        # Перевірка Pydantic моделей
        if isinstance(result, ExamResponse):
            return bool(result.questions)
        if isinstance(result, KeyPointsResponse):
            return bool(result.points)

        # Перевірка тексту
        if isinstance(result, str):
            if not result.strip(): return False
            if "Error" in result or "помилка" in result.lower(): return False
            return True
        return False

    # --- MAIN ORCHESTRATOR ---

    async def _process_request(self, db: AsyncSession, project_id: int, document_ids: list[int] | None, field_name: str, prompt_template: str, response_schema=None):

        # 1. Спроба взяти з кешу
        cached_data = None
        if not document_ids:
            stmt = (
                select(ProjectAnalysis)
                .filter_by(project_id=project_id)
            )
            result = await db.execute(stmt)
            analysis = result.scalars().first()
            if analysis: cached_data = getattr(analysis, field_name)
        else:
            doc_hash = self._get_docs_hash(document_ids)
            stmt = (
                select(ProjectAnalysisItem)
                .filter_by(project_id=project_id, documents_hash=doc_hash)
            )
            result = await db.execute(stmt)
            item = result.scalars().first()
            if item: cached_data = getattr(item, field_name)

        # 2. Якщо кеш є, треба його правильно відновити (Re-hydrate)
        if cached_data:
            if response_schema:
                try:
                    # Варіант А: Кеш прийшов як рядок (для key_points, бо в БД це TEXT)
                    if isinstance(cached_data, str):
                        data_dict = json.loads(cached_data)
                        return response_schema(**data_dict)

                    # Варіант Б: Кеш прийшов як список/словник (для exam_questions, бо в БД це JSONB)
                    if isinstance(cached_data, (dict, list)):
                        # Специфіка ExamResponse: в БД ми могли зберегти просто список питань
                        if field_name == "exam_questions" and isinstance(cached_data, list):
                            return response_schema(questions=cached_data)

                        return response_schema(**cached_data)

                except Exception as e:
                    print(f"Cache parsing error for {field_name}: {e}")
                    # Якщо кеш битий, ігноруємо і йдемо генерувати
            else:
                return cached_data

        # 3. Генерація (якщо кешу немає або він битий)
        context = await self._get_context(db, project_id, document_ids)
        if not context:
            if response_schema:
                if response_schema == ExamResponse: return ExamResponse(questions=[])
                if response_schema == KeyPointsResponse: return KeyPointsResponse(points=[])
            return "Текст відсутній."

        full_prompt = prompt_template.format(context=context)
        result = await self._generate_ai(full_prompt, schema=response_schema)

        # 4. Збереження
        if self._is_valid_result(result):
            if not document_ids:
                await self._save_full_project_cache(db, project_id, field_name, result)
            else:
                await self._save_partial_cache(db, project_id, self._get_docs_hash(document_ids), field_name, result)

        return result

    # --- PUBLIC API METHODS ---

    async def get_summary(self, db: AsyncSession, project_id: int, document_ids: list[int] | None) -> str:
        return await self._process_request(
            db, project_id, document_ids,
            field_name="summary",
            prompt_template=StudyPrompts.SUMMARY
        )

    async def get_keypoints(self, db: AsyncSession, project_id: int, document_ids: list[int] | None) -> KeyPointsResponse:

        return await self._process_request(
            db, project_id, document_ids,
            field_name="key_points",
            prompt_template=StudyPrompts.KEY_POINTS,
            response_schema=KeyPointsResponse
        )

    async def get_exam_questions(self, db: AsyncSession, project_id: int, document_ids: list[int] | None, difficulty="Medium",question_count = 10) -> ExamResponse:
        prompt = StudyPrompts.EXAM_GENERATION.format(
            difficulty=difficulty,
            question_count=question_count,
            context="{context}"
        )
        return await self._process_request(
            db, project_id, document_ids,
            field_name="exam_questions",
            prompt_template=prompt,
            response_schema=ExamResponse
        )

    async def answer_user_questions(self, db: AsyncSession, project_id: int, questions: list[str], document_ids: list[int] | None) -> str:
        context = await self._get_context(db, project_id, document_ids)
        if not context: return "Немає контексту."

        q_list_str = "\n".join([f"- {q}" for q in questions])
        full_prompt = StudyPrompts.USER_QUESTION.format(questions_list=q_list_str, context=context)

        return await self._generate_ai(full_prompt,schema=UserQuestionsResponse)

study_service = StudyService()

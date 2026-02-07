from pydantic import BaseModel
from typing import List, Optional

# --- ВХІДНІ ДАНІ (Requests) ---

class StudyRequest(BaseModel):
    """Використовується для Summary, Key Points, Exam"""

    document_ids: Optional[List[int]] = None

class UserQuestionsRequest(BaseModel):
    """Використовується для 'Ask Questions'"""
    questions: List[str]

    document_ids: Optional[List[int]] = None


# --- ВИХІДНІ ДАНІ (Responses) ---

class StudyContentResponse(BaseModel):
    content: str

class ExamQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str

class ExamResponse(BaseModel):
    questions: List[ExamQuestion]

class QuestionAnswerPair(BaseModel):
    question: str
    answer: str

class UserQuestionsResponse(BaseModel):
    results: List[QuestionAnswerPair]
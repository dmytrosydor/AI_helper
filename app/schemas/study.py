
from pydantic import BaseModel,Field
from typing import List, Optional

# --- ВХІДНІ ДАНІ (Requests) ---

class BaseStudyRequest(BaseModel):
    """Використовується для Summary, Key Points"""

    document_ids: Optional[List[int]] = None

class ExamRequest(BaseStudyRequest):

    difficulty: str = Field("Medium", description = "Easy, Medium, Hard")
    question_count: int = Field(10, ge=1,le=20, description = "How many questions to generate (1-20)")


class UserQuestionsRequest(BaseModel):
    """Використовується для 'Ask Questions'"""
    questions: List[str]

    document_ids: Optional[List[int]] = None

class KeyPoints(BaseModel):
    title: str
    description: str
    importance: str # high, medium, low

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

class KeyPointsResponse(BaseModel):
    points: List[KeyPoints]
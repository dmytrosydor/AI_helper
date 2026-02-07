from pydantic import BaseModel

class ExamQuestion(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    explanation: str

class ExamResponse(BaseModel):
    question: list[ExamQuestion]

class UserQuestionsRequest(BaseModel):
    questions: list[str]

class QuestionAnswerPair(BaseModel):
    question: str
    answer: str

class UserQuestionsResponse(BaseModel):
    results: list[QuestionAnswerPair]



class StudyContentResponse(BaseModel):
    content: str


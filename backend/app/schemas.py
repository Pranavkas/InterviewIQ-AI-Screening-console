from typing import List, Optional
from pydantic import BaseModel


class CandidateProfileOut(BaseModel):
    id: str
    name: Optional[str]
    skills: List[str]
    technologies: List[str]
    domains: List[str]

    class Config:
        from_attributes = True


class StartInterviewResponse(BaseModel):
    candidate: CandidateProfileOut
    session_id: str
    role: str
    max_questions: int


class QuestionOut(BaseModel):
    qa_id: str
    sequence: int
    topic: Optional[str]
    difficulty: str
    question_text: str
    is_last: bool


class AnswerIn(BaseModel):
    qa_id: str
    answer_text: str


class AnswerFeedbackOut(BaseModel):
    evaluation_score: float
    evaluation_feedback: str
    session_status: str  # in_progress | completed


class QAItemOut(BaseModel):
    sequence: int
    topic: Optional[str]
    difficulty: str
    question_text: str
    answer_text: Optional[str]
    evaluation_score: Optional[float]
    evaluation_feedback: Optional[str]

    class Config:
        from_attributes = True


class SessionSummaryOut(BaseModel):
    session_id: str
    role: str
    status: str
    overall_score: Optional[float]
    strengths: List[str]
    weaknesses: List[str]
    topic_coverage: List[str]
    summary_text: Optional[str]
    qa_history: List[QAItemOut]

import uuid
import datetime as dt
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=True)
    resume_text = Column(Text, nullable=False)
    skills = Column(JSON, default=list)          # e.g. ["Python", "Django", "PostgreSQL"]
    technologies = Column(JSON, default=list)    # frameworks/tools/platforms
    domains = Column(JSON, default=list)         # e.g. ["fintech", "e-commerce"]
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    sessions = relationship("InterviewSession", back_populates="candidate")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    candidate_id = Column(String, ForeignKey("candidates.id"), nullable=False)
    role = Column(String, nullable=False)                 # role key e.g. backend_engineer
    status = Column(String, default="in_progress")        # in_progress | completed
    current_question_index = Column(Integer, default=0)
    current_difficulty = Column(String, default="medium")
    topic_queue = Column(JSON, default=list)
    running_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    candidate = relationship("Candidate", back_populates="sessions")
    qa_pairs = relationship("QuestionAnswer", back_populates="session", order_by="QuestionAnswer.sequence")


class QuestionAnswer(Base):
    __tablename__ = "question_answers"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    topic = Column(String, nullable=True)
    difficulty = Column(String, default="medium")          # easy | medium | hard
    question_text = Column(Text, nullable=False)
    retrieved_context = Column(JSON, default=list)          # chunks used to ground the question
    answer_text = Column(Text, nullable=True)
    evaluation_score = Column(Float, nullable=True)          # 0-10
    evaluation_feedback = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    session = relationship("InterviewSession", back_populates="qa_pairs")


class SessionReport(Base):
    __tablename__ = "session_reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("interview_sessions.id"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=True)
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    topic_coverage = Column(JSON, default=list)
    summary_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

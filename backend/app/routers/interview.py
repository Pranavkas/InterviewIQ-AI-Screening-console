import datetime as dt
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import InterviewSession, Candidate, QuestionAnswer, SessionReport
from app.schemas import QuestionOut, AnswerIn, AnswerFeedbackOut, SessionSummaryOut, QAItemOut
from app.services import interview_engine

router = APIRouter(prefix="/api/interview", tags=["interview"])


def _candidate_dict(candidate: Candidate) -> dict:
    return {
        "skills": candidate.skills or [],
        "technologies": candidate.technologies or [],
        "domains": candidate.domains or [],
    }


def _get_session_or_404(db: Session, session_id: str) -> InterviewSession:
    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.get("/{session_id}/next-question", response_model=QuestionOut)
def next_question(session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, session_id)

    if session.status == "completed":
        raise HTTPException(400, "Interview session already completed.")

    candidate = db.get(Candidate, session.candidate_id)

    # Lazily build the topic queue on the first call.
    if not session.topic_queue:
        session.topic_queue = interview_engine.build_topic_queue(session.role, _candidate_dict(candidate))
        db.commit()

    if session.current_question_index >= len(session.topic_queue):
        raise HTTPException(400, "No more topics queued; call the summary endpoint to finalize.")

    topic = session.topic_queue[session.current_question_index]
    generated = interview_engine.generate_question(
        session.role, topic, session.current_difficulty, _candidate_dict(candidate)
    )

    qa = QuestionAnswer(
        session_id=session.id,
        sequence=session.current_question_index + 1,
        topic=generated["topic"],
        difficulty=generated["difficulty"],
        question_text=generated["question_text"],
        retrieved_context=generated["retrieved_context"],
    )
    db.add(qa)
    db.commit()
    db.refresh(qa)

    is_last = qa.sequence >= settings.MAX_QUESTIONS
    return QuestionOut(
        qa_id=qa.id,
        sequence=qa.sequence,
        topic=qa.topic,
        difficulty=qa.difficulty,
        question_text=qa.question_text,
        is_last=is_last,
    )


@router.post("/{session_id}/answer", response_model=AnswerFeedbackOut)
def submit_answer(session_id: str, payload: AnswerIn, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, session_id)
    qa = db.get(QuestionAnswer, payload.qa_id)
    if not qa or qa.session_id != session_id:
        raise HTTPException(404, "Question not found for this session")

    evaluation = interview_engine.evaluate_answer(
        session.role, qa.question_text, payload.answer_text, qa.retrieved_context or []
    )

    qa.answer_text = payload.answer_text
    qa.evaluation_score = evaluation["score"]
    qa.evaluation_feedback = evaluation["feedback"]
    qa.answered_at = dt.datetime.utcnow()

    # Advance session state + adapt difficulty for the next question.
    session.current_question_index += 1
    if settings.ADAPTIVE_DIFFICULTY:
        session.current_difficulty = interview_engine.next_difficulty(
            session.current_difficulty, evaluation["score"]
        )

    if session.current_question_index >= min(len(session.topic_queue), settings.MAX_QUESTIONS):
        session.status = "completed"
        session.completed_at = dt.datetime.utcnow()

    db.commit()

    return AnswerFeedbackOut(
        evaluation_score=evaluation["score"],
        evaluation_feedback=evaluation["feedback"],
        session_status=session.status,
    )


@router.get("/{session_id}/summary", response_model=SessionSummaryOut)
def get_summary(session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, session_id)
    qa_pairs = db.query(QuestionAnswer).filter(
        QuestionAnswer.session_id == session_id
    ).order_by(QuestionAnswer.sequence).all()

    existing_report = db.query(SessionReport).filter(SessionReport.session_id == session_id).first()

    if not existing_report:
        qa_dicts = [
            {
                "topic": qa.topic,
                "difficulty": qa.difficulty,
                "question_text": qa.question_text,
                "answer_text": qa.answer_text,
                "evaluation_score": qa.evaluation_score,
            }
            for qa in qa_pairs
            if qa.answer_text is not None
        ]
        report_data = interview_engine.synthesize_report(session.role, qa_dicts)
        existing_report = SessionReport(
            session_id=session.id,
            overall_score=report_data["overall_score"],
            strengths=report_data["strengths"],
            weaknesses=report_data["weaknesses"],
            topic_coverage=report_data["topic_coverage"],
            summary_text=report_data["summary_text"],
        )
        db.add(existing_report)
        db.commit()
        db.refresh(existing_report)

    return SessionSummaryOut(
        session_id=session.id,
        role=session.role,
        status=session.status,
        overall_score=existing_report.overall_score,
        strengths=existing_report.strengths or [],
        weaknesses=existing_report.weaknesses or [],
        topic_coverage=existing_report.topic_coverage or [],
        summary_text=existing_report.summary_text,
        qa_history=[QAItemOut.model_validate(qa) for qa in qa_pairs],
    )

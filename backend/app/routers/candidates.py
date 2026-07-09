from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import Candidate, InterviewSession
from app.schemas import StartInterviewResponse, CandidateProfileOut
from app.services.resume_parser import parse_resume
from app.services import rag_engine

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("/roles")
def list_roles():
    return [{"key": k, "label": v["label"]} for k, v in settings.ROLE_CONFIG.items()]


@router.post("/upload-resume", response_model=StartInterviewResponse)
async def upload_resume(
    role: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if role not in settings.ROLE_CONFIG:
        raise HTTPException(400, f"Unknown role '{role}'. Valid roles: {list(settings.ROLE_CONFIG.keys())}")

    file_bytes = await file.read()
    try:
        parsed = parse_resume(file.filename, file_bytes)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if not rag_engine.kb_is_ready(role):
        raise HTTPException(
            503,
            f"Knowledge base for role '{role}' is not ingested yet. "
            f"Run scripts/ingest_kb.py first.",
        )

    candidate = Candidate(
        name=parsed.get("name"),
        resume_text=parsed["resume_text"],
        skills=parsed["skills"],
        technologies=parsed["technologies"],
        domains=parsed["domains"],
    )
    db.add(candidate)
    db.flush()

    session = InterviewSession(candidate_id=candidate.id, role=role)
    db.add(session)
    db.commit()
    db.refresh(candidate)
    db.refresh(session)

    return StartInterviewResponse(
        candidate=CandidateProfileOut.model_validate(candidate),
        session_id=session.id,
        role=role,
        max_questions=settings.MAX_QUESTIONS,
    )

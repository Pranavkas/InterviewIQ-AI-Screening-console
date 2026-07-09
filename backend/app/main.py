import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import candidates, interview
from app.services.llm_client import is_llm_available, active_model_name

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AI-Powered Candidate Screening System",
    description="RAG-driven, role-based adaptive technical interview engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(candidates.router)
app.include_router(interview.router)


@app.on_event("startup")
def on_startup():
    init_db()
    
    # Auto-ingest knowledge base on startup if empty (e.g. when mounting clean persistent volume)
    import os
    from app.services.rag_engine import kb_is_ready, ingest_role_kb
    for role_key, cfg in settings.ROLE_CONFIG.items():
        if not kb_is_ready(role_key):
            file_path = os.path.join(settings.KNOWLEDGE_BASE_DIR, cfg["kb_file"])
            if os.path.exists(file_path):
                logging.info("Auto-ingesting knowledge base for role '%s' on startup...", role_key)
                try:
                    ingest_role_kb(role_key, file_path)
                except Exception as e:
                    logging.error("Failed to auto-ingest knowledge base for role '%s': %s", role_key, e)
            else:
                logging.warning("Knowledge base file not found for role '%s' at %s", role_key, file_path)

    if not is_llm_available():
        logging.warning(
            "LLM provider '%s' is not reachable — question generation/evaluation "
            "will use deterministic fallbacks until it's available.",
            settings.LLM_PROVIDER,
        )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_available": is_llm_available(),
        "model": active_model_name(),
    }

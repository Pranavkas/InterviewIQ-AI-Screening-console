"""
Central configuration for the AI Candidate Screening System.
All tunables are read from environment variables (with sane defaults)
so the system can be reconfigured without touching code.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/interview.db")

    # --- LLM Provider ---
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")  # "ollama" | "groq"

    # --- Ollama (local LLM) ---
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    # --- Groq (hosted LLM API) ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    GROQ_TIMEOUT: int = int(os.getenv("GROQ_TIMEOUT", "60"))

    # --- ChromaDB (RAG vector store) ---
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_store")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    # --- Knowledge base ---
    KNOWLEDGE_BASE_DIR: str = os.getenv("KNOWLEDGE_BASE_DIR", "./knowledge_base")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "180"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "30"))
    TOP_K_CHUNKS: int = int(os.getenv("TOP_K_CHUNKS", "4"))

    # --- Interview behaviour ---
    MAX_QUESTIONS: int = int(os.getenv("MAX_QUESTIONS", "6"))
    ADAPTIVE_DIFFICULTY: bool = os.getenv("ADAPTIVE_DIFFICULTY", "true").lower() == "true"

    # --- CORS ---
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")

    # --- Supported roles -> mapped to knowledge base filenames + core topics ---
    ROLE_CONFIG = {
        "backend_engineer": {
            "label": "Backend Engineer",
            "kb_file": "backend_engineer.txt",
            "core_topics": [
                "REST API design", "database indexing", "caching strategies",
                "concurrency and threading", "system design and scalability",
                "authentication and authorization", "message queues",
            ],
        },
        "ai_ml_engineer": {
            "label": "AI/ML Engineer",
            "kb_file": "ai_ml_engineer.txt",
            "core_topics": [
                "model evaluation metrics", "overfitting and regularization",
                "neural network architectures", "feature engineering",
                "training pipelines", "vector embeddings and retrieval",
                "MLOps and model deployment",
            ],
        },
        "frontend_engineer": {
            "label": "Frontend Engineer",
            "kb_file": "frontend_engineer.txt",
            "core_topics": [
                "component architecture", "state management", "rendering performance",
                "browser fundamentals", "accessibility", "responsive design",
                "build tooling",
            ],
        },
    }


settings = Settings()

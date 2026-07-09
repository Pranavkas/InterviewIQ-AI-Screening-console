"""
Run this once (and whenever the knowledge base text files change) to embed
and index the role-specific corpora into ChromaDB.

Usage:
    cd backend
    python -m scripts.ingest_kb
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.services import rag_engine


def main():
    for role_key, cfg in settings.ROLE_CONFIG.items():
        file_path = os.path.join(settings.KNOWLEDGE_BASE_DIR, cfg["kb_file"])
        if not os.path.exists(file_path):
            print(f"[skip] {role_key}: knowledge base file not found at {file_path}")
            continue
        count = rag_engine.ingest_role_kb(role_key, file_path)
        print(f"[ok]   {role_key}: indexed {count} chunks from {cfg['kb_file']}")


if __name__ == "__main__":
    main()

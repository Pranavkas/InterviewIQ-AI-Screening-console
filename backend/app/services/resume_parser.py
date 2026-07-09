"""
Resume Processing
------------------
Parses an uploaded resume (PDF or plain text) and extracts structured
signal: skills, technologies, and domain exposure.

Approach:
1. Extract raw text (pypdf for PDFs).
2. Use a curated keyword taxonomy for fast, deterministic matching
   (works even if the LLM/Ollama is offline).
3. Ask the local LLM to enrich/clean the extraction into structured JSON
   (best-effort; falls back gracefully to the keyword-based result).
"""
import io
import json
import re
from typing import Dict, List

from pypdf import PdfReader

from app.services.llm_client import generate_json

SKILL_TAXONOMY = {
    "languages": ["python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "sql", "r"],
    "backend": ["fastapi", "flask", "django", "spring boot", "express", "node.js", "graphql", "rest api",
                "microservices", "grpc", "kafka", "rabbitmq", "redis", "postgresql", "mysql", "mongodb",
                "docker", "kubernetes", "aws", "gcp", "azure", "nginx", "celery"],
    "ai_ml": ["pytorch", "tensorflow", "scikit-learn", "keras", "pandas", "numpy", "huggingface",
              "transformers", "llm", "rag", "langchain", "nlp", "computer vision", "opencv",
              "xgboost", "mlflow", "vector database", "chromadb", "pinecone", "airflow"],
    "frontend": ["react", "next.js", "vue", "angular", "redux", "tailwind", "css", "html", "webpack",
                 "vite", "typescript", "svelte"],
    "domains": ["fintech", "healthcare", "e-commerce", "logistics", "edtech", "gaming", "insurance",
                "banking", "cybersecurity", "iot", "blockchain", "saas"],
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    text_parts = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(text_parts)


def extract_text(filename: str, file_bytes: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    return file_bytes.decode("utf-8", errors="ignore")


def _keyword_extract(text: str) -> Dict[str, List[str]]:
    lower = text.lower()
    found = {"skills": [], "technologies": [], "domains": []}
    for term in SKILL_TAXONOMY["languages"] + SKILL_TAXONOMY["backend"] + SKILL_TAXONOMY["ai_ml"] + SKILL_TAXONOMY["frontend"]:
        if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", lower):
            bucket = "skills" if term in SKILL_TAXONOMY["languages"] else "technologies"
            found[bucket].append(term)
    for term in SKILL_TAXONOMY["domains"]:
        if term in lower:
            found["domains"].append(term)
    # de-dup while preserving order
    for k in found:
        found[k] = list(dict.fromkeys(found[k]))
    return found


LLM_EXTRACTION_PROMPT = """You are an information extraction engine. Given a resume, extract:
- skills: programming languages and core technical skills
- technologies: frameworks, tools, platforms, databases used
- domains: industry/domain exposure (e.g. fintech, healthcare)
- name: candidate's name if identifiable, else null

Return ONLY valid JSON with exactly these keys: name, skills, technologies, domains.
Each list should contain short strings, max 12 items each, no duplicates.

RESUME:
{resume_text}
"""


def parse_resume(filename: str, file_bytes: bytes) -> Dict:
    raw_text = extract_text(filename, file_bytes).strip()
    if not raw_text:
        raise ValueError("Could not extract any text from the uploaded resume.")

    keyword_result = _keyword_extract(raw_text)

    llm_result = generate_json(
        LLM_EXTRACTION_PROMPT.format(resume_text=raw_text[:6000])
    )

    result = {
        "name": None,
        "skills": keyword_result["skills"],
        "technologies": keyword_result["technologies"],
        "domains": keyword_result["domains"],
    }

    if llm_result:
        result["name"] = llm_result.get("name") or result["name"]
        for key in ("skills", "technologies", "domains"):
            llm_items = llm_result.get(key) or []
            merged = list(dict.fromkeys([*result[key], *[str(i).lower() for i in llm_items]]))
            result[key] = merged[:15]

    result["resume_text"] = raw_text
    return result

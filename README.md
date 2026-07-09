# InterviewIQ — AI-Powered Candidate Screening System

[![GitHub Pages](https://img.shields.io/badge/Live-Demo--on--GitHub--Pages-2dd4bf?style=for-the-badge&logo=github)](https://pranavkas.github.io/InterviewIQ-An-AI-Powered-Candidate-Screening-System/)
[![Deploy to Render](https://img.shields.io/badge/Deploy%20to-Render-46E3B7?style=for-the-badge&logo=render)](https://render.com/deploy?repo=https://github.com/Pranavkas/InterviewIQ-An-AI-Powered-Candidate-Screening-System)

A production-ready, full-stack, RAG-driven screening system that simulates structured technical interviews. Questions are generated dynamically at runtime based on the candidate's resume, the selected role, and custom role-specific knowledge bases fetched via local vector retrieval.

```
Resume + Role  ─▶  Resume Processing  ─▶  Context Construction  ─▶  RAG Retrieval  ─▶  Question Generation
                                                                                               │
Final Summary  ◀─  Response Handling  ◀─  Interactive Interview (adaptive)  ◀────────────────┘
```

---

## 🚀 Key Features

*   **RAG-Driven Question Ingestion:** Dynamically queries role-specific knowledge bases to build contextually relevant grounding material.
*   **Adaptive Screening Flow:** A feedback loop adjusts the difficulty of the next question based on the candidate's answer scores (stronger answers escalate difficulty; weaker ones ease off).
*   **Offline-First Architecture:** Supports fully offline operation using a local Ollama LLM and offline vector indexing, alongside hosted API support (Groq).
*   **High Resilience & Fallbacks:** Zero hard failures if LLMs go offline. All AI pipeline steps have deterministic fallbacks (keyword matching, length-based scoring, static question pools) to ensure the system is always operational.
*   **Containerized & Cloud-Ready:** Multi-stage Docker builds, Docker Compose configurations, and GitHub Actions CI/CD workflows for automated compilation and deployment.

---

## 🛠️ Architecture & Separation of Concerns

The project adheres to clean engineering principles with a clear boundaries layout:

```
ai-interview-system/
├── backend/                     FastAPI service — all business logic lives here
│   ├── app/
│   │   ├── main.py               App startup, middleware config, CORS
│   │   ├── config.py             Settings management via pydantic-like env loader
│   │   ├── database.py           SQLAlchemy engine and database sessions (SQLite)
│   │   ├── models.py             ORM tables: Candidate, Session, QuestionAnswer, Report
│   │   ├── schemas.py            Pydantic validation schemas (API contracts)
│   │   ├── routers/              FastAPI endpoints (candidates, interview loop)
│   │   └── services/             Pluggable business logic (Resume parser, RAG, LLM client)
│   ├── knowledge_base/           Role-specific txt corpora
│   └── scripts/ingest_kb.py      Knowledge base indexing script
├── frontend/                     React (Vite) frontend application
│   └── src/
│       ├── components/           Reusable UI elements
│       ├── pages/                Home, Interview, and Summary views
│       ├── api.js                Centralized fetch service wrapper
│       └── App.jsx               App routing & topbar settings integration
└── render.yaml                   Render Blueprint definition
```

*   **Decoupled AI Engine:** Swapping the LLM provider (Ollama/Groq) or replacing the vector store database requires updating exactly one file (`llm_client.py` and `rag_engine.py` respectively).
*   **Persistent State:** Screening sessions, answers, and synthesized reports are persisted in SQLite, ensuring candidate state survives browser refreshes.

---

## 🧬 Core Pipelines

| Pipeline Stage | Implementation File | Technical Approach |
| :--- | :--- | :--- |
| **Resume Parsing** | `resume_parser.py` | Combines `pypdf` text extraction with regex-based taxonomy matching, enriched by an LLM parsing pass if online. |
| **Grounding (RAG)** | `rag_engine.py` | Paragraph-level text chunking, embedded locally via an offline TF-IDF vectorizer, stored inside ChromaDB. |
| **Adaptivity** | `interview_engine.py` | Calculates rolling difficulty adjustments. Ratings $\ge 7.5/10$ step up difficulty; ratings $< 4/10$ step down difficulty. |
| **Evaluation** | `interview_engine.py` | Automatically scores and evaluates candidate answers based on retrieved reference material. |

---

## ⚡ Deployment & Hosting

### 1. Frontend (GitHub Pages)
The React client is hosted directly on GitHub Pages. You can test it live:
👉 **[Launch Live InterviewIQ Client](https://pranavkas.github.io/InterviewIQ-An-AI-Powered-Candidate-Screening-System/)**

*To communicate with your own backend from the live site, click the **Gear (API Configuration) icon** in the top header and type your backend URL.*

### 2. Backend (Render Cloud Hosting)
You can deploy the backend FastAPI server to Render with one click using the blueprint button below. This spins up the server and prepares all settings automatically:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Pranavkas/InterviewIQ-An-AI-Powered-Candidate-Screening-System)

1. Click the button to open Render's blueprint dashboard.
2. Enter your **`GROQ_API_KEY`** when prompted.
3. Click **Apply** to build and spin up the Docker backend.
4. Copy the backend service URL generated by Render, paste it into the **API settings** gear on the live demo frontend, and you're good to go!

---

## 💻 Local Development Setup

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   *(Optional)* [Ollama](https://ollama.com) for running LLMs locally.

### 1. Backend Service
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows use: .\venv\Scripts\activate

# Install dependencies & prepare environment
pip install -r requirements.txt
cp .env.example .env      # Configure your LLM_PROVIDER and GROQ_API_KEY here

# Ingest knowledge base files and start the server
python -m scripts.ingest_kb
uvicorn app.main:app --reload --port 8000
```
*Access interactive API documentation at `http://localhost:8000/docs`.*

### 2. Frontend client
```bash
cd frontend
npm install
npm run dev
```
*Access the React UI at `http://localhost:5173`.*

### 3. Docker Compose (Alternative Local Build)
To spin up both services containerized locally:
```bash
docker compose up --build
```
*   Frontend: `http://localhost` (port 80)
*   Backend: `http://localhost:8000`

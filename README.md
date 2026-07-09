# Panel — AI-Powered Candidate Screening System

A full-stack, RAG-driven system that simulates a structured technical
interview. Questions are **not predefined** — they're generated at runtime
from the candidate's resume, the selected role, and a role-specific
knowledge base retrieved via a local vector store.

```
Resume + Role  ─▶  Resume Processing  ─▶  Context Construction  ─▶  RAG Retrieval  ─▶  Question Generation
                                                                                              │
Final Summary  ◀─  Response Handling  ◀─  Interactive Interview (adaptive)  ◀────────────────┘
```

## Architecture

```
ai-interview-system/
├── backend/                     FastAPI service — all business logic lives here
│   ├── app/
│   │   ├── main.py               App wiring, CORS, startup checks
│   │   ├── config.py             ALL configuration via environment variables
│   │   ├── database.py           SQLAlchemy engine/session (SQLite by default)
│   │   ├── models.py             ORM models: Candidate, Session, QuestionAnswer, Report
│   │   ├── schemas.py            Pydantic request/response contracts
│   │   ├── routers/
│   │   │   ├── candidates.py     Resume upload + role selection
│   │   │   └── interview.py      Question loop, answer submission, summary
│   │   └── services/
│   │       ├── resume_parser.py  PDF/text extraction + skill/tech/domain extraction
│   │       ├── rag_engine.py     Chunking + ChromaDB indexing + retrieval
│   │       ├── llm_client.py     Ollama wrapper (generation + robust JSON parsing)
│   │       └── interview_engine.py  Orchestrates context→retrieval→question→eval→report
│   ├── knowledge_base/           Role-specific corpora (plain text, one per role)
│   └── scripts/ingest_kb.py      One-time/rerunnable embedding of the knowledge base
└── frontend/                     React (Vite) app
    └── src/
        ├── pages/Home.jsx         Candidate entry: resume upload + role select
        ├── pages/Interview.jsx    Interactive Q&A loop with adaptive difficulty
        ├── pages/Summary.jsx      Final structured report + full transcript
        └── api.js                 Single place all backend calls go through
```

**Separation of concerns:** routers only handle HTTP concerns and call into
`services/`; `services/` contains all AI/ML and business logic and knows
nothing about HTTP; `models.py`/`database.py` is the only place that talks
to the database. Swapping the LLM provider or vector store means editing
exactly one file each (`llm_client.py`, `rag_engine.py`).

## How each pipeline stage is implemented

| Stage | Where | How |
|---|---|---|
| Resume Processing | `resume_parser.py` | `pypdf` text extraction + a curated skill/tech/domain taxonomy (regex matching), enriched by an LLM extraction pass when Ollama is available. Deterministic fallback means the system still works with the LLM offline. |
| Context Construction | `interview_engine.build_topic_queue` | Interleaves the role's core topics with the candidate's own extracted skills/technologies into a prioritized topic queue. |
| Knowledge Retrieval (RAG) | `rag_engine.py` | Each role's corpus is chunked by paragraph, embedded with an **offline TF-IDF vectorizer** (no external downloads/API calls needed), and stored in a per-role ChromaDB collection. Retrieval is a nearest-neighbor query per topic. |
| Question Generation | `interview_engine.generate_question` | Prompts the local Ollama model with the retrieved chunks + candidate background + target difficulty, and parses strict JSON output. Falls back to a deterministic templated question if the model is unreachable or returns malformed output. |
| Interactive Interview | `routers/interview.py` + `Interview.jsx` | Session state (topic queue, question index, running difficulty) is persisted in the `interview_sessions` table, so the flow survives page refreshes. |
| Adaptive difficulty | `interview_engine.next_difficulty` | A strong answer (≥7.5/10) escalates difficulty for the next question; a weak one (<4/10) eases off. |
| Response Handling | `question_answers` table | Every question, its grounding context, the candidate's answer, and its score/feedback are stored. |
| Final Output | `synthesize_report` + `Summary.jsx` | LLM synthesizes strengths/weaknesses/narrative from the full transcript (with a deterministic score-based fallback), persisted in `session_reports`. |

## Design decisions worth calling out

- **Offline-first AI stack.** Both the LLM (Ollama) and the embeddings
  (TF-IDF, fit per-role at ingest time) run entirely locally — no API keys,
  no external network calls at runtime. This matches the "local model"
  brief and means the system works in network-restricted environments.
- **Never a hard failure if the LLM is down.** Every LLM call site has a
  deterministic fallback (keyword extraction, templated questions,
  length-based scoring) so the *pipeline* (RAG → generation → evaluation →
  report) is always demonstrable end-to-end, with or without Ollama running.
- **Config via environment variables only** — see `backend/.env.example`.
  Nothing is hardcoded (model name, DB URL, chunk size, question count,
  adaptivity on/off, CORS origins are all tunable).

## LLM provider: Ollama (default) or Groq

The LLM is fully pluggable via `LLM_PROVIDER` in `.env` — every other module
calls `generate_text()` / `generate_json()` / `is_llm_available()` from
`llm_client.py` and doesn't know or care which provider is behind them.

**Ollama (default, fully local, no API key):**
```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

**Groq (hosted, very fast inference, needs a free API key from [console.groq.com](https://console.groq.com)):**
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...your_key...
GROQ_MODEL=llama-3.3-70b-versatile
```
No code or dependency changes needed to switch — just edit `.env` and
restart the backend. `GET /api/health` reports which provider is active and
whether it's currently reachable.

## Running it locally

### Prerequisites
- Python 3.10+
- Node 18+
- [Ollama](https://ollama.com) installed, with a model pulled, e.g.:
  ```bash
  ollama pull llama3.1
  ollama serve   # usually runs automatically after install
  ```

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate     # optional but recommended
pip install -r requirements.txt
cp .env.example .env                                  # edit if needed

python -m scripts.ingest_kb                            # embed the knowledge base (run once)
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs.
`GET /api/health` reports whether Ollama is currently reachable.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env       # points at http://localhost:8000 by default
npm run dev
```

Visit `http://localhost:5173`.

### 3. Try it
1. Upload a resume (`.pdf` or `.txt`) and pick a role.
2. Answer the generated questions — the difficulty chip adapts as you go.
3. Review the final summary: overall score, strengths, gaps, and the full
   transcript.

## Extending the system

- **Add a role:** add an entry to `ROLE_CONFIG` in `backend/app/config.py`
  and a `.txt` corpus file in `backend/knowledge_base/`, then re-run
  `python -m scripts.ingest_kb`.
- **Swap the LLM provider:** edit `backend/app/services/llm_client.py` only.
- **Swap the vector store / embeddings:** edit
  `backend/app/services/rag_engine.py` only (e.g. drop in
  `SentenceTransformerEmbeddingFunction` or a Pinecone client if you have
  GPU/network available).
- **Swap the database:** set `DATABASE_URL` to any SQLAlchemy-supported URL
  (e.g. Postgres) — no code changes needed.

## Docker & Deployment

This project is fully containerized and ready for deployment using Docker.

### Local Deployment with Docker Compose

If you have Docker installed, you can spin up the entire full-stack application locally with a single command:

```bash
docker compose up --build
```

- The frontend will be accessible at `http://localhost` (port 80).
- The backend will run at `http://localhost:8000`.
- Backend SQLite and ChromaDB data are persisted in the host directory `./backend/data`.

### Deploying to Render (Recommended PaaS)

To host your application on Render, set up the Frontend and Backend as two separate services linked to your GitHub repository:

#### 1. Backend (FastAPI Web Service)
- Create a new **Web Service** on Render.
- Set the **Root Directory** to `backend`.
- Select **Docker** as the Runtime (Render will automatically detect and build using `backend/Dockerfile`).
- Add the following **Environment Variables** in the Render settings:
  - `LLM_PROVIDER`: Set to `groq` (highly recommended for production hosting as it runs fast and doesn't crash low-memory containers).
  - `GROQ_API_KEY`: Your Groq API key.
  - `GROQ_MODEL`: `llama-3.3-70b-versatile` (or your model of choice).
- (Optional) Set up a **Persistent Disk** on Render:
  - Mount Path: `/app/data`
  - Size: 1 GB (plenty for SQLite and embeddings).
  - Add `DATABASE_URL=sqlite:////app/data/interview.db` and `CHROMA_PERSIST_DIR=/app/data/chroma_store` to environment variables so that candidate interviews and vector databases are stored on the persistent disk.

#### 2. Frontend (React Static Site)
- Create a new **Static Site** on Render.
- Set the **Root Directory** to `frontend`.
- Set **Build Command** to `npm run build`.
- Set **Publish Directory** to `dist`.
- Add an **Environment Variable**:
  - `VITE_API_BASE_URL`: Set this to your backend's Render Web Service URL (e.g. `https://your-backend-service.onrender.com`).

### CI/CD with GitHub Actions

This repository includes a GitHub Actions workflow in `.github/workflows/docker-build-push.yml`.
On every push to the `main` or `master` branch, it automatically builds the frontend and backend Docker containers and pushes them to the **GitHub Container Registry (GHCR)** under `ghcr.io/<your-username>/ai-interview-system/backend:latest` and `frontend:latest`.

# AIVOA – AI-Powered Customer Complaint Management System

A production-oriented internship assignment implementation for pharmaceutical customer complaints.

## Stack
- Frontend: React + Vite + Redux Toolkit + Inter
- Backend: Python + FastAPI + SQLAlchemy
- AI: LangGraph + Groq (`gemma2-9b-it`, configurable)
- Database: PostgreSQL (SQLite fallback for zero-setup local demo)
- Document intake: PDF/DOCX/TXT/EML + pasted complaint text

The assignment explicitly requires React/Redux, FastAPI, LangGraph, Groq, SQL, and Inter. This implementation follows that stack and the page-3 reference UI: a complaint form on the left and AI intake/copilot panel on the right. It also implements the optional AI tools listed on page 4: completeness checker, root-cause recommendation, duplicate detection, CAPA recommendation, summary, and AI risk classification.

## Features
1. Paste complaint text or upload PDF/DOCX/TXT/EML.
2. AI extraction populates the complaint form.
3. LangGraph runs a structured workflow: extraction → completeness → risk → root cause → CAPA → summary → duplicate check.
4. Risk assessment and rationale are shown in the AI Copilot.
5. Missing fields and recommended actions are visible before saving.
6. Complaints persist to SQL.
7. Saved complaints can be listed and reopened from the recent-records panel.
8. Demo mode works without a Groq key using deterministic mock analysis; set `GROQ_API_KEY` for real AI.
9. Health endpoint and Docker Compose included.

## Quick start

### Option A: Docker (recommended)
```bash
cp backend/.env.example backend/.env
# Add GROQ_API_KEY if available

docker compose up --build
```
Open http://localhost:5173

### Option B: local
Backend:
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Environment
`backend/.env`:
```env
DATABASE_URL=sqlite:///./aivoa.db
GROQ_API_KEY=
GROQ_MODEL=gemma2-9b-it
CORS_ORIGINS=http://localhost:5173
```
For PostgreSQL use e.g.:
```env
DATABASE_URL=postgresql+psycopg://aivoa:aivoa@db:5432/aivoa
```

## API
- `GET /api/health`
- `POST /api/analyze` multipart form: `complaint_text`, optional `file`
- `POST /api/complaints` save analyzed complaint
- `GET /api/complaints`
- `GET /api/complaints/{id}`

OpenAPI: http://localhost:8000/docs

## Demo complaint
A realistic sample is included at `sample_data/sample_complaint.txt`.

## Architecture
```text
React UI
  ↓ Redux Toolkit
FastAPI
  ├── document parser
  ├── LangGraph workflow
  │    ├── extract
  │    ├── completeness
  │    ├── risk
  │    ├── root cause
  │    ├── CAPA
  │    ├── summary
  │    └── duplicate
  └── SQLAlchemy → PostgreSQL/SQLite
```

## Current Groq model note
The assignment names `gemma2-9b-it`. Groq currently lists that model in its deprecation documentation with an October 8, 2025 shutdown date, while its current production model list recommends models such as `llama-3.3-70b-versatile`. The app therefore keeps the assignment model configurable but automatically retries with `llama-3.3-70b-versatile` if the configured model is unavailable.

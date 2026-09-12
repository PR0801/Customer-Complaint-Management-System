from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .config import settings
from .db import Base, engine, get_db
from .models import Complaint
from .parser import extract_file_text
from .schemas import AnalysisResponse, ComplaintOut, ComplaintData, AIAnalysis
from .ai import analyze

Base.metadata.create_all(bind=engine)
app = FastAPI(title="AIVOA Complaint Management API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
def health(): return {"status":"ok", "ai_mode":"groq" if settings.groq_api_key else "demo"}

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_complaint(complaint_text: str = Form(""), file: UploadFile | None = File(None), db: Session = Depends(get_db)):
    text = complaint_text.strip()
    if file:
        data = await file.read()
        try: text = (text + "\n" + extract_file_text(file.filename or "upload.txt", data)).strip()
        except ValueError as e: raise HTTPException(400, str(e))
    if not text: raise HTTPException(400, "Paste complaint text or upload a complaint document.")
    history = [{"id": row.id, "complaint": row.complaint} for row in db.query(Complaint).order_by(Complaint.created_at.desc()).limit(100).all()]
    complaint, analysis = analyze(text, history)
    return {"complaint": complaint, "ai_analysis": analysis, "source_text": text}

@app.post("/api/complaints", response_model=ComplaintOut)
def save(payload: AnalysisResponse, db: Session = Depends(get_db)):
    row = Complaint(complaint=payload.complaint.model_dump(), ai_analysis=payload.ai_analysis.model_dump(), source_text=payload.source_text)
    db.add(row); db.commit(); db.refresh(row)
    return row

@app.get("/api/complaints", response_model=list[ComplaintOut])
def list_complaints(db: Session = Depends(get_db)):
    return db.query(Complaint).order_by(Complaint.created_at.desc()).all()

@app.get("/api/complaints/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    row = db.get(Complaint, complaint_id)
    if not row: raise HTTPException(404, "Complaint not found")
    return row

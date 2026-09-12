from pathlib import Path
from io import BytesIO
from pypdf import PdfReader
from docx import Document

ALLOWED = {".pdf", ".docx", ".txt", ".eml"}

def extract_file_text(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise ValueError("Unsupported file type. Use PDF, DOCX, TXT or EML.")
    if ext == ".pdf":
        reader = PdfReader(BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if ext == ".docx":
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    return data.decode("utf-8", errors="ignore")

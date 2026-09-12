from datetime import datetime
from sqlalchemy import DateTime, Integer, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class Complaint(Base):
    __tablename__ = "complaints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint: Mapped[dict] = mapped_column(JSON)
    ai_analysis: Mapped[dict] = mapped_column(JSON)
    source_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

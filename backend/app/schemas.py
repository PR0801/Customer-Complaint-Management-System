from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class ComplaintData(BaseModel):
    complaint_source: str = "Customer Email"
    customer_name: str = ""
    product_name: str = ""
    product_strength_grade: str = ""
    batch_lot_number: str = ""
    manufacturing_date: str = ""
    expiry_date: str = ""
    quantity_affected: str = ""
    complaint_type: str = ""
    complaint_date: str = ""
    detailed_description: str = ""
    initial_severity: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    priority: Literal["Low", "Medium", "High", "Urgent"] = "Medium"

class AIAnalysis(BaseModel):
    completeness_score: int = Field(ge=0, le=100)
    missing_fields: list[str] = []
    risk_level: Literal["Low", "Medium", "High", "Critical"] = "Medium"
    risk_rationale: str = ""
    root_cause_recommendations: list[str] = []
    capa_recommendations: list[str] = []
    complaint_summary: str = ""
    duplicate_likelihood: Literal["Low", "Medium", "High"] = "Low"
    duplicate_reason: str = ""
    confidence: int = Field(ge=0, le=100, default=80)

class AnalysisResponse(BaseModel):
    complaint: ComplaintData
    ai_analysis: AIAnalysis
    source_text: str

class ComplaintOut(BaseModel):
    id: int
    complaint: ComplaintData
    ai_analysis: AIAnalysis
    source_text: str
    created_at: datetime

    class Config:
        from_attributes = True

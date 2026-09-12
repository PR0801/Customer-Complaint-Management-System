import json, re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from pydantic import ValidationError
from .schemas import ComplaintData, AIAnalysis
from .config import settings

class GraphState(TypedDict, total=False):
    source_text: str
    complaint: dict
    analysis: dict
    history: list[dict]

SYSTEM = """You are a pharmaceutical Quality Management System complaint intake assistant. Extract only information supported by the supplied complaint. Never invent batch numbers, dates, customer names or medical facts. Return strict JSON with keys complaint and analysis. complaint must contain: complaint_source, customer_name, product_name, product_strength_grade, batch_lot_number, manufacturing_date, expiry_date, quantity_affected, complaint_type, complaint_date, detailed_description, initial_severity, priority. analysis must contain: completeness_score, missing_fields, risk_level, risk_rationale, root_cause_recommendations, capa_recommendations, complaint_summary, duplicate_likelihood, duplicate_reason, confidence. Severity/risk should reflect potential product quality, patient impact and regulatory significance. Use empty strings when unknown."""

FIELDS = ["customer_name","product_name","product_strength_grade","batch_lot_number","manufacturing_date","expiry_date","quantity_affected","complaint_type","complaint_date","detailed_description"]

def mock_extract(text: str):
    def find(pattern):
        m = re.search(pattern, text, re.I)
        return m.group(1).strip() if m else ""
    complaint = ComplaintData(
        complaint_source="Customer Email" if "email" in text.lower() else "Customer Complaint",
        customer_name=find(r"(?:customer|from)\s*[:\-]\s*([^\n]+)"),
        product_name=find(r"product\s*[:\-]\s*([^\n]+)"),
        product_strength_grade=find(r"(?:strength|grade)\s*[:\-]\s*([^\n]+)"),
        batch_lot_number=find(r"batch(?:/lot| lot)?\s*(?:number)?\s*[:\-]\s*([^\n]+)"),
        manufacturing_date=find(r"manufactur(?:ing|ed)\s*date\s*[:\-]\s*([^\n]+)"),
        expiry_date=find(r"expir(?:y|ation)\s*date\s*[:\-]\s*([^\n]+)"),
        quantity_affected=find(r"quantity\s*(?:affected)?\s*[:\-]\s*([^\n]+)"),
        complaint_type=find(r"complaint\s*type\s*[:\-]\s*([^\n]+)"),
        complaint_date=find(r"complaint\s*date\s*[:\-]\s*([^\n]+)"),
        detailed_description=find(r"(?:description|details?)\s*[:\-]\s*([\s\S]+)") or text[:1000],
        initial_severity="High" if re.search(r"patient|adverse|contamination|wrong product|serious", text, re.I) else "Medium",
        priority="High" if re.search(r"patient|adverse|contamination|wrong product|serious", text, re.I) else "Medium",
    )
    missing = [f.replace("_", " ").title() for f in FIELDS if not getattr(complaint, f)]
    score = round((len(FIELDS)-len(missing))/len(FIELDS)*100)
    risk = "High" if complaint.initial_severity == "High" else "Medium"
    analysis = AIAnalysis(
        completeness_score=score, missing_fields=missing, risk_level=risk,
        risk_rationale="Potential product-quality impact requires QA review; patient-impact language should be verified." if risk == "High" else "No critical patient-impact signal was identified in the available text; QA should validate the classification.",
        root_cause_recommendations=["Review batch manufacturing and packaging records", "Check retained samples and analytical results", "Review deviations, OOS/OOT and trend history"],
        capa_recommendations=["Open investigation with documented evidence review", "Assess affected lots and distribution scope", "Define corrective/preventive actions after confirmed root cause"],
        complaint_summary=text[:500].strip(), duplicate_likelihood="Low", duplicate_reason="No complaint history was supplied to the intake workflow.", confidence=65)
    return complaint.model_dump(), analysis.model_dump()

def call_llm(text: str):
    if not settings.groq_api_key:
        return mock_extract(text)
    from groq import Groq
    client = Groq(api_key=settings.groq_api_key)
    models = [settings.groq_model]
    if "llama-3.3-70b-versatile" not in models:
        models.append("llama-3.3-70b-versatile")
    last_error = None
    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type":"json_object"},
                messages=[{"role":"system","content":SYSTEM},{"role":"user","content":text[:15000]}],
            )
            raw = json.loads(response.choices[0].message.content)
            complaint = ComplaintData.model_validate(raw.get("complaint", {}))
            analysis = AIAnalysis.model_validate(raw.get("analysis", {}))
            return complaint.model_dump(), analysis.model_dump()
        except Exception as exc:
            last_error = exc
    raise last_error

def extract_node(state: GraphState):
    complaint, analysis = call_llm(state["source_text"])
    return {"complaint": complaint, "analysis": analysis}

def completeness_node(state: GraphState):
    c = state["complaint"]
    missing = [f.replace("_", " ").title() for f in FIELDS if not c.get(f)]
    a = dict(state["analysis"])
    a["missing_fields"] = missing
    a["completeness_score"] = round((len(FIELDS)-len(missing))/len(FIELDS)*100)
    return {"analysis": a}

def risk_node(state: GraphState):
    c, a = state["complaint"], dict(state["analysis"])
    text = (c.get("detailed_description", "") + " " + c.get("complaint_type", "")).lower()
    if any(x in text for x in ["death", "hospital", "serious adverse", "contamination", "wrong strength"]):
        a["risk_level"] = "Critical"
    elif any(x in text for x in ["adverse", "patient", "contamination", "mix-up", "wrong product"]):
        a["risk_level"] = "High"
    return {"analysis": a}

def recommendation_node(state: GraphState):
    a = dict(state["analysis"])
    if not a.get("root_cause_recommendations"):
        a["root_cause_recommendations"] = ["Review batch records and deviations", "Inspect retained sample and analytical results", "Trend similar complaints"]
    if not a.get("capa_recommendations"):
        a["capa_recommendations"] = ["Open documented investigation", "Assess scope and distribution impact", "Implement CAPA based on verified root cause"]
    if not a.get("complaint_summary"):
        a["complaint_summary"] = state["source_text"][:500]
    return {"analysis": a}

def duplicate_node(state: GraphState):
    a = dict(state["analysis"])
    history = state.get("history", [])
    current = state["complaint"]
    best = 0.0
    best_match = None
    current_text = (current.get("detailed_description", "") or "").lower()
    current_batch = (current.get("batch_lot_number", "") or "").strip().lower()
    current_product = (current.get("product_name", "") or "").strip().lower()
    for item in history:
        old = item.get("complaint", {})
        score = 0.0
        old_batch = (old.get("batch_lot_number", "") or "").strip().lower()
        old_product = (old.get("product_name", "") or "").strip().lower()
        old_text = (old.get("detailed_description", "") or "").lower()
        if current_batch and old_batch and current_batch == old_batch:
            score += 0.55
        if current_product and old_product and current_product == old_product:
            score += 0.25
        if current_text and old_text:
            a_words = set(re.findall(r"[a-z0-9]+", current_text))
            b_words = set(re.findall(r"[a-z0-9]+", old_text))
            if a_words and b_words:
                score += 0.20 * (len(a_words & b_words) / max(1, len(a_words | b_words)))
        if score > best:
            best, best_match = score, item
    if best >= 0.75:
        a["duplicate_likelihood"] = "High"
    elif best >= 0.45:
        a["duplicate_likelihood"] = "Medium"
    else:
        a["duplicate_likelihood"] = "Low"
    if best_match:
        a["duplicate_reason"] = f"Closest saved complaint is #{best_match.get('id')} with a similarity score of {round(best * 100)}%."
    else:
        a["duplicate_reason"] = "No sufficiently similar saved complaint was found."
    return {"analysis": a}

def build_graph():
    g = StateGraph(GraphState)
    g.add_node("extract", extract_node)
    g.add_node("completeness", completeness_node)
    g.add_node("risk", risk_node)
    g.add_node("recommendations", recommendation_node)
    g.add_node("duplicate", duplicate_node)
    g.add_edge(START, "extract")
    g.add_edge("extract", "completeness")
    g.add_edge("completeness", "risk")
    g.add_edge("risk", "recommendations")
    g.add_edge("recommendations", "duplicate")
    g.add_edge("duplicate", END)
    return g.compile()

graph = build_graph()

def analyze(text: str, history: list[dict] | None = None):
    try:
        result = graph.invoke({"source_text": text, "history": history or []})
        return ComplaintData.model_validate(result["complaint"]), AIAnalysis.model_validate(result["analysis"])
    except Exception as e:
        if settings.groq_api_key:
            raise
        c, a = mock_extract(text)
        return ComplaintData.model_validate(c), AIAnalysis.model_validate(a)

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import MutualFundScheme, SchemeAnalytics
from app.engine.recommendations import get_top_funds
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    investment_amount: Optional[float] = None
    investment_mode: Optional[str] = None
    horizon_years: Optional[int] = None
    risk_appetite: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    recommendations: List[dict] = []
    follow_ups: List[str] = []

SYSTEM_PROMPT = """You are an expert Indian mutual fund advisor for India Mutual Fund Finder.
Rules:
- Only recommend Direct Growth plans.
- Explain OCS (Objective Composite Score) components: Rolling Returns (25%), Risk-Adjusted (25%), Consistency (20%), Fundamentals (15%), Trend (15%).
- Adjust advice for SIP vs Lump Sum (rupee cost averaging vs valuation penalty).
- Enforce AMC cap 33% and category diversification.
- Always cite category, expense ratio, and risk.
- If user asks about historic performance, reference CAGR, Sharpe, Sortino, downside capture from analytics.
- Past returns are not a forecast: never promise or imply future returns, and never call an equity fund "safe" or "low risk". Say when expense ratio is unavailable.
- Never hallucinate ISINs or NAVs; use only provided fund context.
- Be concise, friendly, and actionable.
"""

def build_fund_context(db: Session) -> str:
    # Only holistic funds with real 5Y analytics, sorted by Sharpe for low-risk credibility
    rows = db.query(MutualFundScheme, SchemeAnalytics).join(SchemeAnalytics, MutualFundScheme.scheme_id == SchemeAnalytics.scheme_id).filter(MutualFundScheme.is_active == True, SchemeAnalytics.time_horizon_years==5, SchemeAnalytics.cagr > 0).order_by(SchemeAnalytics.sharpe_ratio.desc()).limit(12).all()
    if not rows:
        rows = db.query(MutualFundScheme, SchemeAnalytics).join(SchemeAnalytics, MutualFundScheme.scheme_id == SchemeAnalytics.scheme_id).filter(SchemeAnalytics.time_horizon_years==5).order_by(SchemeAnalytics.cagr.desc()).limit(12).all()
    lines = []
    for s, a in rows:
        lines.append(f"- {s.scheme_name} ({s.category}, {s.amc_name}, expense {("%.2f%%" % float(s.ter_pct)) if s.ter_pct is not None else "n/a"}, 5Y CAGR {float(a.cagr):.1f}%, Sharpe {float(a.sharpe_ratio):.2f}, Sortino {float(a.sortino_ratio):.2f})")
    if not lines:
        # fallback to top 8 Direct Growth
        for s in db.query(MutualFundScheme).filter(MutualFundScheme.plan_type=="Direct").limit(8).all():
            lines.append(f"- {s.scheme_name} ({s.category}, {s.amc_name})")
    return "\n".join(lines)

def heuristic_intent(message: str) -> dict:
    m = message.lower()
    intent = {}
    if "sip" in m:
        intent["investment_mode"] = "SIP"
    elif "lump" in m:
        intent["investment_mode"] = "Lump Sum"
    if "small" in m:
        intent["category"] = "Small Cap"
    elif "mid" in m:
        intent["category"] = "Mid Cap"
    elif "large" in m:
        intent["category"] = "Large Cap"
    elif "flexi" in m:
        intent["category"] = "Flexi Cap"
    elif "hybrid" in m:
        intent["category"] = "Hybrid"
    if "low risk" in m or "conservative" in m:
        intent["risk_appetite"] = "low"
    elif "high risk" in m or "aggressive" in m:
        intent["risk_appetite"] = "high"
    elif "medium" in m or "moderate" in m:
        intent["risk_appetite"] = "medium"
    # amount
    import re
    amt = re.search(r"(\d+)\s*(lakh|lakhs|k|000)", m)
    if amt:
        try:
            val = amt.group(0)
            if "lakh" in val:
                num = int(re.search(r"\d+", val).group()) * 100000
                intent["investment_amount"] = num
        except: pass
    return intent

async def call_llm(system: str, user: str, fund_context: str, history: List[ChatMessage]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            import httpx
            msgs = [{"role": "system", "content": system + "\n\nAvailable funds:\n" + fund_context}]
            for h in history[-6:]:
                msgs.append({"role": h.role, "content": h.content})
            msgs.append({"role": "user", "content": user})
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"model": os.getenv("OPENAI_MODEL","gpt-4o-mini"), "messages": msgs, "temperature": 0.3, "max_tokens": 800})
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}, falling back to heuristic")
    # heuristic fallback
    return heuristic_reply(user, fund_context)

def heuristic_reply(user: str, fund_context: str) -> str:
    return (
        f"Based on your query: \"{user}\"\n\n"
        f"Here is what I found from our OCS-ranked universe (Direct Growth only):\n{fund_context}\n\n"
        "How to choose:\n"
        "• **SIP** benefits from volatility + high alpha (rupee cost averaging); we up-weight consistency & Sortino.\n"
        "• **Lump Sum** penalizes overvalued portfolios (P/E >1.5x median) and rewards downside capture ≤85.\n"
        "• Check the **Recommendations** tab with your amount/horizon/risk to see the live OCS-ranked list and overlap matrix.\n\n"
        "Tell me your amount, horizon (1/3/5/10y), risk (low/medium/high), and preferred category, and I'll rank the best funds for you."
    )

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    intent = heuristic_intent(req.message)
    amount = req.investment_amount or intent.get("investment_amount") or 100000
    mode = req.investment_mode or intent.get("investment_mode") or "Lump Sum"
    horizon = req.horizon_years or 5
    risk = req.risk_appetite or intent.get("risk_appetite") or "medium"
    category = intent.get("category")

    # Get recommendations to show alongside chat
    try:
        recs = get_top_funds(investment_amount=float(amount), investment_mode=mode, horizon_years=int(horizon), risk_appetite=risk, category=category, db=db)[:3]
    except Exception as e:
        logger.error(f"rec error {e}")
        recs = []

    fund_context = build_fund_context(db)
    reply = await call_llm(SYSTEM_PROMPT, req.message, fund_context, req.history)

    follow_ups = [
        "What's your investment amount and horizon?",
        "Do you prefer SIP or Lump Sum?",
        "Which category: Large/Mid/Small/Flexi/Hybrid?",
    ]
    return ChatResponse(reply=reply, recommendations=recs, follow_ups=follow_ups)

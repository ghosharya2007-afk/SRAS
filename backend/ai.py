"""
SRAS AI Routes
==============
POST /api/ai/analyze         — Analyze request text with Gemini
POST /api/ai/sitrep          — Generate situation report
GET  /api/ai/forecast/{zone} — Get demand forecast for a zone
"""

from fastapi import APIRouter

from models.schemas import AnalyzeRequestBody
from services.gemini_service import analyze_request, generate_sitrep, forecast_zone_demand

router = APIRouter(prefix="/api/ai", tags=["AI / Gemini"])


@router.post("/analyze")
async def analyze_text(body: AnalyzeRequestBody):
    """
    Analyze emergency text using Gemini AI.
    Returns type, severity, urgency keywords, and confidence score.
    """
    result = await analyze_request(body.text)
    return result


@router.post("/sitrep")
async def get_sitrep():
    """
    Generate an AI situation report (SITREP) from current operational data.
    Aggregates all request/provider stats and feeds to Gemini.
    """
    from routes.requests import get_requests_store
    from routes.dispatch import get_providers_store, get_dispatches_store

    requests_store = get_requests_store()
    providers_store = get_providers_store()
    dispatches_store = get_dispatches_store()

    all_requests = list(requests_store.values())
    all_providers = list(providers_store.values())
    all_dispatches = list(dispatches_store.values())

    pending = [r for r in all_requests if r["status"] == "pending"]
    resolved = [r for r in all_requests if r["status"] == "resolved"]

    pending_by_type = {}
    for r in pending:
        t = r.get("type", "other")
        pending_by_type[t] = pending_by_type.get(t, 0) + 1

    stats = {
        "total_requests": len(all_requests),
        "pending_count": len(pending),
        "pending_by_type": pending_by_type,
        "resolved_count": len(resolved),
        "active_providers": len([p for p in all_providers if p["status"] == "available"]),
        "busy_providers": len([p for p in all_providers if p["status"] == "busy"]),
        "total_dispatches": len(all_dispatches),
        "completed_dispatches": len([d for d in all_dispatches if d["status"] == "completed"]),
        "highest_priority_pending": max(
            (r.get("priority_score", 0) for r in pending), default=0
        ),
    }

    result = await generate_sitrep(stats)
    return result


@router.get("/forecast/{zone}")
async def get_forecast(zone: str):
    """
    Get demand forecast for a specific zone using Gemini.
    Uses last 7 days of simulated historical data.
    """
    from routes.requests import get_requests_store
    requests_store = get_requests_store()

    # Build simplified historical data (in production, query Firestore)
    all_requests = list(requests_store.values())
    zone_requests = [
        r for r in all_requests
        if r.get("location", {}).get("zone", "").lower() == zone.lower()
    ]

    # Simulated 7-day history (in production, aggregate from real data)
    import random
    historical = []
    for day in range(7, 0, -1):
        historical.append({
            "day": f"Day -{day}",
            "food": random.randint(2, 15),
            "medical": random.randint(1, 8),
            "shelter": random.randint(0, 5),
        })

    result = await forecast_zone_demand(zone, historical, weather="partly cloudy")
    return result

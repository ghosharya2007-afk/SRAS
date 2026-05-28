"""
SRAS — Smart Resource Allocation System
========================================
FastAPI Backend Application

Endpoints:
  /api/requests     — Emergency request management
  /api/providers    — Resource provider management
  /api/dispatch     — Dispatch matching engine
  /api/ai           — Gemini AI integration
  /api/stats        — Dashboard metrics
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.requests import router as requests_router
from routes.dispatch import router as dispatch_router
from routes.ai import router as ai_router
from routes.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    print("[SRAS] Backend starting...")
    print(f"   Gemini API: {'[OK] Configured' if os.environ.get('GEMINI_API_KEY') else '[WARN] Not set'}")
    yield
    print("[SRAS] Backend shutting down...")


app = FastAPI(
    title="SRAS — Smart Resource Allocation System",
    description="AI-powered emergency resource allocation and dispatch engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for hackathon demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Mount Routers ────────────────────────────────
app.include_router(requests_router)
app.include_router(dispatch_router)
app.include_router(ai_router)
app.include_router(stats_router)


# ─── Health Check ─────────────────────────────────
@app.get("/", tags=["Health"])
async def health_check():
    return {
        "service": "SRAS API",
        "status": "healthy",
        "version": "1.0.0",
        "gemini": "configured" if os.environ.get("GEMINI_API_KEY") else "not_configured",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


# ─── Seed Demo Data Endpoint ─────────────────────
@app.post("/api/seed", tags=["Dev"])
async def seed_demo_data():
    """
    Seed the database with sample requests and providers for demo.
    """
    from routes.requests import requests_db
    from routes.dispatch import providers_db
    from datetime import datetime, timezone, timedelta
    from services.priority_engine import compute_priority_score
    import uuid

    now = datetime.now(timezone.utc)

    # Sample providers
    sample_providers = [
        {
            "id": "prov-001",
            "name": "Red Cross Unit 3",
            "organization": "Red Cross",
            "capability_types": ["food", "medical", "shelter"],
            "location": {"lat": 12.9716, "lng": 77.5946, "address": "Bangalore Central", "zone": "Zone-A"},
            "status": "available",
            "reliability_score": 8.5,
            "current_assignment": None,
            "registered_at": now.isoformat(),
            "provider_uid": "rc-001",
        },
        {
            "id": "prov-002",
            "name": "Community Kitchen NGO",
            "organization": "Food For All",
            "capability_types": ["food"],
            "location": {"lat": 12.9352, "lng": 77.6245, "address": "Koramangala", "zone": "Zone-B"},
            "status": "available",
            "reliability_score": 7.0,
            "current_assignment": None,
            "registered_at": now.isoformat(),
            "provider_uid": "ck-001",
        },
        {
            "id": "prov-003",
            "name": "Emergency Medical Team",
            "organization": "City Hospital",
            "capability_types": ["medical", "critical"],
            "location": {"lat": 12.9850, "lng": 77.5533, "address": "Rajajinagar", "zone": "Zone-C"},
            "status": "available",
            "reliability_score": 9.2,
            "current_assignment": None,
            "registered_at": now.isoformat(),
            "provider_uid": "emt-001",
        },
    ]

    # Sample requests (with different ages for priority diversity)
    sample_requests = [
        {
            "id": "req-001",
            "type": "critical",
            "description": "Elderly person collapsed, not breathing, needs immediate CPR and ambulance",
            "severity": 10,
            "location": {"lat": 12.9780, "lng": 77.5900, "address": "MG Road", "zone": "Zone-A"},
            "status": "pending",
            "created_at": (now - timedelta(minutes=15)).isoformat(),
            "updated_at": now.isoformat(),
            "assigned_to": None,
            "is_verified": True,
            "requester_id": "user-001",
            "gemini_analysis": {"type": "critical", "severity": 10, "confidence": 0.97, "urgency_keywords": ["collapsed", "not breathing", "CPR"], "reasoning": "Life-threatening emergency"},
        },
        {
            "id": "req-002",
            "type": "food",
            "description": "Family of 5 hasn't eaten in 2 days, children are weak and dehydrated",
            "severity": 8,
            "location": {"lat": 12.9600, "lng": 77.5700, "address": "Chickpet", "zone": "Zone-A"},
            "status": "pending",
            "created_at": (now - timedelta(hours=3)).isoformat(),
            "updated_at": now.isoformat(),
            "assigned_to": None,
            "is_verified": False,
            "requester_id": "user-002",
            "gemini_analysis": {"type": "food", "severity": 8, "confidence": 0.92, "urgency_keywords": ["children", "2 days", "dehydrated"], "reasoning": "High urgency food need with vulnerable children"},
        },
        {
            "id": "req-003",
            "type": "shelter",
            "description": "Displaced family needs temporary shelter, currently sleeping outdoors",
            "severity": 6,
            "location": {"lat": 12.9400, "lng": 77.6100, "address": "BTM Layout", "zone": "Zone-B"},
            "status": "pending",
            "created_at": (now - timedelta(hours=8)).isoformat(),
            "updated_at": now.isoformat(),
            "assigned_to": None,
            "is_verified": True,
            "requester_id": "user-003",
            "gemini_analysis": {"type": "shelter", "severity": 6, "confidence": 0.88, "urgency_keywords": ["displaced", "outdoors"], "reasoning": "Moderate shelter need"},
        },
        {
            "id": "req-004",
            "type": "medical",
            "description": "Child has high fever for 3 days, no access to medicine",
            "severity": 7,
            "location": {"lat": 12.9500, "lng": 77.5800, "address": "Jayanagar", "zone": "Zone-B"},
            "status": "pending",
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "updated_at": now.isoformat(),
            "assigned_to": None,
            "is_verified": False,
            "requester_id": "user-004",
            "gemini_analysis": {"type": "medical", "severity": 7, "confidence": 0.90, "urgency_keywords": ["child", "fever", "3 days"], "reasoning": "Pediatric medical need"},
        },
        {
            "id": "req-005",
            "type": "food",
            "description": "Running low on water supply, need clean drinking water for community",
            "severity": 5,
            "location": {"lat": 12.9900, "lng": 77.5600, "address": "Yeshwantpur", "zone": "Zone-C"},
            "status": "pending",
            "created_at": (now - timedelta(minutes=30)).isoformat(),
            "updated_at": now.isoformat(),
            "assigned_to": None,
            "is_verified": True,
            "requester_id": "user-005",
            "gemini_analysis": {"type": "food", "severity": 5, "confidence": 0.85, "urgency_keywords": ["water", "community"], "reasoning": "Community water supply need"},
        },
    ]

    # Compute priority scores
    for req in sample_requests:
        created = datetime.fromisoformat(req["created_at"].replace("Z", "+00:00"))
        minutes_waiting = (now - created).total_seconds() / 60
        score_info = compute_priority_score(
            request_type=req["type"],
            severity=req["severity"],
            minutes_waiting=minutes_waiting,
            is_verified=req["is_verified"],
        )
        req["priority_score"] = score_info["total"]
        req["score_breakdown"] = score_info

    # Load into stores
    for p in sample_providers:
        providers_db[p["id"]] = p
    for r in sample_requests:
        requests_db[r["id"]] = r

    return {
        "seeded": True,
        "providers": len(sample_providers),
        "requests": len(sample_requests),
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

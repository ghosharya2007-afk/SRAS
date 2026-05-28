"""
SRAS Dispatch Routes
====================
POST /api/dispatch/run              — Run greedy dispatch matching
POST /api/dispatch/{id}/accept      — Provider accepts assignment
POST /api/dispatch/{id}/complete    — Provider completes delivery
GET  /api/providers                 — List all providers
POST /api/providers                 — Register a provider
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from models.schemas import ProviderRegistrationBody
from services.matching_engine import run_greedy_dispatch, update_reliability_score

router = APIRouter(tags=["Dispatch"])

# In-memory stores
providers_db: dict = {}
dispatches_db: dict = {}


@router.post("/api/providers")
async def register_provider(body: ProviderRegistrationBody):
    """Register a new resource provider."""
    provider_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)

    provider_doc = {
        "id": provider_id,
        "name": body.name,
        "organization": body.organization,
        "capability_types": body.capability_types,
        "location": body.location.model_dump(),
        "status": "available",
        "reliability_score": 5.0,
        "current_assignment": None,
        "registered_at": now.isoformat(),
        "provider_uid": body.provider_uid,
    }

    providers_db[provider_id] = provider_doc
    return provider_doc


@router.get("/api/providers")
async def list_providers():
    """List all registered providers."""
    return list(providers_db.values())


@router.post("/api/dispatch/run")
async def run_dispatch():
    """
    Run greedy matching algorithm.
    Fetches all pending requests and available providers,
    runs matching, creates dispatch records.
    """
    from routes.requests import get_requests_store
    requests_store = get_requests_store()

    pending = [
        r for r in requests_store.values() if r["status"] == "pending"
    ]
    available = [
        p for p in providers_db.values() if p["status"] == "available"
    ]

    if not pending:
        return {"matched": 0, "unmatched": 0, "assignments": [], "message": "No pending requests"}

    if not available:
        return {"matched": 0, "unmatched": len(pending), "assignments": [], "message": "No available providers"}

    # Run greedy dispatch
    result = run_greedy_dispatch(pending, available)

    now = datetime.now(timezone.utc)

    # Create dispatch records and update statuses
    for assignment in result["assignments"]:
        dispatch_id = str(uuid.uuid4())[:8]
        req_id = assignment["request_id"]
        prov_id = assignment["provider_id"]

        dispatch_doc = {
            "id": dispatch_id,
            "request_id": req_id,
            "provider_id": prov_id,
            "dispatched_at": now.isoformat(),
            "accepted_at": None,
            "completed_at": None,
            "status": "pending_acceptance",
            "match_score": assignment["match_score"],
            "distance_km": assignment["distance_km"],
        }
        dispatches_db[dispatch_id] = dispatch_doc

        # Update request status
        if req_id in requests_store:
            requests_store[req_id]["status"] = "assigned"
            requests_store[req_id]["assigned_to"] = prov_id
            requests_store[req_id]["updated_at"] = now.isoformat()

        # Update provider status
        if prov_id in providers_db:
            providers_db[prov_id]["status"] = "busy"
            providers_db[prov_id]["current_assignment"] = req_id

        assignment["dispatch_id"] = dispatch_id

    return {
        "matched": result["matched_count"],
        "unmatched": result["unmatched_count"],
        "assignments": result["assignments"],
    }


@router.post("/api/dispatch/{dispatch_id}/accept")
async def accept_dispatch(dispatch_id: str):
    """Provider accepts a dispatch assignment."""
    if dispatch_id not in dispatches_db:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    dispatch = dispatches_db[dispatch_id]
    if dispatch["status"] != "pending_acceptance":
        raise HTTPException(status_code=400, detail=f"Cannot accept dispatch in status: {dispatch['status']}")

    now = datetime.now(timezone.utc)
    dispatch["accepted_at"] = now.isoformat()
    dispatch["status"] = "accepted"

    # Update request status
    from routes.requests import get_requests_store
    requests_store = get_requests_store()
    req_id = dispatch["request_id"]
    if req_id in requests_store:
        requests_store[req_id]["status"] = "in_progress"
        requests_store[req_id]["updated_at"] = now.isoformat()

    return dispatch


@router.post("/api/dispatch/{dispatch_id}/complete")
async def complete_dispatch(dispatch_id: str):
    """Provider marks delivery as complete. Updates reliability score."""
    if dispatch_id not in dispatches_db:
        raise HTTPException(status_code=404, detail="Dispatch not found")

    dispatch = dispatches_db[dispatch_id]
    if dispatch["status"] not in ("accepted", "pending_acceptance"):
        raise HTTPException(status_code=400, detail=f"Cannot complete dispatch in status: {dispatch['status']}")

    now = datetime.now(timezone.utc)
    dispatch["completed_at"] = now.isoformat()
    dispatch["status"] = "completed"

    # Calculate response time
    dispatched = datetime.fromisoformat(dispatch["dispatched_at"])
    dispatch["response_time_minutes"] = round((now - dispatched).total_seconds() / 60, 1)

    # Update request status
    from routes.requests import get_requests_store
    requests_store = get_requests_store()
    req_id = dispatch["request_id"]
    if req_id in requests_store:
        requests_store[req_id]["status"] = "resolved"
        requests_store[req_id]["updated_at"] = now.isoformat()

    # Update provider reliability (+0.5 for success)
    prov_id = dispatch["provider_id"]
    if prov_id in providers_db:
        providers_db[prov_id]["status"] = "available"
        providers_db[prov_id]["current_assignment"] = None
        providers_db[prov_id]["reliability_score"] = update_reliability_score(
            providers_db[prov_id]["reliability_score"], success=True
        )

    return dispatch


@router.get("/api/dispatches")
async def list_dispatches():
    """List all dispatch records."""
    return list(dispatches_db.values())


def get_providers_store():
    return providers_db

def get_dispatches_store():
    return dispatches_db

"""
SRAS Request Routes
===================
POST /api/requests       — Create new emergency request
GET  /api/requests       — List all requests (filtered)
GET  /api/requests/{id}  — Get single request
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models.schemas import CreateRequestBody, RequestResponse
from services.priority_engine import compute_priority_score
from services.gemini_service import analyze_request

router = APIRouter(prefix="/api/requests", tags=["Requests"])

# In-memory store (replace with Firestore in production)
requests_db: dict = {}


@router.post("", response_model=RequestResponse)
async def create_request(body: CreateRequestBody):
    """
    Create a new emergency request.
    1. Calls Gemini to auto-classify the description
    2. Overrides severity if Gemini confidence > 0.85
    3. Computes initial priority score
    4. Returns request with queue position
    """
    request_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)

    # Step 1: Gemini analysis
    gemini_result = await analyze_request(body.description)

    # Step 2: Override severity if AI is confident
    final_severity = body.severity
    final_type = body.type
    if gemini_result.get("confidence", 0) > 0.85:
        final_severity = gemini_result.get("severity", body.severity)
        final_type = gemini_result.get("type", body.type)

    # Step 3: Compute priority
    score_info = compute_priority_score(
        request_type=final_type,
        severity=final_severity,
        minutes_waiting=0,
        is_verified=body.is_verified,
    )

    # Build request document
    request_doc = {
        "id": request_id,
        "type": final_type,
        "description": body.description,
        "severity": final_severity,
        "location": body.location.model_dump(),
        "status": "pending",
        "priority_score": score_info["total"],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "assigned_to": None,
        "gemini_analysis": gemini_result,
        "is_verified": body.is_verified,
        "requester_id": body.requester_id,
        "score_breakdown": score_info,
    }

    requests_db[request_id] = request_doc

    # Calculate queue position
    all_pending = [
        r for r in requests_db.values() if r["status"] == "pending"
    ]
    all_scores = sorted(
        [r["priority_score"] for r in all_pending], reverse=True
    )
    queue_pos = all_scores.index(score_info["total"]) + 1 if score_info["total"] in all_scores else len(all_scores)

    return RequestResponse(
        id=request_id,
        type=final_type,
        description=body.description,
        severity=final_severity,
        location=body.location.model_dump(),
        status="pending",
        priority_score=score_info["total"],
        queue_position=queue_pos,
        gemini_analysis=gemini_result,
        created_at=now.isoformat(),
        assigned_to=None,
        is_verified=body.is_verified,
        score_breakdown=score_info,
    )


@router.get("")
async def list_requests(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """List requests, sorted by priority_score descending."""
    results = list(requests_db.values())

    if status:
        results = [r for r in results if r["status"] == status]
    if type:
        results = [r for r in results if r["type"] == type]
    if zone:
        results = [r for r in results if r.get("location", {}).get("zone") == zone]

    # Sort by priority descending
    results.sort(key=lambda r: r.get("priority_score", 0), reverse=True)

    # Add queue positions
    for i, r in enumerate(results):
        r["queue_position"] = i + 1

    return results[:limit]


@router.get("/{request_id}")
async def get_request(request_id: str):
    """Get a single request by ID."""
    if request_id not in requests_db:
        raise HTTPException(status_code=404, detail="Request not found")
    return requests_db[request_id]


def get_requests_store():
    """Expose the store for other routes."""
    return requests_db

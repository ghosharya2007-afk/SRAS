"""
SRAS Stats Routes
=================
GET /api/stats/dashboard — Aggregated dashboard metrics
"""

from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("/dashboard")
async def get_dashboard_stats():
    """
    Return aggregated operational metrics for the admin dashboard.
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
    active_providers = [p for p in all_providers if p["status"] == "available"]

    # Pending by type
    pending_by_type = {}
    for r in pending:
        t = r.get("type", "other")
        pending_by_type[t] = pending_by_type.get(t, 0) + 1

    # Average wait time for pending requests
    now = datetime.now(timezone.utc)
    wait_times = []
    for r in pending:
        try:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            wait_minutes = (now - created).total_seconds() / 60
            wait_times.append(wait_minutes)
        except (ValueError, KeyError):
            pass

    avg_wait = round(sum(wait_times) / len(wait_times), 1) if wait_times else 0.0

    # Resolution rate today
    total_today = len(all_requests) if all_requests else 1
    resolution_rate = round(len(resolved) / total_today, 3) if total_today > 0 else 0.0

    # Highest priority unmet request
    highest_unmet = None
    if pending:
        highest_unmet = max(pending, key=lambda r: r.get("priority_score", 0))

    # Zone demand aggregation
    zone_map = {}
    for r in pending:
        zone = r.get("location", {}).get("zone", "Unknown")
        if zone not in zone_map:
            zone_map[zone] = {"zone": zone, "count": 0, "total_priority": 0}
        zone_map[zone]["count"] += 1
        zone_map[zone]["total_priority"] += r.get("priority_score", 0)

    zone_demand = []
    for z in zone_map.values():
        z["avg_priority"] = round(z["total_priority"] / z["count"], 2) if z["count"] > 0 else 0
        del z["total_priority"]
        zone_demand.append(z)

    return {
        "pending_by_type": pending_by_type,
        "avg_wait_minutes": avg_wait,
        "resolution_rate_today": resolution_rate,
        "active_providers": len(active_providers),
        "highest_priority_unmet": highest_unmet,
        "zone_demand": zone_demand,
        "total_pending": len(pending),
        "total_resolved_today": len(resolved),
        "total_requests": len(all_requests),
        "total_providers": len(all_providers),
        "total_dispatches": len(all_dispatches),
    }

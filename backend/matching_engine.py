"""
SRAS Matching Engine
====================
Greedy matching algorithm for request-to-provider assignment.

Matching Score Formula:
  M(r, p) = w₁ × Proximity(r,p) + w₂ × Reliability(p) + w₃ × Capability(r,p)

Where:
  w₁ = 0.55 (proximity weight)
  w₂ = 0.30 (reliability weight)
  w₃ = 0.15 (capability match weight)

  Proximity(r, p) = 1 / (1 + d_km)
  Reliability(p) = provider.reliability_score / 10
  Capability(r, p) = 1.0 if r.type ∈ p.capability_types else 0.0
"""

import math
from typing import Optional

# Matching weights
W_PROXIMITY = 0.55
W_RELIABILITY = 0.30
W_CAPABILITY = 0.15

# Provider reliability score adjustments
RELIABILITY_SUCCESS_BOOST = 0.5
RELIABILITY_FAILURE_PENALTY = 1.0
RELIABILITY_MIN = 1.0
RELIABILITY_MAX = 10.0
RELIABILITY_DEFAULT = 5.0


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate Haversine distance between two points in kilometers.
    Earth radius: 6371 km.
    """
    R = 6371.0  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def compute_matching_score(request: dict, provider: dict) -> dict:
    """
    Compute matching score between a request and a provider.
    
    Returns dict with total score and component breakdown.
    """
    req_lat = request["location"]["lat"]
    req_lng = request["location"]["lng"]
    prov_lat = provider["location"]["lat"]
    prov_lng = provider["location"]["lng"]

    # Distance in km
    distance_km = haversine_distance_km(req_lat, req_lng, prov_lat, prov_lng)

    # Proximity score: closer = higher (range: 0 to 1)
    proximity = 1.0 / (1.0 + distance_km)

    # Reliability score: normalized to 0-1
    reliability_raw = provider.get("reliability_score", RELIABILITY_DEFAULT)
    reliability = max(0, min(1, reliability_raw / 10.0))

    # Capability match: binary (1 if provider can serve this request type)
    request_type = request.get("type", "food")
    provider_capabilities = provider.get("capability_types", [])
    capability = 1.0 if request_type in provider_capabilities else 0.0

    # Weighted total
    total = (W_PROXIMITY * proximity +
             W_RELIABILITY * reliability +
             W_CAPABILITY * capability)

    return {
        "total": round(total, 4),
        "proximity_score": round(proximity, 4),
        "reliability_score": round(reliability, 4),
        "capability_match": capability,
        "distance_km": round(distance_km, 2),
    }


def find_best_provider(request: dict, providers: list[dict]) -> Optional[dict]:
    """
    Find the best available provider for a request using greedy matching.
    
    Filters by:
      1. Provider status must be "available"
      2. Provider must have capability for request type
    
    Scores remaining candidates and returns the best match.
    """
    request_type = request.get("type", "food")

    # Filter candidates
    candidates = [
        p for p in providers
        if p.get("status") == "available"
        and request_type in p.get("capability_types", [])
    ]

    if not candidates:
        return None

    # Score each candidate
    scored = []
    for provider in candidates:
        score_info = compute_matching_score(request, provider)
        scored.append({
            "provider": provider,
            "match_score": score_info,
        })

    # Sort by total score descending
    scored.sort(key=lambda x: x["match_score"]["total"], reverse=True)

    return scored[0] if scored else None


def run_greedy_dispatch(requests: list[dict], providers: list[dict]) -> dict:
    """
    Run greedy matching: for each pending request (sorted by priority desc),
    find the best available provider.
    
    Returns:
      - matched: list of (request_id, provider_id, score) tuples
      - unmatched_requests: list of request IDs with no available provider
      - assignments: detailed assignment info
    """
    # Sort requests by priority score descending
    sorted_requests = sorted(
        requests,
        key=lambda r: r.get("priority_score", 0),
        reverse=True,
    )

    # Track available providers (copy to avoid mutation)
    available_providers = [
        p.copy() for p in providers if p.get("status") == "available"
    ]

    matched = []
    unmatched = []
    assignments = []

    for request in sorted_requests:
        if request.get("status") != "pending":
            continue

        best = find_best_provider(request, available_providers)

        if best:
            provider = best["provider"]
            score = best["match_score"]

            assignment = {
                "request_id": request.get("id"),
                "provider_id": provider.get("id"),
                "match_score": score["total"],
                "distance_km": score["distance_km"],
                "score_breakdown": score,
            }

            matched.append(assignment)
            assignments.append(assignment)

            # Remove matched provider from available pool
            available_providers = [
                p for p in available_providers
                if p.get("id") != provider.get("id")
            ]
        else:
            unmatched.append(request.get("id"))

    return {
        "matched_count": len(matched),
        "unmatched_count": len(unmatched),
        "assignments": assignments,
        "unmatched_requests": unmatched,
    }


def update_reliability_score(current_score: float, success: bool) -> float:
    """
    Update provider reliability score based on dispatch outcome.
    
    Success: +0.5 (capped at 10.0)
    Failure/Timeout: -1.0 (floored at 1.0)
    """
    if success:
        new_score = current_score + RELIABILITY_SUCCESS_BOOST
    else:
        new_score = current_score - RELIABILITY_FAILURE_PENALTY

    return round(max(RELIABILITY_MIN, min(RELIABILITY_MAX, new_score)), 1)

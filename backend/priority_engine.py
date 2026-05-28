"""
SRAS Priority Engine
====================
Implements bounded priority scoring with logarithmic aging.

Formula:
  P(r) = B(type) + T(t) + S(s) + V(v)

Where:
  B(type) = base urgency by category
  T(t) = min(40, 40 × ln(1 + t_hours) / ln(1 + 12))  [bounded time aging]
  S(s) = severity × 3  [severity bonus, range 3-30]
  V(v) = 5 if verified, else 0
"""

import math
from datetime import datetime, timezone
from enum import IntEnum
from typing import Optional


class ResourceCategory(IntEnum):
    FOOD = 1
    SHELTER = 2
    MEDICAL = 3
    CRITICAL = 4


CATEGORY_BASE_SCORES = {
    "food": 10,
    "shelter": 15,
    "medical": 50,
    "critical": 100,
}

# Score ranges per category:
# food:     [10, 85]
# shelter:  [15, 90]
# medical:  [50, 125]
# critical: [100, 175]

MAX_AGING_BONUS = 40.0
AGING_SATURATION_HOURS = 12.0  # time bonus plateaus after ~12 hours
SEVERITY_MULTIPLIER = 3.0      # severity 1-10 → bonus 3-30
VERIFIED_BOOST = 5.0


def compute_time_bonus(minutes_waiting: float) -> float:
    """
    Logarithmic time-aging bonus with hard cap at MAX_AGING_BONUS.
    
    Properties:
      - At t=0:   T ≈ 0
      - At t=1hr: T ≈ 11.5
      - At t=6hr: T ≈ 30.1
      - At t=12h: T = 40.0 (hard cap)
      - Growth rate slows after 6 hours (prevents starvation inversion)
    """
    hours_waiting = max(0, minutes_waiting / 60.0)
    raw_bonus = MAX_AGING_BONUS * math.log1p(hours_waiting) / math.log1p(AGING_SATURATION_HOURS)
    return min(MAX_AGING_BONUS, round(raw_bonus, 2))


def compute_severity_bonus(severity: int) -> float:
    """
    Linear severity bonus. severity ∈ [1, 10] → bonus ∈ [3, 30].
    """
    clamped = max(1, min(10, severity))
    return round(clamped * SEVERITY_MULTIPLIER, 2)


def compute_priority_score(
    request_type: str,
    severity: int,
    minutes_waiting: float,
    is_verified: bool = False,
) -> dict:
    """
    Compute bounded priority score with full breakdown.
    
    Returns dict with:
      - total: final priority score
      - base: base score from category
      - time_bonus: logarithmic aging bonus
      - severity_bonus: severity contribution
      - verified_bonus: trusted source boost
    """
    base = CATEGORY_BASE_SCORES.get(request_type, 10)
    time_bonus = compute_time_bonus(minutes_waiting)
    severity_bonus = compute_severity_bonus(severity)
    verified_bonus = VERIFIED_BOOST if is_verified else 0.0

    total = round(base + time_bonus + severity_bonus + verified_bonus, 2)

    return {
        "total": total,
        "base": base,
        "time_bonus": time_bonus,
        "severity_bonus": severity_bonus,
        "verified_bonus": verified_bonus,
        "category": request_type,
    }


def compute_priority_from_request(request_data: dict) -> dict:
    """
    Compute priority from a Firestore request document.
    Automatically calculates minutes_waiting from created_at.
    """
    created_at = request_data.get("created_at")
    if created_at:
        if hasattr(created_at, 'timestamp'):
            # Firestore Timestamp object
            created_time = datetime.fromtimestamp(created_at.timestamp(), tz=timezone.utc)
        elif isinstance(created_at, str):
            created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created_time = datetime.now(timezone.utc)
        
        now = datetime.now(timezone.utc)
        minutes_waiting = (now - created_time).total_seconds() / 60.0
    else:
        minutes_waiting = 0.0

    return compute_priority_score(
        request_type=request_data.get("type", "food"),
        severity=request_data.get("severity", 5),
        minutes_waiting=minutes_waiting,
        is_verified=request_data.get("is_verified", False),
    )


def get_queue_position(request_score: float, all_scores: list[float]) -> int:
    """
    Determine queue position (1-indexed) given a score and all scores.
    Higher score = higher position (lower number).
    """
    sorted_scores = sorted(all_scores, reverse=True)
    try:
        return sorted_scores.index(request_score) + 1
    except ValueError:
        return len(sorted_scores) + 1


def estimate_wait_time(queue_position: int, avg_resolution_minutes: float = 15.0) -> float:
    """
    Rough estimate of wait time based on queue position.
    Uses historical average resolution time.
    """
    return round(queue_position * avg_resolution_minutes, 1)

"""
SRAS Pydantic Models & Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LocationSchema(BaseModel):
    lat: float
    lng: float
    address: Optional[str] = ""
    zone: Optional[str] = "Zone-A"


class CreateRequestBody(BaseModel):
    type: str = Field(..., description="food | medical | shelter | critical")
    description: str = Field(..., min_length=3)
    severity: int = Field(5, ge=1, le=10)
    location: LocationSchema
    requester_id: Optional[str] = "anonymous"
    is_verified: bool = False


class RequestResponse(BaseModel):
    id: str
    type: str
    description: str
    severity: int
    location: dict
    status: str
    priority_score: float
    queue_position: int
    gemini_analysis: Optional[dict] = None
    created_at: str
    assigned_to: Optional[str] = None
    is_verified: bool = False
    score_breakdown: Optional[dict] = None


class ProviderRegistrationBody(BaseModel):
    name: str
    organization: Optional[str] = ""
    capability_types: list[str] = Field(..., description='e.g. ["food", "medical"]')
    location: LocationSchema
    provider_uid: Optional[str] = "anonymous"


class DispatchActionBody(BaseModel):
    dispatch_id: str


class AnalyzeRequestBody(BaseModel):
    text: str = Field(..., min_length=3)


class DashboardStats(BaseModel):
    pending_by_type: dict
    avg_wait_minutes: float
    resolution_rate_today: float
    active_providers: int
    highest_priority_unmet: Optional[dict] = None
    zone_demand: list
    total_pending: int
    total_resolved_today: int

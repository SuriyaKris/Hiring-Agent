"""Enrichment Plan schema for Candidate Enrichment Sourcing."""

from typing import List, Dict
from pydantic import BaseModel, Field


class EnrichmentPlan(BaseModel):
    """Represents a planned sequence of candidate enrichment executions."""
    providers: List[str] = Field(default_factory=list, description="List of provider names scheduled to execute")
    estimated_cost: float = Field(0.0, description="Total estimated cost of the plan (in USD)")
    estimated_time: float = Field(0.0, description="Total estimated execution time of the plan (in seconds)")
    reason: str = Field(..., description="Justification explaining the need for the selected providers")
    field_confidences: Dict[str, float] = Field(default_factory=dict, description="Expected confidence accuracy per missing field")

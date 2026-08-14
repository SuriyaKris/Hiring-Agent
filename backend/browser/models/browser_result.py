"""Browser Result Model — Milestone: State & Result.

Structured outcome schema returned by the BrowserAgent.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from browser.health_check import HealthReport


class BrowserResult(BaseModel):
    """Structured result returned upon completing a BrowserPlan."""
    success: bool = Field(..., description="Whether the objective was fully achieved without critical failure")
    profile: Dict[str, Any] = Field(default_factory=dict, description="Extracted profile data payload")
    screenshots: List[str] = Field(default_factory=list, description="Paths to captured screenshot files")
    downloads: List[str] = Field(default_factory=list, description="Paths to files downloaded during execution")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Consolidated timing and efficiency metrics")
    health_report: Optional[HealthReport] = Field(None, description="Structured health check assessment of target platform")
    errors: List[str] = Field(default_factory=list, description="List of error logs or exception messages collected during run")

"""Browser Plan Models — Milestone 3.3."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from browser.models.enrichment_objective import EnrichmentObjective


class BrowserPlanStep(BaseModel):
    """Represents a single step/task within a BrowserPlan."""
    task_type: str = Field(..., description="Unique name/type of the browser task (e.g., 'open_page')")
    params: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters passed to the task")
    status: str = Field("pending", description="Execution state: 'pending' | 'running' | 'completed' | 'failed'")
    duration_seconds: float = Field(0.0, description="Execution duration of this step in seconds")
    error_message: Optional[str] = Field(None, description="Error message description if this step failed")


class BrowserPlan(BaseModel):
    """Holds a sequence of BrowserPlanSteps compiled from an EnrichmentObjective."""
    objective: EnrichmentObjective = Field(..., description="High level objective this plan satisfies")
    steps: List[BrowserPlanStep] = Field(default_factory=list, description="Ordered sequence of tasks/steps to execute")
    status: str = Field("pending", description="Plan execution status: 'pending' | 'running' | 'completed' | 'failed'")

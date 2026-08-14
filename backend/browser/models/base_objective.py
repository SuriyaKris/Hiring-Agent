"""Base Browser Objective Model — Specialized Models.

Provides standard parameters shared across both Search and Enrichment objectives.
"""

from pydantic import BaseModel, Field


class BaseBrowserObjective(BaseModel):
    """Common schema parameters inherited by specialized browser intents."""
    goal: str = Field(..., description="High-level goal or reason for the browser action (e.g. 'SearchCandidates', 'EnrichCandidate')")
    site: str = Field(..., description="Target site/platform name (e.g. 'linkedin', 'indeed')")
    priority: int = Field(1, description="Execution priority (lower is higher priority)")
    timeout: int = Field(30000, description="Overall execution timeout in milliseconds")

"""Browser Validation Models — Milestone 4.2.

Provides structures representing profile-level outcomes and consolidated validation results.
"""

from typing import List, Dict
from pydantic import BaseModel, Field


class ProfileResult(BaseModel):
    """Result details for a single candidate profile validation run."""
    name: str = Field(..., description="Name of candidate/page under test")
    url: str = Field(..., description="Target URL tested")
    platform: str = Field(..., description="Target platform name (e.g. 'linkedin')")
    success: bool = Field(..., description="Whether the browser navigation completed without errors")
    sections_found: List[str] = Field(default_factory=list, description="Sections successfully extracted")
    sections_missing: List[str] = Field(default_factory=list, description="Expected sections that were empty or missing")
    duration: float = Field(0.0, description="Execution duration in seconds")
    errors: List[str] = Field(default_factory=list, description="Error messages raised during execution steps")


class BrowserValidationResult(BaseModel):
    """Overall report compiling outcomes across all validation runs."""
    results: List[ProfileResult] = Field(default_factory=list, description="Aggregated validation details per profile")
    total_profiles: int = Field(0, description="Total profiles tested")
    successful_runs: int = Field(0, description="Total successful profile runs")
    failed_runs: int = Field(0, description="Total failed profile runs")
    overall_success_rate: float = Field(0.0, description="Pass/fail ratio across all tests (0.0 to 1.0)")
    section_accuracies: Dict[str, float] = Field(default_factory=dict, description="Percentage of successfully found sections (0.0 to 1.0)")
    failure_reasons: Dict[str, int] = Field(default_factory=dict, description="Counts of categorized reasons for failure")
    average_duration: float = Field(0.0, description="Average run duration in seconds")

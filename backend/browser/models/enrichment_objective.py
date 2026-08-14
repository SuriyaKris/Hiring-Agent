"""Enrichment Objective Model — Specialized Models."""

from typing import List, Optional
from pydantic import Field
from browser.models.base_objective import BaseBrowserObjective


class EnrichmentObjective(BaseBrowserObjective):
    """Schema representing candidate details enrichment objectives/intents."""
    url: Optional[str] = Field(None, description="Direct page URL to navigate to (if known)")
    candidate_url: Optional[str] = Field(None, description="URL of the candidate profile (alternative to url)")
    sections: List[str] = Field(default_factory=list, description="Target profile sections to extract (e.g. ['about', 'skills'])")

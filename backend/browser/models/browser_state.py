"""Browser State Model — Milestone: State & Result.

Maintains dynamic, serializable runtime state tracking during browser execution.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class BrowserState(BaseModel):
    """Schema tracking active runtime states of a browser session."""
    current_url: Optional[str] = Field(None, description="Active page URL")
    authenticated: bool = Field(False, description="Whether the browser session is authenticated")
    cookies: List[dict] = Field(default_factory=list, description="Retrieved session cookies")
    screenshots: List[str] = Field(default_factory=list, description="List of captured screenshot paths")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Active task metrics and execution timings")
    visited_pages: List[str] = Field(default_factory=list, description="Chronological log of navigated URLs")
    downloaded_files: List[str] = Field(default_factory=list, description="Paths of any downloaded files")
    errors: List[str] = Field(default_factory=list, description="Any warnings or errors captured during runtime")

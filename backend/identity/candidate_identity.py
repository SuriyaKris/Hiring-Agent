"""Candidate Identity Model — Milestone 6.1.

Defines the entity structures representing a resolved unique human entity across various sources.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

from schemas.candidate_profile import CandidateProfile


class CandidateIdentity(BaseModel):
    """Aggregates multiple candidate profiles linked to the same physical person."""
    identity_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Resolved unique human identifier")
    confidence: float = Field(1.0, description="Match confidence score for this resolution (0.0 to 1.0)")
    sources: List[str] = Field(default_factory=list, description="Source platforms compiled (e.g. ['linkedin', 'apollo'])")
    primary_profile: CandidateProfile = Field(..., description="Normalized master/consolidated candidate profile")
    aliases: List[str] = Field(default_factory=list, description="Alternative names or handles matched")
    matched_profiles: List[CandidateProfile] = Field(default_factory=list, description="Roster of original profiles resolved into this identity")

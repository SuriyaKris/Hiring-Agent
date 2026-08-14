"""Matching Engine for Identity Resolution — Milestone 6.2.

Computes match scores based on hard (Exact URL/Email) and soft (Name, Company, Title, Location) signals.
"""

import re
from typing import Optional
from difflib import SequenceMatcher
from loguru import logger

from schemas.candidate_profile import CandidateProfile


def normalize_val(val: Optional[str]) -> str:
    """Normalize strings by removing extra whitespace, lowercasing, and stripping punctuation."""
    if not val:
        return ""
    # Strip URL protocols if matching URLs
    val = re.sub(r'^(https?://)?(www\.)?', '', val.strip().lower())
    val = val.rstrip("/")
    return val


def string_similarity(s1: str, s2: str) -> float:
    """Compute string similarity ratio using SequenceMatcher."""
    n1, n2 = normalize_val(s1), normalize_val(s2)
    if not n1 or not n2:
        return 0.0
    return SequenceMatcher(None, n1, n2).ratio()


class MatchingEngine:
    """Calculates resolution confidence across exact (hard) and similarity-based (soft) candidate signals."""

    def __init__(self, match_threshold: float = 0.8):
        self.match_threshold = match_threshold

    def get_current_company(self, profile: CandidateProfile) -> str:
        """Helper to retrieve current company name."""
        if profile.company and profile.company.name:
            return profile.company.name
        if profile.experience:
            for exp in profile.experience:
                if exp.is_current:
                    return exp.company_name
            return profile.experience[0].company_name
        return ""

    def get_current_title(self, profile: CandidateProfile) -> str:
        """Helper to retrieve current job title."""
        if profile.experience:
            for exp in profile.experience:
                if exp.is_current:
                    return exp.title
            return profile.experience[0].title
        return ""

    def compute_match_score(self, p1: CandidateProfile, p2: CandidateProfile) -> float:
        """Calculate match score between two profiles (0.0 to 1.0)."""
        b1, b2 = p1.basic_info, p2.basic_info

        # ── HARD SIGNALS (100% confidence on matches) ─────────────────────────
        
        # 1. LinkedIn URL match
        li1, li2 = normalize_val(b1.linkedin_url), normalize_val(b2.linkedin_url)
        if li1 and li2 and (li1 == li2):
            # Exclude generic base domains
            if li1 not in ["linkedin.com", "linkedin.com/in", "linkedin.com/in/", "www.linkedin.com", "www.linkedin.com/in", "www.linkedin.com/in/"]:
                return 1.0

        # 2. Email match
        em1, em2 = normalize_val(b1.email), normalize_val(b2.email)
        if em1 and em2 and (em1 == em2):
            # Exclude placeholder emails indicating not unlocked
            if not ("not_unlocked" in em1 or "notunlocked" in em1 or em1 in ["", "null", "none"]):
                return 1.0

        # 3. GitHub URL match
        gh1, gh2 = normalize_val(b1.github_url), normalize_val(b2.github_url)
        if gh1 and gh2 and (gh1 == gh2):
            return 1.0

        # 4. Apollo Person ID match
        ap1 = normalize_val(p1.metadata.apollo_person_id)
        ap2 = normalize_val(p2.metadata.apollo_person_id)
        if ap1 and ap2 and (ap1 == ap2):
            return 1.0

        # ── SOFT SIGNALS (Weighted components if hard signals are absent) ─────
        # Component Weights: Name (40%), Company (30%), Title (20%), Location (10%)
        
        name_sim = string_similarity(b1.full_name, b2.full_name)
        
        comp1 = self.get_current_company(p1)
        comp2 = self.get_current_company(p2)
        comp_sim = string_similarity(comp1, comp2)

        title1 = self.get_current_title(p1)
        title2 = self.get_current_title(p2)
        title_sim = string_similarity(title1, title2)

        loc_sim = string_similarity(b1.location, b2.location)

        # Calculate weighted sum of present properties
        weighted_score = (
            (name_sim * 0.4) +
            (comp_sim * 0.3) +
            (title_sim * 0.2) +
            (loc_sim * 0.1)
        )

        return round(weighted_score, 3)

    def is_match(self, p1: CandidateProfile, p2: CandidateProfile) -> bool:
        """Check if two profiles are a match based on threshold limits."""
        score = self.compute_match_score(p1, p2)
        return score >= self.match_threshold

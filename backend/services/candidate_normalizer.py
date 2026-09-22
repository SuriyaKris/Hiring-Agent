"""Candidate Normalizer — Standardizes metadata representations for candidate profiles."""

import re
from typing import List, Optional
from loguru import logger
from schemas.candidate_profile import CandidateProfile, SkillItem


def clean_name(name: Optional[str]) -> str:
    """Format and normalize candidate names."""
    if not name:
        return "Unknown"
    name = name.strip()
    # Remove professional suffix titles (MD, PhD, MBA, Esq)
    name = re.sub(r',\s*(MD|PhD|MBA|Esq|PMP|PE)\b', '', name, flags=re.IGNORECASE)
    # Titlecase
    return name.title()


def clean_company(company: Optional[str]) -> str:
    """Clean company naming noise (Inc, LLC, Corp)."""
    if not company:
        return ""
    company = company.strip()
    company = re.sub(r'\b,\s*(Inc\.?|LLC|Corp\.?|L\.P\.|Co\.?|Incorporated|Corporation)\b', '', company, flags=re.IGNORECASE)
    company = re.sub(r'\b\s+(Inc\.?|LLC|Corp\.?|L\.P\.|Co\.?|Incorporated|Corporation)\b', '', company, flags=re.IGNORECASE)
    return company.strip()


def clean_location(loc: Optional[str]) -> str:
    """Normalize location syntax without injecting default countries."""
    if not loc:
        return ""
    loc = loc.strip()
    # Map double comma or trailing spaces
    loc = re.sub(r'\s*,\s*', ', ', loc)
    return loc.strip(", ")


def normalize_url(url: Optional[str]) -> str:
    """Strip query parameters, trailing slashes, and spaces from profile URLs."""
    if not url:
        return ""
    url = url.strip()
    # Strip query parameters
    url = url.split("?")[0]
    # Strip trailing slash
    if url.endswith("/"):
        url = url[:-1]
    return url


class CandidateNormalizer:
    """Normalizes candidate profile fields before evaluation and matching engines."""

    def normalize(self, profile: CandidateProfile) -> CandidateProfile:
        """Apply standardization rules to profile properties in-place."""
        basic = profile.basic_info
        
        # Normalize LinkedIn URL
        if basic.linkedin_url:
            basic.linkedin_url = normalize_url(basic.linkedin_url)
        
        # Clean basic details
        basic.full_name = clean_name(basic.full_name)
        if basic.first_name:
            basic.first_name = clean_name(basic.first_name)
        if basic.last_name:
            basic.last_name = clean_name(basic.last_name)
            
        basic.location = clean_location(basic.location)

        # Standardize company info
        if profile.company and profile.company.name:
            profile.company.name = clean_company(profile.company.name)

        # Standardize experience company names and titles
        for exp in profile.experience:
            exp.company_name = clean_company(exp.company_name)
            exp.title = exp.title.strip()
            exp.location = clean_location(exp.location)

        # Standardize skills list
        clean_skills = []
        seen_skills = set()
        for skill in profile.skills:
            name = skill.name.strip()
            norm = name.lower()
            if norm not in seen_skills:
                clean_skills.append(SkillItem(name=name, category=skill.category))
                seen_skills.add(norm)
        profile.skills = clean_skills

        return profile

"""Deduplication Service — Milestone 5.5.

Matches and merges duplicate CandidateProfiles by LinkedIn URL, Email, GitHub, and Name + Company.
"""

from typing import List, Dict, Optional
import re
from loguru import logger

from schemas.candidate_profile import CandidateProfile, ExperienceItem, SkillItem


def normalize_string(val: Optional[str]) -> str:
    """Lowercase and strip whitespace/punctuation for soft comparisons."""
    if not val:
        return ""
    return re.sub(r'[^a-z0-9]', '', val.lower())


def get_current_company(profile: CandidateProfile) -> Optional[str]:
    """Retrieve current company name from CompanyDetails or current experience items."""
    if profile.company and profile.company.name:
        return profile.company.name
    if profile.experience:
        for exp in profile.experience:
            if exp.is_current:
                return exp.company_name
        return profile.experience[0].company_name
    return None


def merge_profiles(p1: CandidateProfile, p2: CandidateProfile) -> CandidateProfile:
    """Merge details of profile p2 into p1 in-place, preserving richer fields."""
    b1 = p1.basic_info
    b2 = p2.basic_info

    # Basic info fields fallback
    if not b1.email and b2.email:
        b1.email = b2.email
    if not b1.phone and b2.phone:
        b1.phone = b2.phone
    if not b1.linkedin_url and b2.linkedin_url:
        b1.linkedin_url = b2.linkedin_url
    if not b1.github_url and b2.github_url:
        b1.github_url = b2.github_url
    if not b1.location and b2.location:
        b1.location = b2.location
    if not b1.headline and b2.headline:
        b1.headline = b2.headline

    # Merge Summary
    if (not p1.summary or not p1.summary.about) and p2.summary and p2.summary.about:
        p1.summary = p2.summary

    # Merge Company details
    if (not p1.company or not p1.company.name) and p2.company and p2.company.name:
        p1.company = p2.company

    # Merge Skills
    existing_skills = {normalize_string(s.name) for s in p1.skills}
    for skill in p2.skills:
        norm_s = normalize_string(skill.name)
        if norm_s not in existing_skills:
            p1.skills.append(skill)
            existing_skills.add(norm_s)

    # Merge Experiences
    existing_exp = {
        (normalize_string(e.company_name), normalize_string(e.title))
        for e in p1.experience
    }
    for exp in p2.experience:
        key = (normalize_string(exp.company_name), normalize_string(exp.title))
        if key not in existing_exp:
            p1.experience.append(exp)
            existing_exp.add(key)

    # Merge Education
    existing_edu = {normalize_string(e.school_name) for e in p1.education}
    for edu in p2.education:
        norm_e = normalize_string(edu.school_name)
        if norm_e not in existing_edu:
            p1.education.append(edu)
            existing_edu.add(norm_e)

    # Merge Certifications
    existing_cert = {normalize_string(c.name) for c in p1.certifications}
    for cert in p2.certifications:
        norm_c = normalize_string(cert.name)
        if norm_c not in existing_cert:
            p1.certifications.append(cert)
            existing_cert.add(norm_c)

    # Merge Metadata (add executed providers together)
    raw1 = p1.metadata.raw_data or {}
    raw2 = p2.metadata.raw_data or {}
    exec1 = set(raw1.get("executed_providers", []))
    exec2 = set(raw2.get("executed_providers", []))
    raw1["executed_providers"] = list(exec1.union(exec2))
    p1.metadata.raw_data = raw1

    return p1


def is_valid_dedup_email(email: Optional[str]) -> bool:
    if not email:
        return False
    e = email.lower().strip()
    return not ("not_unlocked" in e or "notunlocked" in e or e in ["", "null", "none"])


def is_valid_dedup_linkedin(url: Optional[str]) -> bool:
    if not url:
        return False
    u = url.lower().strip()
    return u not in ["", "https://linkedin.com", "https://linkedin.com/in", "https://linkedin.com/in/", "https://www.linkedin.com", "https://www.linkedin.com/in", "https://www.linkedin.com/in/"]


class DeduplicationService:
    """Handles identification and merging of redundant candidate records."""

    def deduplicate(self, candidates: List[CandidateProfile]) -> List[CandidateProfile]:
        """Aggregate duplicate profiles, returning a list of unique, enriched CandidateProfiles."""
        unique_profiles: List[CandidateProfile] = []

        for cand in candidates:
            matched_idx = -1
            
            # Extract key properties
            c_name_norm = normalize_string(cand.basic_info.full_name)
            c_company_norm = normalize_string(get_current_company(cand))
            c_email_norm = normalize_string(cand.basic_info.email)
            c_li_norm = normalize_string(cand.basic_info.linkedin_url)
            c_gh_norm = normalize_string(cand.basic_info.github_url)

            # Look for existing match in unique list
            for idx, existing in enumerate(unique_profiles):
                e_name_norm = normalize_string(existing.basic_info.full_name)
                e_company_norm = normalize_string(get_current_company(existing))
                e_email_norm = normalize_string(existing.basic_info.email)
                e_li_norm = normalize_string(existing.basic_info.linkedin_url)
                e_gh_norm = normalize_string(existing.basic_info.github_url)

                # Match Criteria 1: LinkedIn URL match
                if is_valid_dedup_linkedin(cand.basic_info.linkedin_url) and is_valid_dedup_linkedin(existing.basic_info.linkedin_url):
                    if c_li_norm and e_li_norm and (c_li_norm == e_li_norm):
                        matched_idx = idx
                        break

                # Match Criteria 2: Email Match
                if is_valid_dedup_email(cand.basic_info.email) and is_valid_dedup_email(existing.basic_info.email):
                    if c_email_norm and e_email_norm and (c_email_norm == e_email_norm):
                        matched_idx = idx
                        break

                # Match Criteria 3: GitHub Match
                if c_gh_norm and e_gh_norm and (c_gh_norm == e_gh_norm):
                    matched_idx = idx
                    break

                # Match Criteria 4: Name + Current Company match
                if c_name_norm and e_name_norm and (c_name_norm == e_name_norm):
                    if c_company_norm and e_company_norm and (c_company_norm == e_company_norm):
                        matched_idx = idx
                        break

            if matched_idx != -1:
                # Merge duplicate into matched record
                logger.info(f"[Deduplication] Merging duplicate candidate '{cand.basic_info.full_name}'")
                unique_profiles[matched_idx] = merge_profiles(unique_profiles[matched_idx], cand)
            else:
                unique_profiles.append(cand)

        return unique_profiles


async def get_excluded_identities(db, role_track_id) -> set[str]:
    """
    Query all candidate records that belong to any search session in this role track.
    Returns a set of normalized values (email, linkedin_url, apollo_person_id) to exclude.
    """
    try:
        import uuid
        from sqlalchemy import select
        from db import CandidateRecord, SearchSessionRecord
        from identity.matching_engine import normalize_val

        # Find all sessions in this track
        session_stmt = select(SearchSessionRecord.session_id).where(SearchSessionRecord.role_track_id == role_track_id)
        res = await db.execute(session_stmt)
        session_ids = [r[0] for r in res.all()]

        if not session_ids:
            return set()

        # Query all candidates in those sessions
        cand_stmt = select(CandidateRecord).where(CandidateRecord.search_session_id.in_(session_ids))
        res = await db.execute(cand_stmt)
        candidates = res.scalars().all()

        exclusions = set()
        for c in candidates:
            if c.apollo_person_id:
                exclusions.add(normalize_val(c.apollo_person_id))
            if c.linkedin_url:
                exclusions.add(normalize_val(c.linkedin_url))
            if c.email:
                exclusions.add(normalize_val(c.email))

        return exclusions
    except Exception as e:
        from loguru import logger
        logger.warning(f"Failed to fetch excluded identities: {e}")
        return set()

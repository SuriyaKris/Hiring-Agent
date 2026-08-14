"""
Feature Engineering Service — .
Calculates a 6-wide feature vector for candidate profiles against a Job Description search specification.
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

from models.schemas import JDSearchSpec, CandidateFeatures
from schemas.candidate_profile import CandidateProfile
from nlp.title_taxonomy import (
    FUZZY_MATCH_THRESHOLD,
    REGION_MAP,
    ABOUT_SEMANTIC_SIM_FLOOR,
    ABOUT_SEMANTIC_SIM_CEILING,
    EXP_SEMANTIC_SIM_FLOOR,
    EXP_SEMANTIC_SIM_CEILING,
    RELEVANT_EXP_MULTIPLIER,
)
from nlp.embedding_model import SemanticEmbedder

# Instantiate a thread-safe semantic embedder cache
_semantic_embedder = SemanticEmbedder()


def normalize_persona(persona_input: Any) -> str:
    """Lowercase and strip role-level prefixes (e.g. entry, senior, mid) for comparison. Handles list or string."""
    if not persona_input:
        return ""
    if isinstance(persona_input, list):
        persona_str = " ".join(str(item) for item in persona_input if item)
    else:
        persona_str = str(persona_input)
        
    p = persona_str.lower().strip()
    
    # Strip common seniority level prefixes
    prefixes = ["entry / ", "mid / ", "senior / ", "junior / ", "associate / "]
    for prefix in prefixes:
        if p.startswith(prefix):
            p = p[len(prefix):]
            
    # Normalize punctuation and whitespace
    p = re.sub(r'[^a-z0-9 ]', ' ', p)
    return " ".join(p.split())


def parse_date_to_year_fraction(date_str: Optional[str], default_now: bool = False) -> Optional[float]:
    """Convert YYYY-MM or YYYY date strings to a fractional float representing the year."""
    if not date_str:
        if default_now:
            now = datetime.utcnow()
            return now.year + (now.month - 1) / 12.0
        return None
        
    date_str = date_str.strip()
    if date_str.lower() == 'present':
        now = datetime.utcnow()
        return now.year + (now.month - 1) / 12.0
        
    # Match YYYY-MM
    m = re.match(r'^(\d{4})-(\d{2})', date_str)
    if m:
        year = int(m.group(1))
        month = int(m.group(2))
        return year + (month - 1) / 12.0
        
    # Match YYYY
    m = re.match(r'^(\d{4})', date_str)
    if m:
        return float(m.group(1))
        
    if default_now:
        now = datetime.utcnow()
        return now.year + (now.month - 1) / 12.0
        
    logger.warning(f"Could not parse date string '{date_str}' — treating job duration as unknown, not zero.")
    return None



def check_territory_match(candidate_location: str, target_territory: str) -> float:
    """
    Check if a candidate's location matches the target territory.
    Supports substring checking, word token matching, and region alias mapping.
    """
    if not candidate_location or not target_territory:
        return 0.0
        
    cand_lower = candidate_location.lower()
    target_lower = target_territory.lower()
    
    # Substring shortcut
    if target_lower in cand_lower or cand_lower in target_lower:
        return 1.0
        
    # Clean and tokenize
    cand_words = set(re.split(r'[^a-z0-9]', cand_lower))
    target_words = set(re.split(r'[^a-z0-9]', target_lower))
    
    # Word intersection for safety (exclude short 2-letter words like "la" or "or" to avoid collisions)
    intersect_words = cand_words.intersection(target_words)
    intersect_words = {w for w in intersect_words if len(w) > 2}
    if intersect_words:
        return 1.0
        
    # Region alias expansion
    for region, config in REGION_MAP.items():
        # If target matches this region
        target_matches_region = (
            region in target_lower or 
            any(name in target_lower for name in config["names"]) or
            any(code in target_words for code in config["codes"])
        )
        if target_matches_region:
            # Check if candidate matches any of the region names
            if any(name in cand_lower or name in cand_words for name in config["names"]):
                return 1.0
            # For 2-letter codes, we check exact standalone word token matching
            if any(code in cand_words for code in config["codes"]):
                return 1.0
                
    return 0.0


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Consolidate overlapping or adjacent intervals into a minimal list of non-overlapping intervals."""
    if not intervals:
        return []
    # Sort by start fraction
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = []
    for current in sorted_intervals:
        if not merged:
            merged.append(current)
        else:
            last_start, last_end = merged[-1]
            curr_start, curr_end = current
            # If current start overlaps or is adjacent to last end
            if curr_start <= last_end:
                merged[-1] = (last_start, max(last_end, curr_end))
            else:
                merged.append(current)
    return merged


def rescale_similarity(raw_sim: float, floor: float, ceiling: float) -> float:
    """
    Rescale a raw cosine similarity score computed on longer text (about/experience)
    into a fuller 0-1 range, since long-text embeddings compress into a narrow band.
    """
    if raw_sim <= floor:
        return 0.0
    if raw_sim >= ceiling:
        return 1.0
    return (raw_sim - floor) / (ceiling - floor)


class FeatureEngineeringService:
    """Service that computes candidate profile features against parsed JD specifications."""

    def compute_features(self, profile: CandidateProfile, spec: JDSearchSpec) -> Optional[CandidateFeatures]:
        """
        Calculate the 6 core features. Returns None if any critical JD specs are missing.
        """
        # Validate JD fields (Fail loud in dev: log warnings and return None for dependent features)
        target_titles = spec.target_titles
        target_persona = spec.target_persona
        target_territory = spec.target_territory
        raw_data = profile.metadata.raw_data or {}
        
        # We check if they are completely missing or empty
        if not target_titles:
            logger.warning("Feature engineering cannot run: 'target_titles' is missing or empty in JDSearchSpec.")
            return None
            
        if not target_persona:
            logger.warning("Feature engineering cannot run: 'target_persona' is missing or empty in JDSearchSpec.")
            return None
            
        if not target_territory:
            logger.warning("Feature engineering cannot run: 'target_territory' is missing or empty in JDSearchSpec.")
            return None
            
        # Get candidate's current title (Fix 2)
        current_job = next(
            (j for j in profile.experience if getattr(j, "is_current", False)),
            None
        )
        if current_job:
            logger.debug(f"Found explicit current job: '{current_job.title}' at '{current_job.company_name}'")
        else:
            current_job = profile.experience[0] if profile.experience else None
            if current_job:
                logger.debug(f"No explicit current job found; fell back to first experience item: '{current_job.title}'")
            else:
                logger.debug("No experience items available to select current job.")
                
        current_title = current_job.title if current_job else (profile.basic_info.headline or "")

        
        # 1. title_keyword_match
        title_keyword_match = 0.0
        if current_title:
            try:
                from rapidfuzz import fuzz
                scores = [fuzz.token_set_ratio(current_title.lower(), t.lower()) / 100.0 for t in target_titles]
                title_keyword_match = max(scores) if scores else 0.0
            except Exception as e:
                logger.error(f"Failed to calculate title_keyword_match: {e}")
                title_keyword_match = 0.0
                
        # (Persona match removed and weights reallocated to semantics)
                
        # 3. title_semantic_sim
        title_semantic_sim = 0.0
        if current_title:
            try:
                title_semantic_sim = _semantic_embedder.compute_max_similarity(current_title, target_titles)
            except Exception as e:
                logger.error(f"Failed to calculate title_semantic_sim: {e}")
                title_semantic_sim = 0.0
                
        # First compute total timeline experience from the candidate's history (Fix 1 & 3)
        history_intervals = []
        for job in profile.experience:
            start = job.start_date
            end = job.end_date
            s_frac = parse_date_to_year_fraction(start)
            e_frac = parse_date_to_year_fraction(end, default_now=job.is_current)
            if s_frac is None or e_frac is None:
                logger.warning(
                    f"Skipping experience item '{job.title or 'Unknown'}' at '{job.company_name or 'Unknown'}' "
                    f"due to unparseable dates: start='{start}', end='{end}'"
                )
                continue
            history_intervals.append((s_frac, e_frac))
            
        merged_history = merge_intervals(history_intervals)
        history_total = sum(max(0.0, end_f - start_f) for start_f, end_f in merged_history)


        # 4. total_experience_years
        # Passthrough/validation
        total_exp = raw_data.get("years_experience")
        if total_exp is None:
            total_exp = raw_data.get("years_of_experience")
            
        total_experience_years = 0.0
        source_used = "apollo"
        
        try:
            if total_exp is not None:
                exp_val = float(total_exp)
                if exp_val >= 0.0:
                    total_experience_years = exp_val
                else:
                    raise ValueError("Negative experience years")
            else:
                raise ValueError("Experience years is None")
        except (ValueError, TypeError):
            total_experience_years = history_total
            source_used = "experience_history"

        # Override total experience if chronological history shows a larger duration
        if history_total > total_experience_years:
            total_experience_years = history_total
            source_used = "experience_history_override"
            
        logger.debug(f"Computed total_experience_years = {total_experience_years:.2f} using source '{source_used}'")
        
        # 5. relevant_experience_years
        relevant_experience_years = 0.0
        try:
            from rapidfuzz import fuzz
            relevant_intervals = []
            for job in profile.experience:
                job_title = job.title
                if not job_title:
                    continue
                    
                # Match title against target titles
                scores = [fuzz.token_set_ratio(job_title.lower(), t.lower()) for t in target_titles]
                max_score = max(scores) if scores else 0.0
                
                if max_score >= FUZZY_MATCH_THRESHOLD:
                    start = job.start_date
                    end = job.end_date
                    s_frac = parse_date_to_year_fraction(start)
                    e_frac = parse_date_to_year_fraction(end, default_now=job.is_current)
                    if s_frac is None or e_frac is None:
                        logger.warning(
                            f"Skipping relevant experience item '{job.title}' at '{job.company_name or 'Unknown'}' "
                            f"due to unparseable dates: start='{start}', end='{end}'"
                        )
                        continue
                    relevant_intervals.append((s_frac, e_frac))
                    
            merged_relevant = merge_intervals(relevant_intervals)
            relevant_experience_years = sum(max(0.0, end_f - start_f) for start_f, end_f in merged_relevant)
            
            # Enforce mathematical subset constraint (Fix 5)
            if relevant_experience_years > total_experience_years:
                logger.warning(
                    f"relevant_experience_years ({relevant_experience_years:.2f}) exceeded "
                    f"total_experience_years ({total_experience_years:.2f}) before clamping — "
                    f"this should not happen after interval-merge fix; investigate candidate {profile.basic_info}."
                )
                relevant_experience_years = total_experience_years
        except Exception as e:
            logger.error(f"Failed to calculate relevant_experience_years: {e}")
            
        # 6. territory_match
        territory_match = 0.0
        cand_location = profile.basic_info.location or ""
        if cand_location:
            territory_match = check_territory_match(cand_location, target_territory)

        # 7. about_semantic_sim
        about_semantic_sim_raw = 0.0
        candidate_about = (profile.summary.about if profile.summary else None) or profile.basic_info.headline or ""
        jd_text = spec.jd_requirements_text or ""
        if candidate_about and jd_text:
            try:
                about_semantic_sim_raw = _semantic_embedder.compute_max_similarity(candidate_about, [jd_text])
            except Exception as e:
                logger.error(f"Failed to calculate about_semantic_sim: {e}")
        else:
            if not jd_text:
                logger.warning("jd_requirements_text is missing or empty in JDSearchSpec — returning 0.0 for about_semantic_sim")

        about_semantic_sim = rescale_similarity(
            about_semantic_sim_raw,
            ABOUT_SEMANTIC_SIM_FLOOR,
            ABOUT_SEMANTIC_SIM_CEILING
        )

        # 8. experience_semantic_sim
        experience_semantic_sim_raw = 0.0
        exp_text_parts = [
            f"{job.title or ''} at {job.company_name or ''}. {job.description or ''}".strip()
            for job in profile.experience
            if job.description or job.title
        ]
        candidate_experience_text = " ".join(exp_text_parts)[:2000]
        if candidate_experience_text and jd_text:
            try:
                experience_semantic_sim_raw = _semantic_embedder.compute_max_similarity(candidate_experience_text, [jd_text])
            except Exception as e:
                logger.error(f"Failed to calculate experience_semantic_sim: {e}")
        else:
            if not jd_text:
                logger.warning("jd_requirements_text is missing or empty in JDSearchSpec — returning 0.0 for experience_semantic_sim")

        experience_semantic_sim = rescale_similarity(
            experience_semantic_sim_raw,
            EXP_SEMANTIC_SIM_FLOOR,
            EXP_SEMANTIC_SIM_CEILING
        )

        # (Role name match removed and weights redistributed)

        return CandidateFeatures(
            title_keyword_match=title_keyword_match,
            title_semantic_sim=title_semantic_sim,
            about_semantic_sim=about_semantic_sim,
            about_semantic_sim_raw=about_semantic_sim_raw,
            experience_semantic_sim=experience_semantic_sim,
            experience_semantic_sim_raw=experience_semantic_sim_raw,
            total_experience_years=total_experience_years,
            relevant_experience_years=relevant_experience_years,
            territory_match=territory_match
        )


def add_engineered_metrics(profile: CandidateProfile, spec: JDSearchSpec) -> dict:
    """Helper to compute features and a custom feature-engineered fitment score (0-100)."""
    service = FeatureEngineeringService()
    features = service.compute_features(profile, spec)
    if not features:
        return {}
        
    title_kw = features.title_keyword_match or 0.0
    title_sem = features.title_semantic_sim or 0.0
    about_sem = features.about_semantic_sim or 0.0
    experience_sem = features.experience_semantic_sim or 0.0
    total_exp = features.total_experience_years or 0.0
    relevant_exp = features.relevant_experience_years or 0.0
    territory = features.territory_match or 0.0
    
    min_exp = spec.min_experience_years or 2
    total_exp_points = min(10.0, (total_exp / min_exp) * 10.0) if min_exp > 0 else 10.0
    relevant_exp_points = min(10.0, relevant_exp * RELEVANT_EXP_MULTIPLIER)  # Scaled using database-derived multiplier (cap restored to 10)
    territory_points = territory * 10.0  # cap restored to 10
    
    eng_score = (
        (title_kw * 20.0) +             # JD title matches: increased weight from 10 -> 15
        (title_sem * 25.0) +            # Semantic similarities: remains 20
        (about_sem * 10.0) +            # Semantic similarities: remains 20
        (experience_sem * 15.0) +       # Semantic similarities: remains 15
        total_exp_points +              # remains 10 (capped)
        relevant_exp_points +           # cap restored to 10
        territory_points                # cap restored to 10
    )
    eng_score = min(100.0, max(0.0, float(eng_score)))
    
    return {
        "engineered_features": features.model_dump(),
        "engineered_fitment_score": eng_score
    }


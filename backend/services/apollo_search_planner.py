"""Apollo Search Planner — Converts parsed JD specifications to structured query filters."""

from typing import Dict, Any, List
from loguru import logger
from models.schemas import JDSearchSpec


def clean_geo_locations_for_apollo(geo_keywords: List[str]) -> List[str]:
    """Filter out non-geographic keywords (e.g. Remote, Hybrid) leaving real geographic entities."""
    non_geo = {
        "remote", "us remote", "remote us", "remote-first", "anywhere",
        "global", "worldwide", "hybrid", "work from home", "wfh", "all",
        "unspecified", "any", "remote - global", "remote (global)"
    }
    cleaned = []
    for g in geo_keywords:
        if not g:
            continue
        g_clean = g.strip()
        if g_clean.lower() not in non_geo and not g_clean.lower().startswith("remote"):
            # Clean trailing (Remote) or (Hybrid) suffixes e.g., "India (Remote)" -> "India"
            g_clean = g_clean.split("(")[0].strip()
            if g_clean and g_clean.lower() not in non_geo:
                cleaned.append(g_clean)
    return cleaned


VALID_APOLLO_SENIORITIES = {
    "owner", "founder", "c_suite", "partner", "vp", "head", "director", "manager", "senior", "entry"
}

SENIORITY_ALIAS_MAP = {
    "fresher": "entry",
    "freshers": "entry",
    "entry-level": "entry",
    "entry level": "entry",
    "entry_level": "entry",
    "junior": "entry",
    "jr": "entry",
    "intern": "entry",
    "trainee": "entry",
    "associate": "entry",
    "lead": "senior",
    "sr": "senior",
    "principal": "senior",
    "staff": "senior",
    "c-suite": "c_suite",
    "c_suite": "c_suite",
    "cxo": "c_suite",
    "vp": "vp",
    "vice president": "vp",
    "head": "head",
    "director": "director",
    "manager": "manager",
    "owner": "owner",
    "founder": "founder",
    "partner": "partner",
}


def normalize_seniority_for_apollo(seniorities: List[str]) -> List[str]:
    """Map arbitrary user/LLM seniority strings into valid Apollo seniority filters."""
    result = set()
    for s in seniorities:
        if not s:
            continue
        cleaned = s.strip().lower()
        if cleaned in VALID_APOLLO_SENIORITIES:
            result.add(cleaned)
        elif cleaned in SENIORITY_ALIAS_MAP and SENIORITY_ALIAS_MAP[cleaned]:
            result.add(SENIORITY_ALIAS_MAP[cleaned])
    return list(result)


class ApolloSearchPlanner:
    """Intelligently compiles job search specifications into optimized Apollo query filters."""

    def compile_filters(self, spec: JDSearchSpec, broadening_level: int = 0) -> Dict[str, Any]:
        """Convert parsed JDSearchSpec to Apollo filters JSON structure.
        
        broadening_level: 0 (strict), 1 (broad titles/skills/drop email filter), 2 (widest search)
        """
        logger.info(f"[Apollo Search Planner] Compiling filters with broadening_level={broadening_level}")
        
        # Primary titles mapping
        titles = list(spec.primary_titles) if spec.primary_titles else []
        
        if not titles and spec.target_titles:
            titles = list(spec.target_titles)

        # Fallback to role_name only if primary_titles is completely empty
        if not titles and spec.role_name:
            from nlp.title_taxonomy import clean_role_name_for_search
            cleaned_role_titles = clean_role_name_for_search(spec.role_name)
            for rt in cleaned_role_titles:
                if rt and rt not in titles:
                    titles.append(rt)

        if broadening_level >= 1 and spec.related_titles:
            for rt in spec.related_titles:
                if rt and rt not in titles:
                    titles.append(rt)
                    
        logger.info(f"Apollo search titles: {titles[:5]}")
            
        # Locations mapping — clean non-geographic keywords like Remote
        locations = clean_geo_locations_for_apollo(spec.geo_keywords or [])
        if not locations and spec.target_territory:
            locs = clean_geo_locations_for_apollo([spec.target_territory])
            if locs:
                locations = locs

        # Seniority levels mapping: normalize to valid Apollo seniorities
        raw_seniorities = spec.seniority_levels if spec.seniority_levels else []
        mapped_seniorities = normalize_seniority_for_apollo(raw_seniorities)

        # In broadening level 0 and 1, use mapped seniorities if available.
        # In broadening level >= 2, drop seniority filter to maximize discovery across untagged profiles.
        if broadening_level >= 2:
            seniority = []
        else:
            seniority = mapped_seniorities

        # Skills / Keywords mapping:
        # In Apollo, q_keywords is a strict boolean text search. Concatenating multiple multi-word skills
        # causes Apollo to return 0 results because almost no candidate has all words in their summary.
        # Only use q_keywords if titles are completely absent.
        q_keywords = ""
        if not titles and spec.required_skills:
            q_keywords = spec.required_skills[0]

        filters = {
            "person_titles": titles,
            "person_locations": locations,
            "page": 1,
            "per_page": 25,
        }
        if q_keywords:
            filters["q_keywords"] = q_keywords
        if seniority:
            filters["person_seniorities"] = seniority
        
        # In strict level 0, prioritize verified emails; in broader levels, relax constraint
        if broadening_level == 0:
            filters["contact_email_status"] = ["verified", "likely to engage"]
        
        logger.debug(f"[Apollo Search Planner] Active filters compiled: {filters}")
        return filters

"""Apollo Search Planner — Converts parsed JD specifications to structured query filters."""

from typing import Dict, Any, List
from loguru import logger
from models.schemas import JDSearchSpec


def clean_geo_locations_for_apollo(geo_keywords: List[str]) -> List[str]:
    """Filter out non-geographic keywords (e.g. Remote, Hybrid) leaving real geographic entities."""
    non_geo = {
        "remote", "us remote", "remote us", "remote-first", "anywhere",
        "global", "worldwide", "hybrid", "work from home", "wfh", "all",
        "unspecified", "any"
    }
    cleaned = []
    for g in geo_keywords:
        if not g:
            continue
        g_clean = g.strip()
        if g_clean.lower() not in non_geo:
            cleaned.append(g_clean)
    return cleaned


class ApolloSearchPlanner:
    """Intelligently compiles job search specifications into optimized Apollo query filters."""

    def compile_filters(self, spec: JDSearchSpec, broadening_level: int = 0) -> Dict[str, Any]:
        """Convert parsed JDSearchSpec to Apollo filters JSON structure.
        
        broadening_level: 0 (strict), 1 (broad titles/skills/drop email filter), 2 (widest search)
        """
        logger.info(f"[Apollo Search Planner] Compiling filters with broadening_level={broadening_level}")
        
        # Primary titles mapping (unify role_name and parsed primary titles)
        from nlp.title_taxonomy import clean_role_name_for_search
        titles = list(spec.primary_titles) if spec.primary_titles else []
        
        if spec.role_name:
            cleaned_role_titles = clean_role_name_for_search(spec.role_name)
            for rt in cleaned_role_titles:
                if rt and rt not in titles:
                    titles.append(rt)
                    
        if not titles and spec.target_titles:
            titles = list(spec.target_titles)

        if broadening_level >= 1 and spec.related_titles:
            for rt in spec.related_titles:
                if rt and rt not in titles:
                    titles.append(rt)
                    
        logger.info(f"Apollo search titles: {titles[:5]}")
            
        # Locations mapping — clean non-geographic keywords like Remote
        locations = clean_geo_locations_for_apollo(spec.geo_keywords or [])

        # Skills mapping
        skills = spec.required_skills.copy() if spec.required_skills else []
        if broadening_level == 1 and len(skills) > 3:
            skills = skills[:3]
        elif broadening_level >= 2:
            skills = []  # Drop keyword constraint to maximize discovery

        # Seniority levels
        seniority = [s.lower() for s in spec.seniority_levels] if spec.seniority_levels else ["senior", "mid"]
        if broadening_level >= 2:
            seniority.extend(["entry", "director"])
            seniority = list(set(seniority))

        filters = {
            "person_titles": titles,
            "person_locations": locations,
            "q_keywords": " ".join(skills[:5]) if skills else "",
            "person_seniorities": seniority,
            "page": 1,
            "per_page": 25,
        }
        
        # In strict level 0, prioritize verified emails; in broader levels, relax constraint
        if broadening_level == 0:
            filters["contact_email_status"] = ["verified", "likely to engage"]
        
        logger.debug(f"[Apollo Search Planner] Active filters compiled: {filters}")
        return filters

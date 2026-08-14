"""Apollo Search Planner — Converts parsed JD specifications to structured query filters."""

from typing import Dict, Any, List
from loguru import logger
from models.schemas import JDSearchSpec


class ApolloSearchPlanner:
    """Intelligently compiles job search specifications into optimized Apollo query filters."""

    def compile_filters(self, spec: JDSearchSpec, broadening_level: int = 0) -> Dict[str, Any]:
        """Convert parsed JDSearchSpec to Apollo filters JSON structure.
        
        broadening_level: 0 (strict), 1 (broad titles/skills), 2 (widest target location & seniorities)
        """
        logger.info(f"[Apollo Search Planner] Compiling filters with broadening_level={broadening_level}")
        
        # Primary titles mapping
        from nlp.title_taxonomy import clean_role_name_for_search
        if broadening_level == 0 and spec.role_name:
            titles = clean_role_name_for_search(spec.role_name)
        else:
            titles = spec.primary_titles.copy()
            
        logger.info(f"Apollo search titles (incl. role_name if provided): {titles[:5]}")
        if broadening_level >= 1:
            titles.extend(spec.related_titles)
            
        # Locations mapping
        locations = spec.geo_keywords.copy()
        if not locations or broadening_level >= 2:
            locations = ["United States", "Remote US", "USA"]

        # Skills mapping
        skills = spec.required_skills.copy()
        if broadening_level >= 1 and len(skills) > 3:
            # Narrow down to primary 3 skills to broaden search results
            skills = skills[:3]

        # Seniority levels
        seniority = [s.lower() for s in spec.seniority_levels] if spec.seniority_levels else ["senior", "mid"]
        if broadening_level >= 2:
            seniority.extend(["entry", "director"])
            seniority = list(set(seniority))

        filters = {
            "person_titles": titles,
            "person_locations": locations,
            "q_keywords": " ".join(skills[:5]),
            "person_seniorities": seniority,
            "page": 1,
            "per_page": 25,
            "contact_email_status": ["verified", "likely to engage"],
        }
        
        logger.debug(f"[Apollo Search Planner] Active filters compiled: {filters}")
        return filters

"""
Apollo Service — People Search + Contact Enrichment

Prod mode (APOLLO_API_KEY set): calls Apollo.io People Search API with progressive search broadening.
If key is missing or search returns 0 matches, returns empty list with clear logging (no synthetic mock profiles).

Apollo endpoint: POST https://api.apollo.io/v1/mixed_people/api_search
Docs: https://apolloio.github.io/apollo-api-docs/
"""

import json
import os
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from models.schemas import JDSearchSpec, LegacyCandidateProfile
from services.apollo_search_planner import ApolloSearchPlanner
from config import get_settings

settings = get_settings()

APOLLO_BASE = "https://api.apollo.io/v1"
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".apollo_token.json")


def get_apollo_auth() -> tuple[dict, bool]:
    """
    Return the authentication headers and whether it's in production mode.
    Returns: (headers, is_prod)
    """
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                token_data = json.load(f)
            access_token = token_data.get("access_token")
            if access_token:
                return {
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache",
                    "Authorization": f"Bearer {access_token}",
                }, True
        except Exception as e:
            logger.error(f"Error reading OAuth token file: {e}")

    if settings.apollo_api_key and settings.apollo_api_key.strip():
        return {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": settings.apollo_api_key.strip(),
        }, True

    return {}, False


def _to_candidate_profile(raw: dict) -> LegacyCandidateProfile:
    """Convert a raw dict from Apollo to LegacyCandidateProfile."""
    return LegacyCandidateProfile(
        linkedin_url=raw.get("linkedin_url", ""),
        full_name=raw.get("full_name", "Unknown"),
        headline=raw.get("headline", ""),
        current_company=raw.get("current_company", ""),
        current_title=raw.get("current_title", ""),
        location=raw.get("location", ""),
        years_experience=raw.get("years_experience"),
        skills=raw.get("skills", []),
        is_open_to_work=raw.get("is_open_to_work", False),
        email=raw.get("email"),
        phone=raw.get("phone"),
        source=raw.get("source", "apollo"),
        raw_data=raw,
    )


def _map_seniority_levels(levels: list[str]) -> list[str]:
    """Map parsed seniority levels to valid Apollo seniority strings."""
    if not levels:
        return []
        
    apollo_valid = {"owner", "founder", "c_suite", "partner", "vp", "head", "director", "manager", "senior", "entry", "intern"}
    mapped = set()
    for lvl in levels:
        lvl_lower = lvl.lower().strip()
        if "mid" in lvl_lower:
            mapped.update(["senior", "manager", "entry"])
        elif "junior" in lvl_lower or "entry" in lvl_lower:
            mapped.add("entry")
        elif "senior" in lvl_lower or "lead" in lvl_lower:
            mapped.update(["senior", "manager"])
        elif "director" in lvl_lower:
            mapped.add("director")
        elif "vp" in lvl_lower or "vice president" in lvl_lower:
            mapped.add("vp")
        elif "exec" in lvl_lower or "c-level" in lvl_lower or "c_level" in lvl_lower or "ceo" in lvl_lower:
            mapped.update(["c_suite", "vp"])
        elif lvl_lower in apollo_valid:
            mapped.add(lvl_lower)
            
    return list(mapped)


def _get_search_keyword(skills: list[str]) -> str:
    """Filter out soft skills and return the best keyword for search."""
    soft_skills = {
        "communication", "interpersonal", "verbal", "writing", "teamwork", 
        "analytical", "organization", "negotiation", "presentation",
        "problem solving", "leadership", "time management", "flexibility"
    }
    tech_skills = [s for s in skills if s.lower().strip() not in soft_skills]
    return tech_skills[0] if tech_skills else (skills[0] if skills else "")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(ValueError)
)
async def apollo_search(spec: JDSearchSpec, max_results: int = 25) -> list[LegacyCandidateProfile]:
    """
    Search Apollo.io People API with multi-tier progressive query relaxation.
    Returns real candidate profiles or an empty list if no results are found.
    """
    headers, is_prod = get_apollo_auth()
    if not is_prod:
        logger.warning("APOLLO_API_KEY is not configured — returning 0 candidates. Configure APOLLO_API_KEY in .env to enable real sourcing.")
        return []

    planner = ApolloSearchPlanner()
    people = []

    # Progressive search broadening: Level 0 (Targeted), Level 1 (Relaxed), Level 2 (Widest)
    for broadening_level in range(3):
        filters = planner.compile_filters(spec, broadening_level=broadening_level)
        
        payload = {
            "person_titles": filters.get("person_titles", []),
            "page": 1,
            "per_page": min(max_results, 100),
        }
        
        # Only attach geographic locations if real locations are present
        if filters.get("person_locations"):
            payload["person_locations"] = filters["person_locations"]
            
        if filters.get("q_keywords"):
            payload["q_keywords"] = filters["q_keywords"]
            
        if filters.get("person_seniorities"):
            payload["person_seniorities"] = filters["person_seniorities"]
            
        if filters.get("contact_email_status"):
            payload["contact_email_status"] = filters["contact_email_status"]
            
        if hasattr(spec, "currently_using_technology_uids") and spec.currently_using_technology_uids:
            payload["currently_using_any_of_technology_uids"] = [
                t.lower().strip().replace(" ", "_").replace(".", "_")
                for t in spec.currently_using_technology_uids
                if t.strip()
            ]

        logger.info(f"[Apollo Search] Querying Apollo (Level {broadening_level}): titles={payload.get('person_titles', [])[:3]}, locations={payload.get('person_locations', [])[:3]}, keywords={payload.get('q_keywords', '')}")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{APOLLO_BASE}/mixed_people/api_search",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                people = data.get("people", [])
                
            if people:
                logger.info(f"[Apollo Search] Level {broadening_level} returned {len(people)} candidates.")
                break
            else:
                logger.warning(f"[Apollo Search] Level {broadening_level} returned 0 results. Broadening query filters...")
        except Exception as e:
            logger.error(f"[Apollo Search] Apollo API request failed at Level {broadening_level}: {e}")
            if broadening_level == 2:
                break

    if not people:
        logger.info(f"Apollo search returned 0 candidates for role '{spec.role_name or (spec.primary_titles[0] if spec.primary_titles else 'specified role')}'.")
        return []

    profiles = []
    for person in people:
        employment_history = person.get("employment_history", [])
        current_job = employment_history[0] if employment_history else {}

        years = 0
        for job in employment_history:
            start = job.get("start_date") or ""
            end = job.get("end_date") or ""
            try:
                s_year = int(start[:4]) if start else 2020
                e_year = int(end[:4]) if end else 2024
                years += max(0, e_year - s_year)
            except (ValueError, TypeError):
                pass

        # Handle name fallback (mixed_people/api_search obfuscates last name)
        name = person.get("name")
        if not name:
            first = person.get("first_name") or ""
            last = person.get("last_name") or person.get("last_name_obfuscated") or ""
            name = f"{first} {last}".strip() or "Unknown"

        # Handle company name fallback
        org_name = person.get("organization_name") or person.get("organization", {}).get("name") or current_job.get("organization_name") or ""

        profiles.append(LegacyCandidateProfile(
            linkedin_url=person.get("linkedin_url", "") or f"https://linkedin.com/in/{person.get('id', '')}",
            full_name=name,
            headline=person.get("headline", "") or person.get("title", ""),
            current_company=org_name,
            current_title=person.get("title", "") or current_job.get("title", ""),
            location=f"{person.get('city', '')}, {person.get('state', '')}, {person.get('country', '')}".strip(", "),
            years_experience=float(years) if years else None,
            skills=[s.get("name", "") for s in person.get("skills", [])],
            is_open_to_work=person.get("is_likely_to_engage", False),
            email=person.get("email"),
            phone=person.get("phone_numbers", [{}])[0].get("sanitized_number") if person.get("phone_numbers") else None,
            source="apollo",
            raw_data=person,
        ))

    return profiles


async def get_candidates(spec: JDSearchSpec, max_results: int = 25) -> tuple[list[LegacyCandidateProfile], str]:
    """
    Main entry point: returns real candidates + data source label.
    """
    headers, is_prod = get_apollo_auth()
    profiles = await apollo_search(spec, max_results)
    source_label = "apollo" if (is_prod and any(p.source == "apollo" for p in profiles)) else ("apollo" if is_prod else "none")
    return profiles, source_label

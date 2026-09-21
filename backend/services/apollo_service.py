"""
Apollo Service — People Search + Contact Enrichment

POC mode  (APOLLO_API_KEY empty): returns realistic, role-tailored candidates.
Prod mode (APOLLO_API_KEY set):   calls Apollo.io People Search API with progressive search broadening.

Apollo endpoint: POST https://api.apollo.io/v1/mixed_people/search
Docs: https://apolloio.github.io/apollo-api-docs/
"""

import json
import os
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from models.schemas import JDSearchSpec, LegacyCandidateProfile
from services.apollo_search_planner import ApolloSearchPlanner, clean_geo_locations_for_apollo
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
    """Convert a raw dict (mock or Apollo) to CandidateProfile."""
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


def _get_mock_candidates(spec: JDSearchSpec | None = None, max_results: int = 25) -> list[LegacyCandidateProfile]:
    """
    Return realistic, role-tailored candidate profiles for POC/Demo mode or fallback.
    Adapts dynamically to the supplied JDSearchSpec job titles, skills, and target territory.
    """
    primary_title = "Software Engineer"
    if spec:
        if spec.primary_titles:
            primary_title = spec.primary_titles[0]
        elif spec.role_name:
            primary_title = spec.role_name
            
    req_skills = spec.required_skills if (spec and spec.required_skills) else ["Problem Solving", "Architecture", "Git"]
    target_cos = spec.target_companies if (spec and spec.target_companies) else ["TechCorp", "InnovateLabs", "CloudScale", "DevVenture"]
    
    # Resolve location
    geo = "Remote"
    if spec and spec.geo_keywords:
        geo_clean = clean_geo_locations_for_apollo(spec.geo_keywords)
        if geo_clean:
            geo = geo_clean[0]
        elif "remote" in [g.lower() for g in spec.geo_keywords]:
            geo = "Remote"
    elif spec and spec.target_territory:
        geo = spec.target_territory

    templates = [
        {
            "first_name": "Sarah", "last_name": "Johnson", "years": 5.5,
            "title_mod": f"Senior {primary_title}", "company": target_cos[0] if len(target_cos) > 0 else "Stripe",
            "loc_offset": "Austin, TX, USA" if geo in ("Remote", "") else geo, "open": True
        },
        {
            "first_name": "Priya", "last_name": "Sharma", "years": 4.0,
            "title_mod": primary_title, "company": target_cos[1] if len(target_cos) > 1 else "Google",
            "loc_offset": "London, UK" if geo in ("Remote", "") else geo, "open": True
        },
        {
            "first_name": "Alex", "last_name": "Rivera", "years": 6.0,
            "title_mod": f"Lead {primary_title}", "company": target_cos[2] if len(target_cos) > 2 else "Microsoft",
            "loc_offset": "San Francisco, CA, USA" if geo in ("Remote", "") else geo, "open": False
        },
        {
            "first_name": "Michael", "last_name": "Chen", "years": 3.5,
            "title_mod": primary_title, "company": target_cos[3] if len(target_cos) > 3 else "Amazon",
            "loc_offset": "Toronto, Canada" if geo in ("Remote", "") else geo, "open": True
        },
        {
            "first_name": "Elena", "last_name": "Rostova", "years": 7.0,
            "title_mod": f"Principal {primary_title}", "company": target_cos[0] if len(target_cos) > 0 else "Datadog",
            "loc_offset": "Berlin, Germany" if geo in ("Remote", "") else geo, "open": True
        },
    ]

    profiles = []
    for idx, item in enumerate(templates[:max_results]):
        full_name = f"{item['first_name']} {item['last_name']}"
        slug = f"{item['first_name'].lower()}-{item['last_name'].lower()}-{idx+1}"
        
        mock_raw = {
            "id": f"mock-{idx+1}",
            "first_name": item["first_name"],
            "last_name": item["last_name"],
            "name": full_name,
            "headline": f"{item['title_mod']} at {item['company']} | {', '.join(req_skills[:3])}",
            "title": item["title_mod"],
            "organization_name": item["company"],
            "city": item["loc_offset"].split(",")[0].strip(),
            "state": item["loc_offset"].split(",")[1].strip() if len(item["loc_offset"].split(",")) > 1 else "",
            "country": item["loc_offset"].split(",")[-1].strip() if len(item["loc_offset"].split(",")) > 2 else item["loc_offset"],
            "skills": [{"name": s} for s in req_skills[:6]],
            "is_likely_to_engage": item["open"],
            "email": f"{item['first_name'].lower()}.{item['last_name'][0].lower()}@sample-recruit.com",
            "linkedin_url": f"https://linkedin.com/in/{slug}",
            "employment_history": [
                {"title": item["title_mod"], "organization_name": item["company"], "start_date": "2021-01", "is_current": True}
            ]
        }

        profiles.append(LegacyCandidateProfile(
            linkedin_url=mock_raw["linkedin_url"],
            full_name=full_name,
            headline=mock_raw["headline"],
            current_company=item["company"],
            current_title=item["title_mod"],
            location=item["loc_offset"],
            years_experience=item["years"],
            skills=req_skills[:6],
            is_open_to_work=item["open"],
            email=mock_raw["email"],
            phone=None,
            source="mock",
            raw_data=mock_raw,
        ))
        
    return profiles


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(ValueError)
)
async def apollo_search(spec: JDSearchSpec, max_results: int = 25) -> list[LegacyCandidateProfile]:
    """
    Search Apollo.io People API with multi-tier progressive query relaxation.
    Returns dynamic role-tailored mock candidates if APOLLO_API_KEY is not configured or if Apollo yields 0 results.
    """
    headers, is_prod = get_apollo_auth()
    if not is_prod:
        logger.info(f"APOLLO_API_KEY not set — using realistic mock candidates tailored to '{spec.role_name or 'role'}'")
        return _get_mock_candidates(spec, max_results)

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

    # If Apollo still returned 0 candidates after all broadening levels, fallback to dynamic mock candidates
    if not people:
        logger.warning(f"Apollo search returned 0 candidates across all broadening levels — providing calibrated candidates for '{spec.role_name or 'role'}'")
        return _get_mock_candidates(spec, max_results)

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
    Main entry point: returns candidates + data source label.
    Supports both real Apollo search and realistic mock fallback.
    """
    headers, is_prod = get_apollo_auth()
    profiles = await apollo_search(spec, max_results)
    source_label = "apollo" if (is_prod and any(p.source == "apollo" for p in profiles)) else "mock"
    return profiles, source_label

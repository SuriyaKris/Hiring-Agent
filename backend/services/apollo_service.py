"""
Apollo Service — People Search + Contact Enrichment

POC mode  (APOLLO_API_KEY empty): returns realistic mock US sales candidates.
Prod mode (APOLLO_API_KEY set):   calls Apollo.io People Search API.

Apollo endpoint: POST https://api.apollo.io/v1/mixed_people/search
Docs: https://apolloio.github.io/apollo-api-docs/

Cost: Apollo Starter is free (50 credits/mo). API access on custom plans.
"""

import json
import os
import httpx
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from models.schemas import JDSearchSpec, LegacyCandidateProfile
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
            "X-Api-Key": settings.apollo_api_key,
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


def _get_mock_candidates(max_results: int = 25) -> list[LegacyCandidateProfile]:
    """Return realistic mock US sales candidate profiles for POC/Demo mode."""
    mock_data = [
        {
            "id": "mock-1",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "name": "Sarah Johnson",
            "headline": "Senior Inside Sales AE | Salesforce | CRM Expert",
            "title": "Senior Inside Sales Account Executive",
            "organization_name": "Salesforce",
            "city": "Austin",
            "state": "TX",
            "country": "United States",
            "skills": [{"name": "Inside Sales"}, {"name": "Salesforce CRM"}, {"name": "SaaS"}, {"name": "Outbound"}],
            "is_likely_to_engage": True,
            "email": "sarah.j@sample.com",
            "linkedin_url": "https://linkedin.com/in/sarah-johnson-salesforce",
            "employment_history": [{"title": "Senior Inside Sales Account Executive", "organization_name": "Salesforce", "start_date": "2020-01"}]
        },
        {
            "id": "mock-2",
            "first_name": "Priya",
            "last_name": "Sharma",
            "name": "Priya Sharma",
            "headline": "US Sales Executive | Salesforce CRM | Chicago Remote",
            "title": "US Sales Executive",
            "organization_name": "ZoomInfo",
            "city": "Chicago",
            "state": "IL",
            "country": "United States",
            "skills": [{"name": "Sales Executive"}, {"name": "CRM"}, {"name": "B2B Sales"}, {"name": "Pipeline"}],
            "is_likely_to_engage": True,
            "email": "priya.s@sample.com",
            "linkedin_url": "https://linkedin.com/in/priya-sharma-salesexec",
            "employment_history": [{"title": "US Sales Executive", "organization_name": "ZoomInfo", "start_date": "2019-03"}]
        },
        {
            "id": "mock-3",
            "first_name": "James",
            "last_name": "Chen",
            "name": "James Chen",
            "headline": "Business Development Representative | HubSpot | Dallas TX",
            "title": "Business Development Representative",
            "organization_name": "HubSpot",
            "city": "Dallas",
            "state": "TX",
            "country": "United States",
            "skills": [{"name": "BDR"}, {"name": "Lead Generation"}, {"name": "SaaS"}, {"name": "Prospecting"}],
            "is_likely_to_engage": False,
            "email": "james.c@sample.com",
            "linkedin_url": "https://linkedin.com/in/james-chen-bdr-hubspot",
            "employment_history": [{"title": "Business Development Representative", "organization_name": "HubSpot", "start_date": "2021-06"}]
        },
        {
            "id": "mock-4",
            "first_name": "Ashley",
            "last_name": "Williams",
            "name": "Ashley Williams",
            "headline": "Inside Sales Rep | Salesloft | CRM | Remote US",
            "title": "Inside Sales Representative",
            "organization_name": "Salesloft",
            "city": "Atlanta",
            "state": "GA",
            "country": "United States",
            "skills": [{"name": "Inside Sales"}, {"name": "Salesloft"}, {"name": "Outreach"}, {"name": "Cold Calling"}],
            "is_likely_to_engage": True,
            "email": "ashley.w@sample.com",
            "linkedin_url": "https://linkedin.com/in/ashley-williams-salesloft",
            "employment_history": [{"title": "Inside Sales Representative", "organization_name": "Salesloft", "start_date": "2022-01"}]
        },
        {
            "id": "mock-5",
            "first_name": "Marcus",
            "last_name": "Vance",
            "name": "Marcus Vance",
            "headline": "Account Executive - Mid Market | Outreach.io | San Francisco",
            "title": "Account Executive",
            "organization_name": "Outreach.io",
            "city": "San Francisco",
            "state": "CA",
            "country": "United States",
            "skills": [{"name": "Account Executive"}, {"name": "Sales Strategy"}, {"name": "CRM"}, {"name": "Enterprise Sales"}],
            "is_likely_to_engage": True,
            "email": "marcus.v@sample.com",
            "linkedin_url": "https://linkedin.com/in/marcus-vance-outreach",
            "employment_history": [{"title": "Account Executive", "organization_name": "Outreach.io", "start_date": "2018-09"}]
        }
    ]
    profiles = []
    for item in mock_data[:max_results]:
        profiles.append(LegacyCandidateProfile(
            linkedin_url=item["linkedin_url"],
            full_name=item["name"],
            headline=item["headline"],
            current_company=item["organization_name"],
            current_title=item["title"],
            location=f"{item['city']}, {item['state']}, {item['country']}",
            years_experience=4.0,
            skills=[s["name"] for s in item["skills"]],
            is_open_to_work=item["is_likely_to_engage"],
            email=item["email"],
            phone=None,
            source="mock",
            raw_data=item,
        ))
    return profiles


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_not_exception_type(ValueError)
)
async def apollo_search(spec: JDSearchSpec, max_results: int = 25) -> list[LegacyCandidateProfile]:
    """
    Search Apollo.io People API.
    Returns mock candidates if APOLLO_API_KEY is not configured.
    """
    headers, is_prod = get_apollo_auth()
    if not is_prod:
        logger.info("APOLLO_API_KEY not set — using realistic mock US candidates for POC mode")
        return _get_mock_candidates(max_results)

    q_kw = _get_search_keyword(spec.required_skills)
    mapped_sen = _map_seniority_levels(spec.seniority_levels)

    from nlp.title_taxonomy import clean_role_name_for_search
    if spec.role_name:
        search_titles = clean_role_name_for_search(spec.role_name)
    else:
        search_titles = spec.primary_titles + spec.related_titles

    payload = {
        "person_titles": search_titles,
        "person_locations": spec.geo_keywords,
        "page": 1,
        "per_page": min(max_results, 100),
        "contact_email_status": ["verified", "likely to engage"],
    }
    
    if q_kw:
        payload["q_keywords"] = q_kw
    if mapped_sen:
        payload["person_seniorities"] = mapped_sen
    
    if hasattr(spec, "currently_using_technology_uids") and spec.currently_using_technology_uids:
        payload["currently_using_any_of_technology_uids"] = [
            t.lower().strip().replace(" ", "_").replace(".", "_")
            for t in spec.currently_using_technology_uids
            if t.strip()
        ]

    logger.info(f"Apollo search: titles={search_titles[:3]}, locations={spec.geo_keywords[:3]}, q_keywords={q_kw}, seniorities={mapped_sen}")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{APOLLO_BASE}/mixed_people/api_search",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    people = data.get("people", [])
    logger.info(f"Apollo returned {len(people)} results")

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
    source_label = "apollo" if is_prod else "mock"
    profiles = await apollo_search(spec, max_results)
    return profiles, source_label

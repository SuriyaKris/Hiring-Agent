"""Apollo Enrichment Provider implementing BaseProvider."""

from typing import Set
import httpx
from providers.base_provider import BaseProvider
from schemas.candidate_profile import CandidateProfile, CompanyDetails
from config import get_settings
from loguru import logger

settings = get_settings()


class ApolloProvider(BaseProvider):
    """Enriches candidate profiles using Apollo data (Basic Info, Company, Headline, Email)."""

    @property
    def provider_name(self) -> str:
        return "Apollo"

    @property
    def supported_fields(self) -> Set[str]:
        return {"Email", "Phone", "Location", "Headline", "LinkedIn URL", "Company"}

    @property
    def priority(self) -> int:
        return 1

    @property
    def cost(self) -> float:
        return 0.01

    @property
    def estimated_time(self) -> float:
        return 2.0

    async def can_enrich(self, profile: CandidateProfile) -> bool:
        return bool(settings.apollo_api_key) and (
            bool(profile.metadata.apollo_person_id) or
            bool(profile.basic_info.linkedin_url) or
            bool(profile.basic_info.full_name)
        )

    async def enrich(self, profile: CandidateProfile) -> CandidateProfile:
        """Fetch verified contact details and non-obfuscated name using ID lookup or match."""
        bi = profile.basic_info
        person_id = profile.metadata.apollo_person_id

        if not settings.apollo_api_key:
            logger.info(f"[Apollo Provider] No API key configured — skipping enrichment for '{bi.full_name}'")
            return profile

        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": settings.apollo_api_key,
        }

        # Define internal helper for matching attempts
        async def _try_match(client, payload_extra: dict) -> dict:
            """Attempt a /people/match call with the given identifier. Returns person dict or {}."""
            payload = {"reveal_personal_emails": True, **payload_extra}
            try:
                resp = await client.post("https://api.apollo.io/v1/people/match", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("person", {}) or {}
            except Exception as e:
                logger.error(f"[Apollo Provider] Match attempt failed for payload {payload_extra}: {e}")
            return {}

        try:
            person = {}
            match_strategy = "none"

            async with httpx.AsyncClient(timeout=15) as client:
                if person_id:
                    person = await _try_match(client, {"id": person_id})
                    if person:
                        match_strategy = "id"

                if not person and bi.linkedin_url:
                    person = await _try_match(client, {"linkedin_url": bi.linkedin_url})
                    if person:
                        match_strategy = "linkedin_url"

                if not person and bi.full_name:
                    person = await _try_match(client, {"name": bi.full_name})
                    if person:
                        match_strategy = "name"

            logger.info(f"[Apollo Provider] Enrichment for '{bi.full_name}' resolved via strategy='{match_strategy}'")

            if not person:
                logger.info(f"[Apollo Provider] No matching details found for '{bi.full_name}' — returning original profile.")
                return profile

            # Update full name (de-obfuscates the last name from mixed_people/api_search)
            name = person.get("name")
            if not name:
                first = person.get("first_name") or ""
                last = person.get("last_name") or ""
                name = f"{first} {last}".strip()
            if name:
                bi.full_name = name
                if person.get("first_name"):
                    bi.first_name = person.get("first_name")
                if person.get("last_name"):
                    bi.last_name = person.get("last_name")

            # Populate details
            if not bi.email and person.get("email"):
                bi.email = person.get("email")
            if not bi.phone:
                phone_list = person.get("phone_numbers", [])
                bi.phone = phone_list[0].get("sanitized_number") if phone_list else ""
            if not bi.location:
                loc = f"{person.get('city', '')}, {person.get('state', '')}, {person.get('country', '')}".strip(", ")
                if loc:
                    bi.location = loc
            if not bi.headline:
                bi.headline = person.get("headline") or person.get("title")
                
            # Store Apollo IDs and raw details
            profile.metadata.apollo_person_id = person.get("id")
            profile.metadata.apollo_organization_id = person.get("organization_id") or (person.get("organization") or {}).get("id")
            profile.metadata.raw_data = person
            
            # Map skills, experience, education, summary from matched person details
            try:
                from services.candidate_enrichment import CandidateEnrichmentService
                import providers.apollo_mapper
                norm_profile = CandidateEnrichmentService().enrich(person, "apollo")
                if not profile.experience and norm_profile.experience:
                    profile.experience = norm_profile.experience
                if not profile.skills and norm_profile.skills:
                    profile.skills = norm_profile.skills
                if not profile.education and norm_profile.education:
                    profile.education = norm_profile.education
                if (not profile.summary or not profile.summary.about) and norm_profile.summary:
                    profile.summary = norm_profile.summary
            except Exception as ex:
                logger.error(f"[Apollo Provider] Failed to normalize matched person payload: {ex}")

            if person.get("linkedin_url"):
                bi.linkedin_url = person.get("linkedin_url")
            
            # Populate company details if missing
            org = person.get("organization") or {}
            if not profile.company or not profile.company.name:
                org_name = org.get("name") or person.get("organization_name") or ""
                if org_name:
                    profile.company = CompanyDetails(
                        name=str(org_name),
                        website=str(org.get("website_url") or ""),
                        size=str(org.get("estimated_num_employees")) if org.get("estimated_num_employees") is not None else "",
                        industry=str(org.get("primary_industry") or ""),
                        domain=str(org.get("primary_domain") or ""),
                    )

            # Set field sources
            profile.metadata.field_sources["email"] = self.provider_name
            profile.metadata.field_sources["phone"] = self.provider_name
            profile.metadata.field_sources["location"] = self.provider_name
            profile.metadata.field_sources["headline"] = self.provider_name
            profile.metadata.field_sources["company"] = self.provider_name

        except Exception as e:
            logger.error(f"[Apollo Provider] Enrichment lookup failed: {e}")

        # Track execution
        raw = profile.metadata.raw_data or {}
        executed = raw.setdefault("executed_providers", [])
        if self.provider_name not in executed:
            executed.append(self.provider_name)
        profile.metadata.raw_data = raw

        return profile

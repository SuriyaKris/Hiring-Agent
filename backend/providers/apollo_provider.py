"""Apollo Enrichment Provider implementing BaseProvider."""

from typing import Set
import asyncio
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

    async def enrich(self, profile: CandidateProfile, poll_phone: bool = True) -> CandidateProfile:
        """Fetch verified contact details, personal email, and phone numbers using Apollo match & polling."""
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

        webhook_url = settings.effective_apollo_webhook_url

        # Define internal helper for matching attempts
        async def _try_match(client, payload_extra: dict) -> tuple[dict, str | None]:
            """Attempt a /people/match call with the given identifier. Returns (person_dict, request_id_str)."""
            payload = {
                "reveal_personal_emails": True,
                "reveal_phone_number": True,
                "webhook_url": webhook_url,
                **payload_extra
            }
            try:
                resp = await client.post("https://api.apollo.io/v1/people/match", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    person_dict = data.get("person", {}) or {}
                    req_id_str = data.get("request_id_str") or (str(data.get("request_id")) if data.get("request_id") else None)
                    return person_dict, req_id_str
                else:
                    logger.warning(f"[Apollo Provider] Match returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.error(f"[Apollo Provider] Match attempt failed for payload {payload_extra}: {e}")
            return {}, None

        async def _poll_phone_result(client, req_id: str) -> list:
            """Poll Apollo /v1/webhook_result/{request_id} for phone waterfall results."""
            if not req_id:
                return []
            for attempt in range(2):
                await asyncio.sleep(7 if attempt == 0 else 5)
                try:
                    poll_resp = await client.get(
                        f"https://api.apollo.io/v1/webhook_result/{req_id}",
                        headers=headers,
                        timeout=12.0
                    )
                    if poll_resp.status_code == 200:
                        poll_data = poll_resp.json()
                        wr = poll_data.get("webhook_result") or {}
                        people = wr.get("people") or poll_data.get("people") or []
                        if people and isinstance(people, list):
                            phones = people[0].get("phone_numbers") or []
                            if phones:
                                return phones
                    elif poll_resp.status_code == 404:
                        continue
                except Exception as ex:
                    logger.debug(f"[Apollo Provider] Phone poll attempt {attempt+1} error: {ex}")
            return []

        try:
            person = {}
            request_id_str = None
            match_strategy = "none"

            async with httpx.AsyncClient(timeout=30) as client:
                if person_id:
                    person, request_id_str = await _try_match(client, {"id": person_id})
                    if person:
                        match_strategy = "id"

                if not person and bi.linkedin_url:
                    person, request_id_str = await _try_match(client, {"linkedin_url": bi.linkedin_url})
                    if person:
                        match_strategy = "linkedin_url"

                if not person and bi.full_name:
                    person, request_id_str = await _try_match(client, {"name": bi.full_name})
                    if person:
                        match_strategy = "name"

                logger.info(f"[Apollo Provider] Enrichment for '{bi.full_name}' resolved via strategy='{match_strategy}' (phone_req_id={request_id_str})")

                if not person:
                    logger.info(f"[Apollo Provider] No matching details found for '{bi.full_name}' — returning original profile.")
                    return profile

                # If phone numbers are pending and poll_phone is requested, poll Apollo webhook_result
                phone_list = person.get("phone_numbers") or []
                if not phone_list and request_id_str and poll_phone:
                    logger.info(f"[Apollo Provider] Polling phone enrichment for '{bi.full_name}' (request_id={request_id_str})...")
                    polled_phones = await _poll_phone_result(client, request_id_str)
                    if polled_phones:
                        person["phone_numbers"] = polled_phones

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

            # Populate contact details (Prioritizing personal email over corporate email)
            raw_personal = person.get("personal_emails") or []
            personal_email = raw_personal[0] if (isinstance(raw_personal, list) and raw_personal) else (person.get("personal_email") or None)
            work_email = person.get("email") or None

            PERSONAL_EMAIL_DOMAINS = {
                "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
                "me.com", "aol.com", "proton.me", "protonmail.com", "zoho.com",
                "mail.com", "yandex.com", "gmx.com", "live.com", "msn.com"
            }
            if work_email and any(work_email.lower().endswith("@" + d) for d in PERSONAL_EMAIL_DOMAINS):
                if not personal_email:
                    personal_email = work_email

            if personal_email:
                bi.personal_email = personal_email
                bi.email = personal_email  # Prioritize personal email as candidate's primary email!
            elif work_email:
                if not bi.email or not getattr(bi, "personal_email", None):
                    bi.email = work_email

            if work_email:
                bi.corporate_email = work_email

            # Phone numbers (sanitized mobile or office phone)
            phone_list = person.get("phone_numbers") or []
            sanitized_phone = None
            if isinstance(phone_list, list) and phone_list:
                for p in phone_list:
                    if isinstance(p, dict):
                        sanitized_phone = p.get("sanitized_number") or p.get("raw_number")
                    elif isinstance(p, str) and p.strip():
                        sanitized_phone = p.strip()
                    if sanitized_phone:
                        break
            if sanitized_phone:
                bi.phone = sanitized_phone
            elif not bi.phone and person.get("sanitized_phone"):
                bi.phone = person.get("sanitized_phone")

            if not bi.location:
                loc = f"{person.get('city', '')}, {person.get('state', '')}, {person.get('country', '')}".strip(", ")
                if loc:
                    bi.location = loc
            if not bi.headline:
                bi.headline = person.get("headline") or person.get("title")
                
            # Store Apollo IDs and raw details
            profile.metadata.apollo_person_id = person.get("id")
            profile.metadata.apollo_organization_id = person.get("organization_id") or (person.get("organization") or {}).get("id")
            if request_id_str:
                person["apollo_phone_request_id"] = request_id_str
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

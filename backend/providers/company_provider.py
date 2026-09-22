"""Company Enrichment Provider implementing BaseProvider."""

from typing import Set
from providers.base_provider import BaseProvider
from schemas.candidate_profile import CandidateProfile, CompanyDetails


class CompanyProvider(BaseProvider):
    """Enriches candidate profiles with firmographic details about their employer (Company)."""

    @property
    def provider_name(self) -> str:
        return "Company"

    @property
    def supported_fields(self) -> Set[str]:
        return {"Company"}

    @property
    def priority(self) -> int:
        return 5

    @property
    def cost(self) -> float:
        return 0.01

    @property
    def estimated_time(self) -> float:
        return 3.0

    async def can_enrich(self, profile: CandidateProfile) -> bool:
        current_job = profile.experience[0] if profile.experience else None
        has_name = bool(profile.company and profile.company.name) or bool(current_job and current_job.company_name)
        return has_name

    async def enrich(self, profile: CandidateProfile) -> CandidateProfile:
        if not profile.company or not profile.company.name:
            current_job = profile.experience[0] if profile.experience else None
            name = profile.company.name if (profile.company and profile.company.name) else (current_job.company_name if current_job else "")
            if name:
                profile.company = CompanyDetails(name=name, website="", size="")
        profile.metadata.raw_data = profile.metadata.raw_data or {}
        profile.metadata.raw_data["executed_providers"] = list(set(profile.metadata.raw_data.get("executed_providers", []) + ["Company"]))
        profile.metadata.field_sources = profile.metadata.field_sources or {}
        profile.metadata.field_sources["company"] = "Company"
        return profile

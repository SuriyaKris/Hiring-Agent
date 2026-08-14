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
        # Requires a company name (either in experience or basic company detail name) to query details
        current_job = profile.experience[0] if profile.experience else None
        has_name = bool(profile.company and profile.company.name) or bool(current_job and current_job.company_name)
        return has_name

    async def enrich(self, profile: CandidateProfile) -> CandidateProfile:
        # Since mock data is disabled, this provider acts as a pass-through when real Company API is not active.
        return profile

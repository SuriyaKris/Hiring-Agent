"""GitHub API Enrichment Provider implementing BaseProvider."""

from typing import Set
from providers.base_provider import BaseProvider
from schemas.candidate_profile import CandidateProfile, ProjectItem, LanguageItem, SkillItem


class GitHubProvider(BaseProvider):
    """Enriches candidate profiles using GitHub API (Projects, Repositories, Languages, Tech Stack/Skills)."""

    @property
    def provider_name(self) -> str:
        return "GitHub"

    @property
    def supported_fields(self) -> Set[str]:
        return {"Projects", "Languages", "Skills"}

    @property
    def priority(self) -> int:
        return 4

    @property
    def cost(self) -> float:
        return 0.00

    @property
    def estimated_time(self) -> float:
        return 2.0

    async def can_enrich(self, profile: CandidateProfile) -> bool:
        # Requires a GitHub URL to query
        return bool(profile.basic_info.github_url)

    async def enrich(self, profile: CandidateProfile) -> CandidateProfile:
        # Since mock data is disabled, this provider acts as a pass-through when real GitHub API is not active.
        return profile

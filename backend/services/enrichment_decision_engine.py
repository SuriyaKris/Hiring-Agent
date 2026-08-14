"""Enrichment Decision Engine for Candidate Enrichment Pipeline."""

from typing import List, Optional
from pydantic import BaseModel, Field
from schemas.candidate_profile import CandidateProfile
from providers.base_provider import BaseProvider
from services.profile_validator import validate_profile


class EnrichmentDecision(BaseModel):
    """Encapsulates the decision engine's evaluation on candidate enrichment."""
    missing_fields: List[str] = Field(default_factory=list, description="Fields currently missing from the profile")
    eligible_providers: List[str] = Field(default_factory=list, description="Providers that support missing fields, can run, and haven't run yet")
    provider_to_run: Optional[str] = Field(None, description="The name of the next provider to execute (highest priority eligible)")
    providers_to_skip: List[str] = Field(default_factory=list, description="Providers that cannot run, have already run, or support no missing fields")
    should_stop: bool = Field(..., description="True if no missing fields, or no eligible provider remains")


class EnrichmentDecisionEngine:
    """Evaluates candidate profiles, mapping missing fields to suitable enrichment data providers."""

    async def decide_enrichment(self, profile: CandidateProfile, providers: List[BaseProvider]) -> EnrichmentDecision:
        """Analyze profile completeness and determine which provider to execute next.

        Args:
            profile: The candidate's canonical profile.
            providers: A list of candidate enrichment providers.

        Returns:
            An EnrichmentDecision object outlining next steps.
        """
        # 1. What information is missing?
        validation_result = validate_profile(profile)
        missing_fields = set(validation_result.missing_fields)

        # Extract already executed providers to avoid loops
        raw_data = profile.metadata.raw_data or {}
        executed_providers = set(raw_data.get("executed_providers", []))

        eligible = []
        skipped = []

        # 2. Which provider can supply it?
        for provider in providers:
            # Skip if already executed
            if provider.provider_name in executed_providers:
                skipped.append(provider.provider_name)
                continue

            # Skip if this provider does not support any remaining missing fields
            shares_missing_fields = bool(provider.supported_fields.intersection(missing_fields))
            if not shares_missing_fields:
                skipped.append(provider.provider_name)
                continue

            # Skip if provider prerequisites are not met (e.g. GitHub URL)
            can_run = await provider.can_enrich(profile)
            if not can_run:
                skipped.append(provider.provider_name)
                continue

            eligible.append(provider)

        # 3. Which provider should run first?
        # Sort by priority value (lower = higher priority)
        eligible.sort(key=lambda p: p.priority)

        eligible_names = [p.provider_name for p in eligible]
        provider_to_run = eligible_names[0] if eligible_names else None

        # 4. When should enrichment stop?
        should_stop = not missing_fields or not provider_to_run

        return EnrichmentDecision(
            missing_fields=list(missing_fields),
            eligible_providers=eligible_names,
            provider_to_run=provider_to_run,
            providers_to_skip=skipped,
            should_stop=should_stop
        )

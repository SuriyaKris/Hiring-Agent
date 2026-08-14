"""Base Provider Interface for Candidate Enrichment."""

from abc import ABC, abstractmethod
from typing import Set
from schemas.candidate_profile import CandidateProfile


class BaseProvider(ABC):
    """Abstract Base Class defining the contract for all candidate enrichment providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique human-readable name of the provider."""
        pass

    @property
    @abstractmethod
    def supported_fields(self) -> Set[str]:
        """Return the set of fields this provider can supply.

        The fields must match the missing field string identifiers returned by the validator,
        e.g., {"Email", "Phone", "Location", "Headline", "LinkedIn URL", "Summary",
               "Experience", "Experience Description", "Skills", "Education",
               "Certifications", "Languages", "Projects", "Awards", "Company"}
        """
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Return the execution priority of the provider (lower integer value = higher priority)."""
        pass

    @property
    @abstractmethod
    def cost(self) -> float:
        """Return the estimated cost of executing this provider (in USD)."""
        pass

    @property
    @abstractmethod
    def estimated_time(self) -> float:
        """Return the estimated execution duration of this provider (in seconds)."""
        pass

    @abstractmethod
    async def can_enrich(self, profile: CandidateProfile) -> bool:
        """Determine if this provider is capable of enriching the candidate profile.

        For example, a GitHub provider might require a GitHub URL to be present.
        """
        pass

    @abstractmethod
    async def enrich(self, profile: CandidateProfile) -> CandidateProfile:
        """Execute enrichment on the profile and return the enriched Profile."""
        pass

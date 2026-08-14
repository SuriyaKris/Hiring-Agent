"""Candidate Enrichment Service.

Orchestrates raw candidate data normalization and validation.
This service is provider-agnostic and relies on a registry of source-specific normalizers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Any
from schemas.candidate_profile import CandidateProfile


class BaseNormalizer(ABC):
    """Abstract Base Class for source-specific normalizers."""

    @abstractmethod
    def normalize(self, raw_data: Any) -> Dict[str, Any]:
        """Normalize raw source data into a dictionary structure.

        The returned dictionary must conform to the Canonical CandidateProfile schema fields.
        """
        pass


class EnrichmentRegistry:
    """Registry to manage and lookup source-specific normalizers."""

    def __init__(self):
        self._registry: Dict[str, BaseNormalizer] = {}

    def register(self, source: str, normalizer: BaseNormalizer) -> None:
        """Register a normalizer instance for a given source name (case-insensitive)."""
        self._registry[source.lower()] = normalizer

    def get(self, source: str) -> BaseNormalizer:
        """Retrieve the registered normalizer for the given source name."""
        source_key = source.lower()
        if source_key not in self._registry:
            raise ValueError(
                f"No normalizer registered for source: '{source}'. "
                f"Registered sources: {list(self._registry.keys())}"
            )
        return self._registry[source_key]


# Global registry instance
registry = EnrichmentRegistry()


def register_normalizer(source: str, normalizer: BaseNormalizer) -> None:
    """Helper function to register a normalizer globally."""
    registry.register(source, normalizer)


class CandidateEnrichmentService:
    """Orchestrator to normalize and validate candidate profile data."""

    def __init__(self, normalizer_registry: EnrichmentRegistry = registry):
        self.registry = normalizer_registry

    def enrich(self, raw_data: Any, source: str) -> CandidateProfile:
        """Receive, normalize, validate and return a Canonical CandidateProfile.

        Args:
            raw_data: The raw dictionary/payload from the data provider.
            source: The identifier of the data provider (e.g. 'apollo', 'proxycurl').

        Returns:
            A validated Canonical CandidateProfile object.
        """
        # 1. Fetch the correct normalizer
        normalizer = self.registry.get(source)

        # 2. Normalize raw data to the canonical dict structure
        normalized_dict = normalizer.normalize(raw_data)

        # 3. Validate against CandidateProfile schema (throws Pydantic ValidationError if invalid)
        profile = CandidateProfile.model_validate(normalized_dict)

        return profile

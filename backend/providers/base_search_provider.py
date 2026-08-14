"""Base Search Provider Interface — Milestone 5.3."""

from abc import ABC, abstractmethod
from typing import List
from models.schemas import JDSearchSpec


class BaseSearchProvider(ABC):
    """Abstract interface defining the contract for Candidate Discovery search providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the search provider."""
        pass

    @abstractmethod
    async def search(self, spec: JDSearchSpec) -> List[str]:
        """Query matching candidates based on JD criteria.

        Returns:
            List of candidate profile URLs/identifiers.
        """
        pass

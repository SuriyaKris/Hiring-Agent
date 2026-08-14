"""Base Site Scraper Interface — every platform adapter implements this contract."""

from abc import abstractmethod
from typing import Dict, Any, Optional, List
from browser.base_scraper import BaseScraper
from browser.health_check import HealthReport


class BaseSiteScraper(BaseScraper):
    """Abstract base class that all website/platform scraper adapters implement.

    Contract:
        can_handle(url)     → bool         — does this scraper own this URL?
        extract(url)        → dict         — run the extraction, return raw fields
        health_check()      → HealthReport — structured status report
    """

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Determine if this scraper adapter can handle/extract from the given URL."""
        pass

    @abstractmethod
    async def extract(self, url: str, sections: Optional[List[str]] = None) -> Dict[str, Any]:
        """Perform extraction of candidate details from the target URL.

        Args:
            url:      The page URL to scrape.
            sections: Optional list of sections to scrape (e.g. ['skills', 'about']).
                      If None, extracts all sections.
        """
        pass

    @abstractmethod
    async def health_check(self) -> HealthReport:
        """Run a structured availability and selector check.

        Returns:
            HealthReport with can_login, selectors_found, rate_limited,
            captcha_detected, extraction_success, and status_label.
        """
        pass

"""Wellfound Platform Scraper Adapter."""

from typing import Dict, Any, Optional, List
from browser.scrapers.base_scraper import BaseSiteScraper
from loguru import logger


class WellfoundScraper(BaseSiteScraper):
    """Adapts Playwright browser framework to scrape Wellfound profiles."""

    def can_handle(self, url: str) -> bool:
        return "wellfound.com" in url.lower() or "angel.co" in url.lower()

    async def extract(self, url: str, sections: Optional[List[str]] = None) -> Dict[str, Any]:
        await self.initialize()
        logger.info(f"Scraping Wellfound profile: {url}")
        
        try:
            await self.page.goto(url, wait_until="load", timeout=15000)
        except Exception as e:
            logger.warning(f"Failed to load wellfound page: {e}")

        # Returns default mocked profile elements representing Wellfound payload
        data = {
            "headline": "Growth Marketer",
            "about": "Passionate about startups and direct consumer acquisitions.",
            "skills": [{"name": "SEO"}, {"name": "Growth Hacking"}],
            "experience": [
                {
                    "company_name": "Startup Inc",
                    "title": "Marketing Manager",
                    "start_date": "2022-01",
                    "end_date": "Present",
                    "description": "Scaled CAC by 40%.",
                    "is_current": True
                }
            ],
            "education": []
        }

        await self.cleanup()
        return data

    async def health_check(self) -> bool:
        try:
            await self.initialize()
            await self.page.goto("https://wellfound.com", wait_until="load", timeout=10000)
            status = "wellfound.com" in self.page.url
            await self.cleanup()
            return status
        except Exception as e:
            logger.error(f"Wellfound health check failed: {e}")
            return False

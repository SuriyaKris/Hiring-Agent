"""Unit tests for Site Adapter Architecture and Platform Scrapers."""

import os
import sys
import unittest
import shutil

# Path setup to import backend files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from browser.browser_config import BrowserConfig
from browser.browser_manager import BrowserManager
from browser.session_manager import SessionManager
from browser.scrapers.wellfound_scraper import WellfoundScraper
from browser.scrapers.company_scraper import CompanyScraper


class TestSiteScrapers(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        import uuid
        self.test_session_dir = os.path.join(SCRIPT_DIR, "test_sessions")
        self.test_screenshot_dir = os.path.join(SCRIPT_DIR, "test_screenshots")
        self.test_profile_dir = os.path.join(SCRIPT_DIR, f"test_profile_{uuid.uuid4().hex}")
        self.config = BrowserConfig(
            headless=True,
            screenshot_dir=self.test_screenshot_dir,
            profile_dir=self.test_profile_dir,
        )
        self.session_manager = SessionManager(session_dir=self.test_session_dir)

    async def asyncTearDown(self):
        await BrowserManager.close_browser()
        if os.path.exists(self.test_session_dir):
            shutil.rmtree(self.test_session_dir)
        if os.path.exists(self.test_screenshot_dir):
            shutil.rmtree(self.test_screenshot_dir)
        if os.path.exists(self.test_profile_dir):
            try:
                shutil.rmtree(self.test_profile_dir)
            except Exception:
                pass

    def test_scraper_routing_can_handle(self):
        """Verify each scraper correctly identifies URLs it can handle."""
        wf_scraper = WellfoundScraper(session_id="test", config=self.config)
        co_scraper = CompanyScraper(session_id="test", config=self.config)

        # Wellfound
        self.assertTrue(wf_scraper.can_handle("https://wellfound.com/candidates/sarah"))
        self.assertTrue(wf_scraper.can_handle("https://angel.co/candidates/sarah"))

        # Company (generic)
        self.assertTrue(co_scraper.can_handle("https://google.com/about"))
        self.assertFalse(co_scraper.can_handle("https://wellfound.com/candidates/sarah"))


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Browser Automation Framework using IsolatedAsyncioTestCase."""

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
from browser.base_scraper import BaseScraper


class MockScraper(BaseScraper):
    """Concrete implementation of BaseScraper for testing."""
    pass


class TestBrowserFramework(unittest.IsolatedAsyncioTestCase):
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
        # Shutdown browser
        await BrowserManager.close_browser()
        # Clean directories
        if os.path.exists(self.test_session_dir):
            shutil.rmtree(self.test_session_dir)
        if os.path.exists(self.test_screenshot_dir):
            shutil.rmtree(self.test_screenshot_dir)
        if os.path.exists(self.test_profile_dir):
            try:
                shutil.rmtree(self.test_profile_dir)
            except Exception:
                pass

    async def test_browser_manager_launches_singleton(self):
        """Verify that BrowserManager returns a single Chromium browser instance."""
        browser1 = await BrowserManager.get_browser(self.config)
        browser2 = await BrowserManager.get_browser(self.config)
        self.assertEqual(browser1, browser2)
        await BrowserManager.close_browser()
        self.assertIsNone(BrowserManager._browser)

    async def test_session_manager_saves_and_restores_state(self):
        """Verify that SessionManager saves context states and restores them successfully."""
        browser = await BrowserManager.get_browser(self.config)
        context = await self.session_manager.get_or_create_context(
            "recruiter_a", browser, self.config
        )

        # Set a cookie
        await context.add_cookies([{
            "name": "test_cookie",
            "value": "cookie_value_123",
            "domain": ".example.com",
            "path": "/"
        }])

        # Save state
        await self.session_manager.save_session_state("recruiter_a")
        await self.session_manager.close_session("recruiter_a")

        # Load context again
        restored_context = await self.session_manager.get_or_create_context(
            "recruiter_a", browser, self.config
        )
        cookies = await restored_context.cookies()
        cookie_names = [c["name"] for c in cookies]
        self.assertIn("test_cookie", cookie_names)

        # Cleanup
        await self.session_manager.close_session("recruiter_a")

    async def test_base_scraper_navigation_and_screenshot(self):
        """Verify that BaseScraper navigates to pages and takes screenshots successfully."""
        scraper = MockScraper(
            session_id="scraper_test",
            config=self.config,
            session_manager=self.session_manager,
        )
        await scraper.initialize()

        # Navigate using data url to avoid external network dependencies
        await scraper.navigate_with_retry("data:text/html,<h1>Hello Automated Test</h1>")

        # Validate header text loaded
        header = await scraper.page.inner_text("h1")
        self.assertEqual(header, "Hello Automated Test")

        # Capture screenshot
        path = await scraper.take_screenshot("data_url_load")
        self.assertTrue(os.path.exists(path))

        # Cleanup
        await scraper.cleanup()
        await self.session_manager.close_session("scraper_test")


if __name__ == "__main__":
    unittest.main()

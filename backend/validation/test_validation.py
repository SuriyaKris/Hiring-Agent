"""Unit tests for the BrowserValidationRunner service."""

import os
import sys
import shutil
import unittest
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from validation.browser_validation_runner import BrowserValidationRunner
from validation.browser_validation_result import BrowserValidationResult
from browser.browser_config import BrowserConfig
from browser.browser_manager import BrowserManager


STUB_PROFILE_HTML = """
<html><body>
  <div id="about">Experienced Developer.</div>
  <div id="skills-section">
    <ul>
      <li class="pvs-list__item--line-separated"><span aria-hidden="true">Python</span></li>
    </ul>
  </div>
  <button id="see-more">see more</button>
</body></html>
"""


def b64_data_url(html: str) -> str:
    import base64
    encoded = base64.b64encode(html.encode()).decode()
    return f"data:text/html;base64,{encoded}"


class TestBrowserValidationRunner(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.screenshot_dir = os.path.join(SCRIPT_DIR, "_test_val_screenshots")
        self.config = BrowserConfig(headless=True, screenshot_dir=self.screenshot_dir)
        self.runner = BrowserValidationRunner(config=self.config)

        # Create a temporary JSON dataset for testing
        self.temp_json_path = os.path.join(SCRIPT_DIR, "temp_test_dataset.json")
        dataset = [
            {
                "name": "Sarah Developer",
                "url": b64_data_url(STUB_PROFILE_HTML),
                "expected_sections": ["about", "skills", "experience"]  # Experience should be missing!
            }
        ]
        with open(self.temp_json_path, "w") as f:
            json.dump(dataset, f)

    async def asyncTearDown(self):
        await BrowserManager.close_browser()
        if os.path.exists(self.screenshot_dir):
            shutil.rmtree(self.screenshot_dir)
        if os.path.exists(self.temp_json_path):
            os.remove(self.temp_json_path)

    # ── Unit Tests ────────────────────────────────────────────────────────────

    def test_load_dataset(self):
        """Verify load_dataset reads and parses JSON files correctly."""
        items = self.runner.load_dataset(self.temp_json_path)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["name"], "Sarah Developer")

    async def test_validate_dataset_outcome(self):
        """Verify runner evaluates expected vs actual, sets success=False on missing fields."""
        report = await self.runner.validate_dataset(self.temp_json_path, platform="linkedin")

        self.assertIsInstance(report, BrowserValidationResult)
        self.assertEqual(report.total_profiles, 1)
        # experience is expected but missing from the STUB html, so successful_runs should be 0
        self.assertEqual(report.successful_runs, 0)
        self.assertEqual(report.failed_runs, 1)
        self.assertEqual(report.overall_success_rate, 0.0)

        # Check detail results
        profile_res = report.results[0]
        self.assertEqual(profile_res.name, "Sarah Developer")
        self.assertEqual(profile_res.platform, "linkedin")
        self.assertFalse(profile_res.success)
        self.assertIn("about", profile_res.sections_found)
        self.assertIn("skills", profile_res.sections_found)
        self.assertIn("experience", profile_res.sections_missing)


if __name__ == "__main__":
    unittest.main()

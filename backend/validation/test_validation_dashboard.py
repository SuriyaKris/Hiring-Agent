"""Unit tests for validation dashboard, failed reviews, and planner confidence routing."""

import os
import sys
import shutil
import unittest
import json
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from validation.browser_validation_runner import BrowserValidationRunner
from browser.browser_config import BrowserConfig
from browser.browser_manager import BrowserManager
from schemas.candidate_profile import (
    CandidateProfile, BasicInfo, SchemaMetadata, ExperienceItem, ProfileSummary,
    EducationItem, CertificationItem, CompanyDetails
)
from services.profile_validator import validate_profile
from services.enrichment_planner import EnrichmentPlanner


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


class TestValidationDashboard(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.screenshot_dir = os.path.join(SCRIPT_DIR, "_test_dash_screenshots")
        self.config = BrowserConfig(headless=True, screenshot_dir=self.screenshot_dir)
        self.runner = BrowserValidationRunner(config=self.config)

        # Clear reports dir if any
        self.reports_dir = os.path.join(BACKEND_DIR, "validation", "reports")
        if os.path.exists(self.reports_dir):
            shutil.rmtree(self.reports_dir)

        # Create temporary JSON dataset with a failed item
        self.temp_json_path = os.path.join(SCRIPT_DIR, "temp_test_dash_dataset.json")
        dataset = [
            {
                "name": "Sarah Developer",
                "url": b64_data_url(STUB_PROFILE_HTML),
                "expected_sections": ["about", "skills", "experience"]  # Experience should be missing, forcing failure
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
        if os.path.exists(self.reports_dir):
            shutil.rmtree(self.reports_dir)

    # ── Unit Tests ────────────────────────────────────────────────────────────

    async def test_validate_dataset_generates_dashboard_and_failed_reviews(self):
        """Verify runner validation saves dashboard.json and platform failed JSON report on failed run."""
        report = await self.runner.validate_dataset(self.temp_json_path, platform="linkedin")

        # 1. Assert dashboard JSON exists and has valid stats
        dashboard_path = os.path.join(self.reports_dir, "dashboard.json")
        self.assertTrue(os.path.exists(dashboard_path))
        with open(dashboard_path, "r") as f:
            dash = json.load(f)
            
        self.assertIn("linkedin", dash)
        self.assertEqual(dash["linkedin"]["profiles_tested"], 1)
        self.assertEqual(dash["linkedin"]["success_rate"], 0.0)
        self.assertIn("about", dash["linkedin"]["sections"])
        self.assertIn("skills", dash["linkedin"]["sections"])

        # 2. Assert failed report JSON exists and has detailed fields
        failed_report_path = os.path.join(self.reports_dir, "linkedin", "failed_sarah_developer.json")
        self.assertTrue(os.path.exists(failed_report_path))
        with open(failed_report_path, "r") as f:
            failed_run = json.load(f)
            
        self.assertEqual(failed_run["name"], "Sarah Developer")
        self.assertIn("experience", failed_run["sections_missing"])
        self.assertIn("browser_plan", failed_run)
        self.assertIn("browser_result", failed_run)
        self.assertIn("screenshot_path", failed_run)

    def test_planner_prefers_higher_confidence_provider(self):
        """Verify that when multiple providers are eligible for a field, the planner selects the one with higher confidence."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                email="sarah@salesforce.com",
                phone="+1-555-0199",
                location="Austin, TX",
                linkedin_url="https://linkedin.com/in/sarah-j"
            ),
            summary=ProfileSummary(about="Experienced Engineer", tagline="Specialist"),
            experience=[ExperienceItem(company_name="Google", title="SWE", description="SWE description", is_current=True)],
            education=[EducationItem(school_name="University of Texas")],
            certifications=[CertificationItem(name="Cert")],
            company=CompanyDetails(name="Google"),
            # Only skills is missing
            metadata=SchemaMetadata(
                source="test",
                raw_data={"has_resume": True, "resume_path": "path/to/resume.pdf"}
            )
        )

        reliability_metrics = {
            "Playwright": {
                "Summary": 0.95,
                "Experience": 0.91,
                "Skills": 0.45,  # Low reliability
                "Education": 0.88,
                "Certifications": 0.85
            },
            "Resume": {
                "Experience": 0.95,
                "Skills": 0.90,  # High reliability
                "Education": 0.92,
                "Certifications": 0.90
            }
        }

        planner = EnrichmentPlanner(reliability_metrics=reliability_metrics)
        val_result = validate_profile(profile)
        plan = asyncio.run(planner.plan(profile, val_result))

        # Should choose Resume over Playwright for skills, because 0.90 > 0.45
        self.assertIn("Resume", plan.providers)
        self.assertNotIn("Playwright", plan.providers)
        self.assertEqual(plan.field_confidences["Skills"], 0.90)


if __name__ == "__main__":
    unittest.main()

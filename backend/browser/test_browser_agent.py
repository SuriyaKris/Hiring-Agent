"""Unit and integration tests for BrowserAgent and modular Tasks."""

import os
import sys
import shutil
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from browser.models.enrichment_objective import EnrichmentObjective
from browser.models.browser_plan import BrowserPlan
from agents.browser_agent import BrowserAgent
from browser.browser_config import BrowserConfig
from browser.browser_manager import BrowserManager
from browser.session_manager import SessionManager


# ── Stub HTML page for tests ──────────────────────────────────────────────────

STUB_PROFILE_HTML = """
<html><body>
  <div id="about">Experienced Software Engineer specializing in Python.</div>
  <div id="skills-section">
    <ul>
      <li class="pvs-list__item--line-separated"><span aria-hidden="true">Python</span></li>
      <li class="pvs-list__item--line-separated"><span aria-hidden="true">AWS</span></li>
    </ul>
  </div>
  <div id="experience">
    <div class="pvs-list__item--line-separated">
      <span class="t-bold"><span aria-hidden="true">Principal Engineer</span></span>
      <span class="t-normal"><span aria-hidden="true">Microsoft</span></span>
      <span class="pvs-entity__caption-wrapper">2020 to Present</span>
    </div>
  </div>
  <button id="see-more">see more</button>
</body></html>
"""


def b64_data_url(html: str) -> str:
    import base64
    encoded = base64.b64encode(html.encode()).decode()
    return f"data:text/html;base64,{encoded}"


class TestBrowserAgent(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        import uuid
        self.screenshot_dir = os.path.join(SCRIPT_DIR, "_test_agent_screenshots")
        self.config = BrowserConfig(headless=True, screenshot_dir=self.screenshot_dir)
        self.session_mgr = SessionManager()
        self.agent = BrowserAgent(
            session_id=f"test_agent_{uuid.uuid4().hex[:8]}",
            config=self.config,
            session_manager=self.session_mgr
        )

    async def asyncTearDown(self):
        await BrowserManager.close_browser()
        if os.path.exists(self.screenshot_dir):
            shutil.rmtree(self.screenshot_dir)

    # ── Compilation Tests ─────────────────────────────────────────────────────

    def test_plan_compilation_structure(self):
        """Verify BrowserAgent correctly translates an objective into a BrowserPlan."""
        objective = EnrichmentObjective(
            goal="EnrichCandidate",
            site="linkedin",
            url="https://linkedin.com/in/test",
            sections=["about", "skills", "experience"]
        )

        plan = self.agent.compile_plan(objective)

        self.assertIsInstance(plan, BrowserPlan)
        self.assertEqual(plan.objective.site, "linkedin")
        self.assertEqual(plan.status, "pending")
        self.assertGreater(len(plan.steps), 0)

        # First task must navigate to page
        self.assertEqual(plan.steps[0].task_type, "open_page")
        self.assertEqual(plan.steps[0].params["url"], "https://linkedin.com/in/test")

        # Must contain screenshots and extractions
        task_types = [step.task_type for step in plan.steps]
        self.assertIn("extract_text", task_types)
        self.assertIn("screenshot", task_types)

    # ── Execution Tests ───────────────────────────────────────────────────────

    async def test_execute_plan_on_stub(self):
        """Verify agent successfully runs the plan and extracts results on a stub HTML page."""
        objective = EnrichmentObjective(
            goal="EnrichCandidate",
            site="linkedin",
            url=b64_data_url(STUB_PROFILE_HTML),
            sections=["about", "skills", "experience"]
        )

        plan = self.agent.compile_plan(objective)
        result = await self.agent.execute_plan(plan)

        self.assertEqual(plan.status, "completed")
        self.assertTrue(result.success)
        self.assertIn("about", result.profile)
        self.assertIn("skills", result.profile)
        self.assertIn("experience", result.profile)

        # Check extracted content matches DOM elements
        self.assertIn("Software Engineer", result.profile["about"])
        self.assertGreater(len(result.profile["skills"]), 0)
        self.assertEqual(result.profile["experience"][0]["company_name"], "Microsoft")
        self.assertEqual(result.profile["experience"][0]["title"], "Principal Engineer")

        # Verify screenshot is captured in state and exists on disk
        self.assertGreater(len(result.screenshots), 0)
        self.assertTrue(os.path.exists(result.screenshots[0]))

    async def test_execute_plan_records_durations(self):
        """Verify execution logs durations and status for each step."""
        objective = EnrichmentObjective(
            goal="EnrichCandidate",
            site="linkedin",
            url=b64_data_url(STUB_PROFILE_HTML),
            sections=["about"]
        )

        plan = self.agent.compile_plan(objective)
        await self.agent.execute_plan(plan)

        for step in plan.steps:
            self.assertEqual(step.status, "completed")
            self.assertGreaterEqual(step.duration_seconds, 0)
            self.assertIsNone(step.error_message)

    async def test_execute_plan_handles_failure(self):
        """Verify plan fails gracefully and records error message when navigation fails."""
        objective = EnrichmentObjective(
            goal="EnrichCandidate",
            site="linkedin",
            url="data:text/html,<html><body>Broken</body></html>",
            sections=["experience"]
        )

        plan = self.agent.compile_plan(objective)

        # Make the experience selector check fail by querying an invalid path that throws or fails to match
        # To force error, let's inject a task with bad parameters
        plan.steps.append(
            plan.steps[-1].model_copy(update={"task_type": "open_page", "params": {}})
        )

        with self.assertRaises(Exception):
            await self.agent.execute_plan(plan)

        self.assertEqual(plan.status, "failed")
        self.assertIn("failed", [step.status for step in plan.steps])


if __name__ == "__main__":
    unittest.main()

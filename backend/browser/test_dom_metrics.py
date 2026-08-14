"""Tests for DOM Extraction Layer, Screenshot Logging, Health Checks, and Metrics.

Uses data:text/html stub pages — no network calls required.
"""

import os
import sys
import json
import asyncio
import shutil
import time
import unittest
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from browser.metrics import MetricsStore, ExtractionMetric, ProviderSummary
from browser.health_check import HealthReport, HealthChecker


# ── Stub HTML pages ────────────────────────────────────────────────────────────

STUB_PROFILE_HTML = """
<html><body>
  <section id="about"><p class="t-bold">About section content here.</p></section>
  <section id="skills-section">
    <ul>
      <li class="pvs-list__item--line-separated"><span aria-hidden="true">Python</span></li>
      <li class="pvs-list__item--line-separated"><span aria-hidden="true">AWS</span></li>
      <li class="pvs-list__item--line-separated"><span aria-hidden="true">Kubernetes</span></li>
    </ul>
  </section>
  <section id="experience">
    <ul>
      <li class="pvs-list__item--line-separated">
        <span class="t-bold">Senior Engineer</span>
        <span class="t-normal">Stripe</span>
      </li>
    </ul>
  </section>
  <div id="main" class="pv-top-card">Profile loaded</div>
  <button id="show-more">Show more</button>
</body></html>
"""

STUB_CAPTCHA_HTML = """
<html><body>
  <div id="captcha-challenge">Please solve this captcha</div>
</body></html>
"""

STUB_RATE_LIMIT_HTML = """
<html><body>
  <div class="ip-limit-exceeded">You have exceeded the rate limit.</div>
</body></html>
"""


def b64_data_url(html: str) -> str:
    """Encode HTML as a data: URL for Playwright navigation."""
    import base64
    encoded = base64.b64encode(html.encode()).decode()
    return f"data:text/html;base64,{encoded}"


# ── Metrics tests (no Playwright needed) ──────────────────────────────────────

class TestMetricsStore(unittest.TestCase):

    def setUp(self):
        MetricsStore.reset()
        self.store = MetricsStore.instance()

    def _make_metric(self, provider="LinkedIn", success=True, duration=1.5,
                     fields=None, retries=0, error=None):
        m = ExtractionMetric(
            provider=provider,
            session_id="test-session",
            started_at=datetime.utcnow(),
            duration_seconds=duration,
            fields_extracted=fields or ["about", "skills"],
            fields_empty=[],
            retries=retries,
            success=success,
            error_message=error,
        )
        return m

    def test_record_and_get_all(self):
        """Recorded metrics should be retrievable."""
        m = self._make_metric()
        self.store.record(m)
        all_metrics = self.store.get_all()
        self.assertEqual(len(all_metrics), 1)
        self.assertEqual(all_metrics[0].provider, "LinkedIn")

    def test_get_for_provider_filters_correctly(self):
        """get_for_provider should only return matching provider metrics."""
        self.store.record(self._make_metric(provider="LinkedIn"))
        self.store.record(self._make_metric(provider="Indeed"))
        self.store.record(self._make_metric(provider="LinkedIn"))

        linkedin = self.store.get_for_provider("LinkedIn")
        indeed = self.store.get_for_provider("Indeed")
        self.assertEqual(len(linkedin), 2)
        self.assertEqual(len(indeed), 1)

    def test_summary_success_rate(self):
        """ProviderSummary should compute correct success_rate."""
        self.store.record(self._make_metric(success=True))
        self.store.record(self._make_metric(success=True))
        self.store.record(self._make_metric(success=False))

        summary = self.store.get_summary("LinkedIn")
        self.assertEqual(summary.total_runs, 3)
        self.assertEqual(summary.successful_runs, 2)
        self.assertAlmostEqual(summary.success_rate, 0.6667, places=3)

    def test_summary_avg_duration(self):
        """ProviderSummary should compute correct avg_duration."""
        self.store.record(self._make_metric(duration=2.0))
        self.store.record(self._make_metric(duration=4.0))

        summary = self.store.get_summary("LinkedIn")
        self.assertAlmostEqual(summary.avg_duration_seconds, 3.0, places=2)

    def test_summary_avg_fields_extracted(self):
        """ProviderSummary should compute avg fields extracted."""
        self.store.record(self._make_metric(fields=["about", "skills"]))
        self.store.record(self._make_metric(fields=["about", "skills", "experience"]))

        summary = self.store.get_summary("LinkedIn")
        self.assertAlmostEqual(summary.avg_fields_extracted, 2.5, places=1)

    def test_empty_provider_summary(self):
        """get_summary on unknown provider should return zero-value summary."""
        summary = self.store.get_summary("UnknownProvider")
        self.assertEqual(summary.total_runs, 0)
        self.assertEqual(summary.success_rate, 0.0)

    def test_export_json(self):
        """export_json should produce a valid JSON file with all records."""
        self.store.record(self._make_metric())
        self.store.record(self._make_metric(provider="Indeed", success=False))

        export_path = os.path.join(SCRIPT_DIR, "_test_metrics_export.json")
        try:
            self.store.export_json(export_path)
            self.assertTrue(os.path.exists(export_path))
            with open(export_path) as f:
                data = json.load(f)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["provider"], "LinkedIn")
        finally:
            if os.path.exists(export_path):
                os.remove(export_path)

    def test_singleton_returns_same_instance(self):
        """MetricsStore.instance() should return the same object each call."""
        a = MetricsStore.instance()
        b = MetricsStore.instance()
        self.assertIs(a, b)

    def test_multiple_providers_all_summaries(self):
        """get_all_summaries should return one ProviderSummary per provider."""
        self.store.record(self._make_metric(provider="LinkedIn"))
        self.store.record(self._make_metric(provider="Indeed"))
        self.store.record(self._make_metric(provider="GitHub"))

        summaries = self.store.get_all_summaries()
        provider_names = {s.provider for s in summaries}
        self.assertIn("LinkedIn", provider_names)
        self.assertIn("Indeed", provider_names)
        self.assertIn("GitHub", provider_names)


# ── HealthReport unit tests (no Playwright) ───────────────────────────────────

class TestHealthReport(unittest.TestCase):

    def test_is_healthy_true_when_all_good(self):
        report = HealthReport(
            scraper_name="LinkedIn",
            can_login=True,
            extraction_success=True,
            rate_limited=False,
            captcha_detected=False,
        )
        self.assertTrue(report.is_healthy)

    def test_is_healthy_false_on_captcha(self):
        report = HealthReport(
            scraper_name="LinkedIn",
            extraction_success=True,
            captcha_detected=True,
        )
        self.assertFalse(report.is_healthy)
        self.assertEqual(report.status_label, "CAPTCHA")

    def test_is_healthy_false_on_rate_limit(self):
        report = HealthReport(
            scraper_name="LinkedIn",
            extraction_success=True,
            rate_limited=True,
        )
        self.assertFalse(report.is_healthy)
        self.assertEqual(report.status_label, "RATE_LIMITED")

    def test_status_label_ok(self):
        report = HealthReport(
            scraper_name="LinkedIn",
            can_login=True,
            extraction_success=True,
        )
        self.assertEqual(report.status_label, "OK")

    def test_status_label_auth_required(self):
        report = HealthReport(scraper_name="LinkedIn", can_login=False)
        self.assertEqual(report.status_label, "AUTH_REQUIRED")

    def test_to_dict_contains_all_keys(self):
        report = HealthReport(scraper_name="Test")
        d = report.to_dict()
        for key in ["scraper", "status", "is_healthy", "can_login",
                    "selectors_found", "selectors_missing",
                    "rate_limited", "captcha_detected",
                    "extraction_success", "checked_at"]:
            self.assertIn(key, d)


# ── DOMHelper + HealthChecker Playwright tests ────────────────────────────────

class TestDOMHelper(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        from browser.browser_config import BrowserConfig
        from browser.browser_manager import BrowserManager
        self.config = BrowserConfig(headless=True)
        self._browser_manager = BrowserManager
        self.browser = await BrowserManager.get_browser(self.config)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def asyncTearDown(self):
        await self.page.close()
        await self.context.close()
        from browser.browser_manager import BrowserManager
        await BrowserManager.close_browser()

    async def _load_stub(self, html: str):
        await self.page.goto(b64_data_url(html))

    async def test_find_section_returns_locator_for_existing_selector(self):
        """find_section should return a Locator when element exists."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        loc = await dom.find_section(["#missing-selector", "#about"])
        self.assertIsNotNone(loc)

    async def test_find_section_returns_none_for_missing_selectors(self):
        """find_section should return None when all selectors miss."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        loc = await dom.find_section(["#does-not-exist", ".also-missing"])
        self.assertIsNone(loc)

    async def test_extract_text_returns_content(self):
        """extract_text should return text for a matched selector."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        text = await dom.extract_text(["#about"])
        self.assertIn("About section content here", text)

    async def test_extract_text_returns_empty_for_missing(self):
        """extract_text should return empty string when selector not found."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        text = await dom.extract_text(["#no-such-element"])
        self.assertEqual(text, "")

    async def test_extract_all_text_returns_list(self):
        """extract_all_text should return all matching elements as list."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        texts = await dom.extract_all_text(["#skills-section li"])
        self.assertIsInstance(texts, list)
        self.assertGreater(len(texts), 0)

    async def test_extract_all_text_returns_empty_for_missing(self):
        """extract_all_text should return [] when nothing matches."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        texts = await dom.extract_all_text(["#no-such-list li"])
        self.assertEqual(texts, [])

    async def test_safe_click_returns_true_on_success(self):
        """safe_click should return True when element is found and clicked."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        result = await dom.safe_click(["#show-more"])
        self.assertTrue(result)

    async def test_safe_click_returns_false_for_missing(self):
        """safe_click should return False when element not found."""
        from browser.dom_helper import DOMHelper
        await self._load_stub(STUB_PROFILE_HTML)
        dom = DOMHelper(self.page)
        result = await dom.safe_click(["#no-such-button"])
        self.assertFalse(result)

    async def test_health_checker_detects_captcha(self):
        """HealthChecker should set captcha_detected=True on captcha page."""
        await self._load_stub(STUB_CAPTCHA_HTML)
        checker = HealthChecker(self.page, "LinkedIn")
        report = await checker.check(
            key_selectors=["#main"],
            captcha_selectors=["#captcha-challenge"],
        )
        self.assertTrue(report.captcha_detected)
        self.assertFalse(report.is_healthy)
        self.assertEqual(report.status_label, "CAPTCHA")

    async def test_health_checker_detects_rate_limit(self):
        """HealthChecker should set rate_limited=True on rate-limit page."""
        await self._load_stub(STUB_RATE_LIMIT_HTML)
        checker = HealthChecker(self.page, "LinkedIn")
        report = await checker.check(
            key_selectors=["#main"],
            rate_limit_selectors=[".ip-limit-exceeded"],
        )
        self.assertTrue(report.rate_limited)
        self.assertFalse(report.is_healthy)
        self.assertEqual(report.status_label, "RATE_LIMITED")

    async def test_health_checker_reports_healthy_on_valid_page(self):
        """HealthChecker should report healthy when key selectors are found."""
        await self._load_stub(STUB_PROFILE_HTML)
        checker = HealthChecker(self.page, "LinkedIn")
        report = await checker.check(
            key_selectors=["#main", "#about"],
        )
        self.assertTrue(report.extraction_success)
        self.assertIn("#main", report.selectors_found)
        self.assertIn("#about", report.selectors_found)
        self.assertEqual(report.status_label, "OK")

    async def test_health_checker_tracks_missing_selectors(self):
        """HealthChecker should record missing selectors in selectors_missing."""
        await self._load_stub(STUB_PROFILE_HTML)
        checker = HealthChecker(self.page, "LinkedIn")
        report = await checker.check(
            key_selectors=["#main", "#does-not-exist"],
        )
        self.assertIn("#does-not-exist", report.selectors_missing)


# ── screenshot_context + metrics_context integration ──────────────────────────

class TestBaseScraperContexts(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        MetricsStore.reset()
        self.screenshot_dir = os.path.join(SCRIPT_DIR, "_test_screenshots")
        from browser.browser_config import BrowserConfig
        from browser.session_manager import SessionManager
        self.config = BrowserConfig(headless=True, screenshot_dir=self.screenshot_dir)
        self.session_mgr = SessionManager()

    async def asyncTearDown(self):
        from browser.browser_manager import BrowserManager
        await BrowserManager.close_browser()
        if os.path.exists(self.screenshot_dir):
            shutil.rmtree(self.screenshot_dir)

    async def test_metrics_context_records_on_success(self):
        """metrics_context should record a success metric after clean execution."""
        from browser.scrapers.indeed_scraper import IndeedScraper
        scraper = IndeedScraper(
            session_id="test-metrics",
            config=self.config,
            session_manager=self.session_mgr,
        )
        await scraper.initialize()

        async with scraper.metrics_context("IndeedTest", expected_fields=["headline", "skills"]) as m:
            m.fields_extracted = ["headline", "skills"]

        await scraper.cleanup()

        store = MetricsStore.instance()
        records = store.get_for_provider("IndeedTest")
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].success)
        self.assertEqual(records[0].fields_extracted, ["headline", "skills"])
        self.assertGreaterEqual(records[0].duration_seconds, 0)

    async def test_metrics_context_records_on_failure(self):
        """metrics_context should record a failure metric when exception raised."""
        from browser.scrapers.indeed_scraper import IndeedScraper
        scraper = IndeedScraper(
            session_id="test-metrics-fail",
            config=self.config,
            session_manager=self.session_mgr,
        )
        await scraper.initialize()

        with self.assertRaises(ValueError):
            async with scraper.metrics_context("IndeedFail") as m:
                raise ValueError("Simulated extraction failure")

        await scraper.cleanup()

        store = MetricsStore.instance()
        records = store.get_for_provider("IndeedFail")
        self.assertEqual(len(records), 1)
        self.assertFalse(records[0].success)
        self.assertIn("Simulated extraction failure", records[0].error_message)

    async def test_screenshot_context_saves_files(self):
        """screenshot_context should save before/after PNG files."""
        from browser.scrapers.indeed_scraper import IndeedScraper
        scraper = IndeedScraper(
            session_id="test-screenshot",
            config=self.config,
            session_manager=self.session_mgr,
        )
        await scraper.initialize()
        await scraper.page.goto("data:text/html,<h1>Screenshot Test</h1>")

        async with scraper.screenshot_context("profile"):
            pass  # Just capture before/after

        await scraper.cleanup()

        files = os.listdir(self.screenshot_dir)
        before = [f for f in files if "profile_before" in f]
        after = [f for f in files if "profile_after" in f]
        self.assertGreater(len(before), 0, "Expected a 'before' screenshot")
        self.assertGreater(len(after), 0, "Expected an 'after' screenshot")


if __name__ == "__main__":
    unittest.main()

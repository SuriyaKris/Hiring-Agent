"""Base Scraper Class — centralized browser lifecycle, screenshot logging, and metrics."""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from playwright.async_api import BrowserContext, Page
from browser.browser_config import BrowserConfig
from browser.browser_manager import BrowserManager
from browser.session_manager import SessionManager
from browser.metrics import MetricsStore, ExtractionMetric
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


class BaseScraper(ABC):
    """Abstract scraper providing browser lifecycle, screenshot logging, and metrics.

    Every scraper inherits:
      - initialize() / cleanup()        — browser/page lifecycle
      - navigate_with_retry()           — navigation with backoff
      - take_screenshot()               — on-demand screenshot
      - screenshot_context()            — before/after auto-screenshot around any block
      - metrics_context()               — auto-records timing, fields, success per run
    """

    def __init__(
        self,
        session_id: str,
        config: Optional[BrowserConfig] = None,
        session_manager: Optional[SessionManager] = None,
    ):
        self.session_id = session_id
        self.config = config or BrowserConfig()
        self.session_manager = session_manager or SessionManager()
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self):
        """Initialize the scraper page, context, and browser dependencies."""
        browser = await BrowserManager.get_browser(self.config)
        self.context = await self.session_manager.get_or_create_context(
            self.session_id, browser, self.config
        )
        self.page = await self.context.new_page()
        logger.info(f"Initialized scraper page for session '{self.session_id}'")

    async def cleanup(self):
        """Close active scraper page."""
        if self.page:
            await self.page.close()
            self.page = None
            logger.info(f"Closed scraper page for session '{self.session_id}'")

    # ── Navigation ────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def navigate_with_retry(self, url: str):
        """Navigate to a target URL with automatic tenacity backoff retries."""
        logger.info(f"Navigating to: {url} (session '{self.session_id}')")
        await self.page.goto(url, wait_until="load")

    # ── Screenshots ───────────────────────────────────────────────────────────

    async def take_screenshot(self, name: str) -> str:
        """Capture page screenshot and save to config directory.

        Args:
            name: Descriptive label for the screenshot file.

        Returns:
            Absolute path to the saved screenshot, or '' on failure.
        """
        try:
            os.makedirs(self.config.screenshot_dir, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.session_id}_{name}_{timestamp}.png"
            screenshot_path = os.path.join(self.config.screenshot_dir, filename)
            await self.page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved → {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.warning(f"Screenshot '{name}' failed (non-fatal): {e}")
            return ""

    @asynccontextmanager
    async def screenshot_context(self, section: str):
        """Async context manager that captures before/after screenshots around an extraction.

        Usage:
            async with self.screenshot_context("skills"):
                data = await extract_skills(dom)

        Saves:
            {session_id}_{section}_before_{timestamp}.png
            {session_id}_{section}_after_{timestamp}.png
        """
        await self.take_screenshot(f"{section}_before")
        try:
            yield
        finally:
            await self.take_screenshot(f"{section}_after")

    # ── Metrics ───────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def metrics_context(self, provider: str, expected_fields: Optional[List[str]] = None):
        """Async context manager that auto-records an ExtractionMetric.

        Usage:
            async with self.metrics_context("LinkedIn", ["about", "skills"]) as m:
                data = await extractor.extract_sections(url, sections)
                m.fields_extracted = list(data.keys())
                m.retries = retry_count

        Args:
            provider:        Provider/scraper name for the metric label.
            expected_fields: List of fields we expected to extract (used to compute fields_empty).
        """
        metric = ExtractionMetric(
            provider=provider,
            session_id=self.session_id,
            started_at=datetime.utcnow(),
        )
        start_time = time.monotonic()
        error_msg: Optional[str] = None
        try:
            yield metric
            metric.success = True
        except Exception as e:
            metric.success = False
            error_msg = str(e)
            metric.error_message = error_msg
            raise
        finally:
            metric.duration_seconds = round(time.monotonic() - start_time, 3)

            # Compute empty fields = expected - extracted
            if expected_fields:
                extracted_set = set(metric.fields_extracted)
                metric.fields_empty = [f for f in expected_fields if f not in extracted_set]

            MetricsStore.instance().record(metric)
            logger.debug(
                f"[{provider}] metrics_context complete — "
                f"success={metric.success}, duration={metric.duration_seconds}s"
            )

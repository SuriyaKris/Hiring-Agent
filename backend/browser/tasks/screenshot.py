"""Browser Task: Screenshot — Milestone 3.4."""

from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger
import os


class ScreenshotTask(BaseBrowserTask):
    """Task to capture a screenshot of the current page."""

    @property
    def name(self) -> str:
        return "screenshot"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        name = params.get("name", "screenshot")
        screenshot_dir = params.get("screenshot_dir", "test_screenshots")
        session_id = context.get("session_id", "default_session")

        os.makedirs(screenshot_dir, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{session_id}_{name}_{timestamp}.png"
        screenshot_path = os.path.join(screenshot_dir, filename)

        logger.info(f"ScreenshotTask: taking screenshot -> {screenshot_path}")
        await page.screenshot(path=screenshot_path)
        return {"screenshot_path": screenshot_path}

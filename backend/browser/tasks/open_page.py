"""Browser Task: Open Page — Milestone 3.4."""

from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger


class OpenPageTask(BaseBrowserTask):
    """Task to navigate to a target URL."""

    @property
    def name(self) -> str:
        return "open_page"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        url = params.get("url")
        if not url:
            raise ValueError("open_page task requires a 'url' parameter.")

        logger.info(f"OpenPageTask: navigating to {url}")
        # Default wait_until option is load, can override
        wait_until = params.get("wait_until", "load")
        timeout = params.get("timeout", 30000)

        await page.goto(url, wait_until=wait_until, timeout=timeout)
        return {}

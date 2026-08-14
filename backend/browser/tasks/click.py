"""Browser Task: Click — Milestone 3.4."""

from typing import List
from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger


class ClickTask(BaseBrowserTask):
    """Task to perform a safe click on page elements."""

    @property
    def name(self) -> str:
        return "click"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        selectors = params.get("selectors")
        if not selectors:
            raise ValueError("click task requires 'selectors' parameter.")

        logger.info(f"ClickTask: clicking matching selector in {selectors}")
        timeout = params.get("timeout")
        clicked = await dom_helper.safe_click(selectors, timeout=timeout)
        return {"clicked": clicked}

"""Browser Task: Expand Section — Milestone 3.4."""

from typing import List
from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger


class ExpandTask(BaseBrowserTask):
    """Task to expand sections using fallback selectors."""

    @property
    def name(self) -> str:
        return "expand"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        selectors = params.get("selectors")
        if not selectors:
            raise ValueError("expand task requires 'selectors' parameter.")

        logger.info(f"ExpandTask: expanding section via {selectors}")
        timeout = params.get("timeout")
        expanded = await dom_helper.expand_section(selectors, timeout=timeout)
        logger.debug(f"ExpandTask: expanded state: {expanded}")
        return {"expanded": expanded}

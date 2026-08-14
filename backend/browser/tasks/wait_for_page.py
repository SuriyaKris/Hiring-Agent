"""Browser Task: Wait For Page — Milestone 3.4."""

from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger


class WaitForPageTask(BaseBrowserTask):
    """Task to wait for page load states or selectors."""

    @property
    def name(self) -> str:
        return "wait_for_page"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        selector = params.get("selector")
        timeout = params.get("timeout", 10000)
        state = params.get("state", "visible")

        if selector:
            logger.info(f"WaitForPageTask: waiting for selector '{selector}' (state={state})")
            await page.wait_for_selector(selector, state=state, timeout=timeout)
        else:
            # Settle wait
            delay_ms = params.get("delay_ms", 1000)
            logger.info(f"WaitForPageTask: sleeping for {delay_ms}ms")
            import asyncio
            await asyncio.sleep(delay_ms / 1000.0)

        return {}

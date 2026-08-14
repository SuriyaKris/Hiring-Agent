"""Browser Task: Scroll — Milestone 3.4."""

from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger


class ScrollTask(BaseBrowserTask):
    """Task to scroll page up/down or to a selector."""

    @property
    def name(self) -> str:
        return "scroll"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        direction = params.get("direction", "down")
        selector = params.get("selector")
        distance = params.get("distance", 500)

        if selector:
            logger.info(f"ScrollTask: scrolling to selector '{selector}'")
            loc = page.locator(selector).first
            await loc.scroll_into_view_if_needed()
        else:
            logger.info(f"ScrollTask: scrolling {direction} by {distance}px")
            scroll_y = distance if direction == "down" else -distance
            await page.evaluate(f"window.scrollBy(0, {scroll_y})")

        # Give dynamic content time to load
        import asyncio
        await asyncio.sleep(0.3)
        return {}

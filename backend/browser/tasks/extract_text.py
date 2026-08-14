"""Browser Task: Extract Text — Milestone 3.4."""

from typing import List, Dict, Any
from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger


class ExtractTextTask(BaseBrowserTask):
    """Task to extract text or structured blocks using DOMHelper."""

    @property
    def name(self) -> str:
        return "extract_text"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        selectors = params.get("selectors")
        mode = params.get("mode", "text")  # 'text' | 'all_text' | 'blocks'
        output_key = params.get("output_key")

        if not selectors:
            raise ValueError("extract_text task requires a 'selectors' list parameter.")
        if not output_key:
            raise ValueError("extract_text task requires an 'output_key' parameter.")

        logger.info(f"ExtractTextTask: extracting in mode='{mode}' to output_key='{output_key}'")

        data: Any = None
        if mode == "text":
            data = await dom_helper.extract_text(selectors)
        elif mode == "all_text":
            data = await dom_helper.extract_all_text(selectors)
        elif mode == "blocks":
            item_selector = params.get("item_selector")
            fields = params.get("fields")
            if not item_selector or not fields:
                raise ValueError("extract_text task with mode='blocks' requires 'item_selector' and 'fields' parameters.")
            data = await dom_helper.extract_blocks(selectors, item_selector, fields)
        else:
            raise ValueError(f"Unsupported extraction mode: {mode}")

        logger.debug(f"ExtractTextTask: extracted {output_key} -> {data}")
        return {output_key: data}

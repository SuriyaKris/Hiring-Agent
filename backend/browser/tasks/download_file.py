"""Browser Task: Download File — Milestone 3.4."""

from typing import List
from playwright.async_api import Page
from browser.dom_helper import DOMHelper
from browser.tasks.base_task import BaseBrowserTask
from loguru import logger
import os


class DownloadFileTask(BaseBrowserTask):
    """Task to trigger download event and return local file path."""

    @property
    def name(self) -> str:
        return "download_file"

    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        selectors = params.get("selectors")
        output_key = params.get("output_key", "download_path")
        timeout = params.get("timeout", 15000)

        if not selectors:
            raise ValueError("download_file task requires 'selectors' parameter.")

        logger.info(f"DownloadFileTask: waiting for download event via click on {selectors}")
        loc = await dom_helper.find_section(selectors)
        if not loc:
            raise RuntimeError(f"Download link matching {selectors} not found on page.")

        temp_dir = params.get("temp_dir", os.path.join(os.getcwd(), "temp_downloads"))
        os.makedirs(temp_dir, exist_ok=True)

        async with page.expect_download(timeout=timeout) as download_info:
            await loc.first.click()

        download = await download_info.value
        download_path = os.path.join(temp_dir, download.suggested_filename)
        await download.save_as(download_path)

        logger.info(f"DownloadFileTask: download completed -> {download_path}")
        return {output_key: download_path}

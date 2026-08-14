"""Browser Tasks exports and registry map."""

from browser.tasks.base_task import BaseBrowserTask
from browser.tasks.open_page import OpenPageTask
from browser.tasks.wait_for_page import WaitForPageTask
from browser.tasks.scroll import ScrollTask
from browser.tasks.expand import ExpandTask
from browser.tasks.extract_text import ExtractTextTask
from browser.tasks.screenshot import ScreenshotTask
from browser.tasks.download_file import DownloadFileTask
from browser.tasks.click import ClickTask

# Centralised registry mapping task type strings to their execution object singletons
TASK_REGISTRY = {
    "open_page": OpenPageTask(),
    "wait_for_page": WaitForPageTask(),
    "scroll": ScrollTask(),
    "expand": ExpandTask(),
    "extract_text": ExtractTextTask(),
    "screenshot": ScreenshotTask(),
    "download_file": DownloadFileTask(),
    "click": ClickTask(),
}

"""Base Browser Task Class — Milestone 3.4.

Defines the interface all generic task modules must implement.
"""

from abc import ABC, abstractmethod
from playwright.async_api import Page
from browser.dom_helper import DOMHelper


class BaseBrowserTask(ABC):
    """Abstract Base Class for modular browser steps."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier string matching task_type in BrowserPlanStep."""
        pass

    @abstractmethod
    async def execute(self, page: Page, dom_helper: DOMHelper, params: dict, context: dict) -> dict:
        """Perform the browser action and return any extracted metadata or results.

        Args:
            page:       Playwright active Page object.
            dom_helper: Instantiated DOMHelper for element interaction.
            params:     Input parameters dictionary defined in the plan step.
            context:    Shared runtime dictionary passed across steps.

        Returns:
            Dictionary containing result updates to merge into the shared execution results.
        """
        pass

"""Session Manager for loading and persisting cookie states across scraper runs."""

import os
from typing import Dict
from playwright.async_api import Browser, BrowserContext
from browser.browser_config import BrowserConfig
from loguru import logger


class SessionManager:
    """Manages browser contexts, cookies, and local session states for different recruiters/sources."""

    def __init__(self, session_dir: str = "sessions"):
        self.session_dir = session_dir
        os.makedirs(session_dir, exist_ok=True)
        self._active_contexts: Dict[str, BrowserContext] = {}

    def _get_session_path(self, session_id: str) -> str:
        """Get the file path to persist session state for a given ID."""
        return os.path.join(self.session_dir, f"{session_id}.json")

    async def get_or_create_context(
        self, session_id: str, browser: any, config: BrowserConfig
    ) -> BrowserContext:
        """Create or retrieve a BrowserContext, loading state from disk if it exists."""
        if session_id in self._active_contexts:
            return self._active_contexts[session_id]

        from playwright.async_api import BrowserContext
        if isinstance(browser, BrowserContext) or not hasattr(browser, "new_context"):
            logger.info(f"Using Camoufox persistent context directly for session '{session_id}'")
            try:
                browser.set_default_timeout(config.default_timeout)
            except Exception:
                pass
            self._active_contexts[session_id] = browser
            return browser

        session_path = self._get_session_path(session_id)
        context_options = {
            "viewport": {"width": config.viewport_width, "height": config.viewport_height},
            "user_agent": config.user_agent,
        }

        if os.path.exists(session_path):
            logger.info(f"Loading existing session context for '{session_id}' from {session_path}")
            context_options["storage_state"] = session_path
        else:
            logger.info(f"Creating new session context for '{session_id}'")

        context = await browser.new_context(**context_options)
        context.set_default_timeout(config.default_timeout)

        self._active_contexts[session_id] = context
        return context

    async def save_session_state(self, session_id: str):
        """Save storage state (cookies, local storage) of context to disk."""
        context = self._active_contexts.get(session_id)
        if not context:
            logger.warning(f"No active context found for session '{session_id}' to save.")
            return

        session_path = self._get_session_path(session_id)
        await context.storage_state(path=session_path)
        logger.info(f"Saved session context state for '{session_id}' to {session_path}")

    async def close_session(self, session_id: str):
        """Clean up and close an active session context."""
        context = self._active_contexts.pop(session_id, None)
        if context:
            from browser.browser_manager import BrowserManager
            # If the context is the global persistent context managed by BrowserManager, do not close it here
            if context == getattr(BrowserManager, "_browser", None):
                logger.info(f"Skipping context close for shared Camoufox context in session '{session_id}'")
            else:
                await context.close()
                logger.info(f"Closed browser context for session '{session_id}'")

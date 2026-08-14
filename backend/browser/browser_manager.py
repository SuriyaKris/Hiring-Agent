"""Browser Manager Singleton for centralizing Camoufox lifecycle."""

from typing import Optional
from playwright.async_api import BrowserContext
from browser.browser_config import BrowserConfig
from loguru import logger
from camoufox.async_api import AsyncCamoufox


class BrowserManager:
    """Manages a single, shared Camoufox persistent context instance for multiple scrapers."""

    _camoufox: Optional[AsyncCamoufox] = None
    _browser: Optional[BrowserContext] = None

    @classmethod
    async def get_browser(cls, config: Optional[BrowserConfig] = None) -> BrowserContext:
        """Get or launch the shared Camoufox persistent context instance."""
        if cls._browser is None:
            if config is None:
                config = BrowserConfig()

            import os
            profile_path = config.profile_dir
            if not os.path.isabs(profile_path):
                # PROJECT_ROOT is two levels up from e:/Hiring-Agent- testt/backend/browser/browser_manager.py
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                profile_path = os.path.normpath(os.path.join(base_dir, profile_path))

            logger.info(f"Launching shared Camoufox browser (headless={config.headless}) with profile {profile_path}...")
            
            launch_args = {
                "headless": config.headless,
                "persistent_context": True,
                "user_data_dir": profile_path,
                "humanize": True,
                "i_know_what_im_doing": True,
            }
            if config.proxy:
                launch_args["proxy"] = config.proxy

            cls._camoufox = AsyncCamoufox(**launch_args)
            # Enter the context manager to start Camoufox and get BrowserContext
            cls._browser = await cls._camoufox.__aenter__()
            logger.info(f"Camoufox browser context successfully launched with profile {profile_path}.")

            # Register a close listener to clean up references when the context is closed
            cls._browser.on("close", lambda _: cls._reset_refs())

        return cls._browser

    @classmethod
    def _reset_refs(cls):
        """Reset internal singleton references."""
        cls._browser = None
        cls._camoufox = None
        logger.debug("Camoufox references reset due to context close.")

    @classmethod
    async def close_browser(cls):
        """Clean up and close the active Camoufox persistent context instance."""
        if cls._camoufox:
            logger.info("Closing Camoufox browser context...")
            try:
                await cls._camoufox.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error exiting Camoufox context manager: {e}")
            cls._reset_refs()
            logger.info("Camoufox browser context closed.")

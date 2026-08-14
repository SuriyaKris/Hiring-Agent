"""Browser Configuration Settings for Playwright Automation."""

from typing import Optional
from pydantic_settings import BaseSettings


class BrowserConfig(BaseSettings):
    """Holds configuration parameters for the automated Playwright browser."""
    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 800
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    default_timeout: int = 30000  # in milliseconds
    proxy: Optional[dict] = None
    screenshot_dir: str = "screenshots"
    profile_dir: str = "./browser_profiles/linkedin_profile"

    class Config:
        env_prefix = "BROWSER_"
        env_file = ".env"
        extra = "ignore"

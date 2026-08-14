"""Health Check System — Milestone: Health Checks.

Every scraper reports structured health status, not just a boolean.
In production you ask: "Why is LinkedIn enrichment failing?"
HealthReport answers that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from loguru import logger


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class HealthReport:
    """Structured health status for a scraper instance."""
    scraper_name: str

    # Auth & access
    can_login: bool = False

    # DOM sanity checks
    selectors_found: List[str] = field(default_factory=list)
    selectors_missing: List[str] = field(default_factory=list)

    # Anti-bot signals
    rate_limited: bool = False
    captcha_detected: bool = False

    # Overall extraction outcome
    extraction_success: bool = False
    error_message: Optional[str] = None

    # Timestamp
    checked_at: datetime = field(default_factory=datetime.utcnow)
    notes: str = ""

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def is_healthy(self) -> bool:
        """True only when site is reachable, not blocked, and selectors work."""
        return (
            self.extraction_success
            and not self.rate_limited
            and not self.captcha_detected
        )

    @property
    def status_label(self) -> str:
        if self.captcha_detected:
            return "CAPTCHA"
        if self.rate_limited:
            return "RATE_LIMITED"
        if not self.can_login:
            return "AUTH_REQUIRED"
        if not self.extraction_success:
            return "EXTRACTION_FAILED"
        return "OK"

    def to_dict(self) -> dict:
        return {
            "scraper": self.scraper_name,
            "status": self.status_label,
            "is_healthy": self.is_healthy,
            "can_login": self.can_login,
            "selectors_found": self.selectors_found,
            "selectors_missing": self.selectors_missing,
            "rate_limited": self.rate_limited,
            "captcha_detected": self.captcha_detected,
            "extraction_success": self.extraction_success,
            "error_message": self.error_message,
            "checked_at": self.checked_at.isoformat(),
            "notes": self.notes,
        }


# ── HealthChecker ─────────────────────────────────────────────────────────────

class HealthChecker:
    """Runs a structured health check against a live Playwright page.

    Usage:
        checker = HealthChecker(page, scraper_name="LinkedIn")
        report  = await checker.check(
            key_selectors=["#main-content", ".profile-header"],
            captcha_selectors=["#captcha", ".challenge-page"],
            rate_limit_selectors=[".rate-limit-message"],
        )
    """

    def __init__(self, page, scraper_name: str):
        self.page = page
        self.scraper_name = scraper_name

    async def check(
        self,
        key_selectors: List[str],
        captcha_selectors: Optional[List[str]] = None,
        rate_limit_selectors: Optional[List[str]] = None,
        auth_indicator_selectors: Optional[List[str]] = None,
        timeout: int = 5000,
    ) -> HealthReport:
        """Run all health checks and return a HealthReport.

        Args:
            key_selectors:           Selectors that MUST be present for healthy extraction.
            captcha_selectors:       Selectors that indicate a CAPTCHA challenge.
            rate_limit_selectors:    Selectors that indicate rate limiting.
            auth_indicator_selectors: Selectors that indicate the user IS logged in.
            timeout:                 Per-selector check timeout in ms.

        Returns:
            A populated HealthReport.
        """
        report = HealthReport(scraper_name=self.scraper_name)

        # ── CAPTCHA check ─────────────────────────────────────────────────────
        if captcha_selectors:
            for sel in captcha_selectors:
                try:
                    loc = self.page.locator(sel)
                    if await loc.count() > 0:
                        report.captcha_detected = True
                        report.notes += f"Captcha selector matched: {sel}. "
                        logger.warning(f"[{self.scraper_name}] CAPTCHA detected via '{sel}'")
                        break
                except Exception:
                    pass

        # ── Rate limit check ──────────────────────────────────────────────────
        if rate_limit_selectors:
            for sel in rate_limit_selectors:
                try:
                    loc = self.page.locator(sel)
                    if await loc.count() > 0:
                        report.rate_limited = True
                        report.notes += f"Rate limit selector matched: {sel}. "
                        logger.warning(f"[{self.scraper_name}] Rate limited via '{sel}'")
                        break
                except Exception:
                    pass

        # ── Auth check ────────────────────────────────────────────────────────
        if "login" in self.page.url or "signup" in self.page.url or "authwall" in self.page.url:
            report.can_login = False
            logger.debug(f"[{self.scraper_name}] Auth failed: Redirected to auth screen/login/signup/authwall (url={self.page.url})")
        elif auth_indicator_selectors:
            for sel in auth_indicator_selectors:
                try:
                    loc = self.page.locator(sel)
                    await loc.first.wait_for(state="attached", timeout=2000)
                    if await loc.count() > 0:
                        report.can_login = True
                        logger.debug(f"[{self.scraper_name}] Auth confirmed via '{sel}'")
                        break
                except Exception:
                    pass
        else:
            # If no auth selectors given, assume session may be present
            report.can_login = True

        # ── Key selector checks ───────────────────────────────────────────────
        for sel in key_selectors:
            try:
                loc = self.page.locator(sel)
                await loc.first.wait_for(state="attached", timeout=timeout)
                if await loc.count() > 0:
                    report.selectors_found.append(sel)
                else:
                    report.selectors_missing.append(sel)
            except Exception:
                report.selectors_missing.append(sel)

        # ── Determine overall extraction success ──────────────────────────────
        if report.captcha_detected or report.rate_limited:
            report.extraction_success = False
        elif report.selectors_found:
            report.extraction_success = True
        else:
            report.extraction_success = False
            report.error_message = "No key selectors found on page."

        status = report.status_label
        logger.info(
            f"[{self.scraper_name}] Health check complete — "
            f"status={status}, found={len(report.selectors_found)}, "
            f"missing={len(report.selectors_missing)}"
        )
        return report

"""Browser Agent — Milestone 3.2.

Orchestrates intent-driven browser automation. Resolves objectives, compiles
generic plans, executes them step-by-step using modular tasks, and returns
inspectable status logs and final results.

This class knows nothing about site-specific CSS selectors.
All site-specific locators are loaded from external configs.
"""

import time
import traceback
from typing import Dict, Any, List, Optional, Union
from loguru import logger

from browser.models.enrichment_objective import EnrichmentObjective
from browser.models.browser_plan import BrowserPlan, BrowserPlanStep
from browser.models.browser_state import BrowserState
from browser.models.browser_result import BrowserResult
from browser.browser_manager import BrowserManager
from browser.session_manager import SessionManager
from browser.dom_helper import DOMHelper
from browser.tasks import TASK_REGISTRY
from browser.browser_config import BrowserConfig
from browser.health_check import HealthChecker, HealthReport


# ── Site selector configurations ──────────────────────────────────────────────
# Maps target platform names to parameter arrays for generic tasks.
# To support a new site, simply append its configuration here.

SITE_TASKS_CONFIG: Dict[str, Dict[str, Any]] = {
    "linkedin": {
        "auth_indicators": [".global-nav__me-photo", "#global-nav"],
        "sections": {
            "name": {
                "extract_selectors": [
                    "h1.text-heading-xlarge",
                    ".pv-text-details__left-panel h1",
                    "h1.top-card-layout__title",
                    "h1"
                ],
                "mode": "text"
            },
            "about": {
                "expand_selectors": ["button[aria-label*='see more']", ".inline-show-more-text__button"],
                "extract_selectors": [
                    "#about ~ .pvs-list__outer-container .visually-hidden",
                    "#about",
                    ".pv-about__summary-text",
                    "section.summary p",
                    "section.summary"
                ],
                "mode": "text"
            },
            "skills": {
                "expand_selectors": ["button[aria-label*='Show all skills']", "button:has-text('Show all')"],
                "extract_selectors": [
                    "#skills-section",
                    "section[data-section='skills']",
                    ".pv-skill-categories-section"
                ],
                "mode": "blocks",
                "item_selector": ".pvs-list__item--line-separated, li",
                "fields": {
                    "name": [".t-bold span", "span[aria-hidden='true']"]
                }
            },
            "experience": {
                "expand_selectors": ["button[aria-label*='Show all experiences']", "button:has-text('Show all')"],
                "extract_selectors": [
                    "#experience ~ .pvs-list__outer-container",
                    "#experience",
                    "section[data-section='experience']",
                    "section.experience"
                ],
                "mode": "blocks",
                "item_selector": ".pvs-list__item--line-separated, .pv-entity__position-group-pager, li.experience-item, .experience-item",
                "fields": {
                    "title": [".t-bold span", "span[aria-hidden='true']:nth-child(1)", "h3.experience-item__title", ".experience-item__title"],
                    "company_name": [".t-normal span", ".pv-entity__secondary-title", "h4.experience-item__subtitle", ".experience-item__subtitle"],
                    "dates": [".pvs-entity__caption-wrapper", ".pv-entity__date-range span:nth-child(2)", "span.experience-item__duration", ".experience-item__duration"],
                    "description": [".pvs-list__item--with-top-padding span", ".pv-entity__description", "p.experience-item__description", ".experience-item__description"]
                }
            }
        }
    },
    "indeed": {
        "auth_indicators": [".indeed-nav", ".navHeader"],
        "sections": {
            "resume": {
                "mode": "download",
                "selectors": [".indeed-resume-download", "a[href*='download']", "button:has-text('Download')"]
            },
            "headline": {
                "extract_selectors": [".indeed-headline", "h1"],
                "mode": "text"
            }
        }
    }
}


class BrowserAgent:
    """Core browser automation agent translating high level objectives into sequential plans."""

    def __init__(
        self,
        session_id: str = "default_agent",
        config: Optional[BrowserConfig] = None,
        session_manager: Optional[SessionManager] = None
    ):
        self.session_id = session_id
        self.config = config or BrowserConfig()
        self.session_manager = session_manager or SessionManager()

    # ── Plan compilation ──────────────────────────────────────────────────────

    def compile_plan(self, objective: EnrichmentObjective) -> BrowserPlan:
        """Compile a BrowserObjective into a sequence of concrete steps/tasks."""
        site_key = objective.site.lower()
        site_cfg = SITE_TASKS_CONFIG.get(site_key, {})

        steps = []

        # 1. Navigation task
        target_url = objective.url or objective.candidate_url
        if not target_url:
            raise ValueError("EnrichmentObjective must specify either 'url' or 'candidate_url'.")

        steps.append(BrowserPlanStep(
            task_type="open_page",
            params={"url": target_url, "timeout": objective.timeout}
        ))

        # 2. Extraction loop
        if "candidate_urls" in objective.sections:
            # Map platform to search result anchor selectors for Fallback URL Processing
            result_selectors = {
                "linkedin": ["a.app-aware-link", ".search-results-container a"],
                "indeed": ["a.jcs-JobTitle", "a[href*='/rc/clk']"],
            }
            selectors = result_selectors.get(site_key, ["a"])
            steps.append(BrowserPlanStep(
                task_type="extract_text",
                params={
                    "selectors": ["body"],
                    "mode": "blocks",
                    "output_key": "candidate_urls",
                    "item_selector": ", ".join(selectors),
                    "fields": {
                        "url": ["@href"]
                    }
                }
            ))
        else:
            for section in objective.sections:
                sec_cfg = site_cfg.get("sections", {}).get(section.lower())
                if not sec_cfg:
                    logger.warning(f"BrowserAgent: no task configuration found for section '{section}' on site '{objective.site}'")
                    continue

                # Special case: download action
                if sec_cfg.get("mode") == "download":
                    steps.append(BrowserPlanStep(
                        task_type="download_file",
                        params={
                            "selectors": sec_cfg["selectors"],
                            "output_key": f"downloaded_{section}"
                        }
                    ))
                else:
                    # 2a. Expand collapsible sections
                    if "expand_selectors" in sec_cfg:
                        steps.append(BrowserPlanStep(
                            task_type="expand",
                            params={"selectors": sec_cfg["expand_selectors"]}
                        ))

                    # 2b. Extract text content
                    extract_params = {
                        "selectors": sec_cfg["extract_selectors"],
                        "mode": sec_cfg["mode"],
                        "output_key": section
                    }
                    if sec_cfg["mode"] == "blocks":
                        extract_params["item_selector"] = sec_cfg["item_selector"]
                        extract_params["fields"] = sec_cfg["fields"]

                    steps.append(BrowserPlanStep(
                        task_type="extract_text",
                        params=extract_params
                    ))

        # 3. Screenshot log task
        steps.append(BrowserPlanStep(
            task_type="screenshot",
            params={"name": "final_page", "screenshot_dir": self.config.screenshot_dir}
        ))

        return BrowserPlan(objective=objective, steps=steps)

    # ── Plan Execution ────────────────────────────────────────────────────────

    async def execute_plan(self, plan: BrowserPlan) -> BrowserResult:
        """Execute all steps of the BrowserPlan sequentially, maintaining BrowserState."""
        logger.info(f"[{self.session_id}] Executing BrowserPlan containing {len(plan.steps)} steps.")
        plan.status = "running"

        state = BrowserState()
        profile_data = {}
        context = {
            "session_id": self.session_id,
            "config": self.config
        }

        browser = await BrowserManager.get_browser(self.config)
        context_obj = await self.session_manager.get_or_create_context(self.session_id, browser, self.config)
        page = await context_obj.new_page()
        dom_helper = DOMHelper(page)

        # Check authentication state and login automatically if credentials are provided in settings
        from config import get_settings
        settings = get_settings()
        site_key = plan.objective.site.lower()
        
        if site_key == "linkedin" and settings.linkedin_username and settings.linkedin_password:
            from browser.scrapers.linkedin_scraper.authentication import check_auth_state, login as linkedin_login
            is_auth = await check_auth_state(page)
            if not is_auth:
                logger.info(f"[{self.session_id}] Automated LinkedIn login initiated using settings credentials.")
                credentials = {
                    "username": settings.linkedin_username,
                    "password": settings.linkedin_password
                }
                login_success = await linkedin_login(page, credentials)
                if login_success:
                    await self.session_manager.save_session_state(self.session_id)
                    logger.info(f"[{self.session_id}] LinkedIn logged in and session state persisted successfully.")

        health_report = None
        success = True

        try:
            for step in plan.steps:
                step.status = "running"
                start_time = time.monotonic()
                task_impl = TASK_REGISTRY.get(step.task_type)

                if not task_impl:
                    raise KeyError(f"No task execution module registered for task_type '{step.task_type}'")

                try:
                    logger.debug(f"[{self.session_id}] Running step: {step.task_type} with params={step.params}")
                    step_results = await task_impl.execute(page, dom_helper, step.params, context)

                    # Update BrowserState depending on task results
                    if step.task_type == "open_page":
                        url_navigated = step.params.get("url")
                        state.current_url = url_navigated
                        state.visited_pages.append(url_navigated)
                    elif step.task_type == "screenshot":
                        screenshot_path = step_results.get("screenshot_path")
                        if screenshot_path:
                            state.screenshots.append(screenshot_path)
                    elif step.task_type == "download_file":
                        download_path = step_results.get(step.params.get("output_key", "download_path"))
                        if download_path:
                            state.downloaded_files.append(download_path)
                    else:
                        profile_data.update(step_results)

                    step.status = "completed"
                except Exception as e:
                    step.status = "failed"
                    step.error_message = str(e)
                    state.errors.append(f"Step '{step.task_type}' failed: {e}")
                    logger.error(f"[{self.session_id}] Step '{step.task_type}' failed: {e}\n{traceback.format_exc()}")
                    plan.status = "failed"
                    success = False

                    # Capture screenshot on failure for easier diagnostic tracing
                    try:
                        filename = f"{self.session_id}_error_step_{step.task_type}.png"
                        import os
                        os.makedirs(self.config.screenshot_dir, exist_ok=True)
                        err_screenshot = os.path.join(self.config.screenshot_dir, filename)
                        await page.screenshot(path=err_screenshot)
                        state.screenshots.append(err_screenshot)
                    except Exception:
                        pass
                    raise
                finally:
                    duration = round(time.monotonic() - start_time, 3)
                    step.duration_seconds = duration
                    state.metrics[step.task_type] = state.metrics.get(step.task_type, 0.0) + duration

            # Compile HealthReport at the end if we navigated anywhere
            if state.current_url:
                site_key = plan.objective.site.lower()
                site_cfg = SITE_TASKS_CONFIG.get(site_key, {})
                auth_selectors = site_cfg.get("auth_indicators", [])

                # Verify if user is logged in
                is_auth = False
                for sel in auth_selectors:
                    try:
                        if await page.locator(sel).count() > 0:
                            is_auth = True
                            break
                    except Exception:
                        pass
                state.authenticated = is_auth

                try:
                    checker = HealthChecker(page, scraper_name=plan.objective.site)
                    # Use a lightweight check since we are already on the page
                    health_report = await checker.check(
                        key_selectors=auth_selectors[:1] if auth_selectors else [],
                        auth_indicator_selectors=auth_selectors
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate health report: {e}")

            plan.status = "completed"
            logger.info(f"[{self.session_id}] BrowserPlan execution completed successfully.")
        except Exception as e:
            plan.status = "failed"
            success = False
            raise RuntimeError(f"BrowserPlan execution failed: {e}") from e
        finally:
            await page.close()

        return BrowserResult(
            success=success,
            profile=profile_data,
            screenshots=state.screenshots,
            downloads=state.downloaded_files,
            metrics=state.metrics,
            health_report=health_report,
            errors=state.errors
        )

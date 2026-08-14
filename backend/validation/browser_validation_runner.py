"""Browser Validation Runner — Milestone 4.2.

Executes regression/validation testing across target candidate profiles to catch selector breakage.
Generates comprehensive failure JSON reports (including plan, result, health check, screenshot paths)
and updates a centralized JSON dashboard.
"""

import dataclasses
import json
import os
import re
import time
from typing import List, Dict, Any, Optional
from loguru import logger

from browser.models.enrichment_objective import EnrichmentObjective
from agents.browser_agent import BrowserAgent
from validation.browser_validation_result import BrowserValidationResult, ProfileResult
from browser.browser_config import BrowserConfig


class BrowserValidationRunner:
    """Service to load datasets, execute objectives via BrowserAgent, and output verification reports."""

    def __init__(self, config: Optional[BrowserConfig] = None):
        self.config = config or BrowserConfig()

    def load_dataset(self, file_path: str) -> List[Dict[str, Any]]:
        """Load profile configuration items from a JSON file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Validation dataset file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def validate_profile_item(self, item: Dict[str, Any], platform: str) -> ProfileResult:
        """Execute validation against a single candidate profile config item."""
        name = item.get("name", "Unknown")
        url = item.get("url")
        expected_sections = item.get("expected_sections", [])

        if not url:
            raise ValueError(f"Profile validation item for '{name}' must specify a 'url' parameter.")

        logger.info(f"[Validation] Sourcing '{name}' | platform={platform} | URL={url}")

        agent = BrowserAgent(
            session_id=f"validation_{platform}_{name.replace(' ', '_').lower()}",
            config=self.config
        )

        objective = EnrichmentObjective(
            goal="EnrichCandidate",
            site=platform,
            url=url,
            sections=expected_sections
        )

        plan = agent.compile_plan(objective)
        start_time = time.monotonic()
        
        success = True
        sections_found = []
        sections_missing = []
        errors = []
        profile_extracted = {}
        browser_result = None

        try:
            browser_result = await agent.execute_plan(plan)
            profile_extracted = browser_result.profile
            success = browser_result.success
            errors.extend(browser_result.errors)
        except Exception as e:
            success = False
            errors.append(str(e))

        duration = round(time.monotonic() - start_time, 3)

        # Compare expected vs actual fields
        for section in expected_sections:
            extracted_val = profile_extracted.get(section)
            # Section is found if it exists in profile and has non-empty contents
            if extracted_val and (not isinstance(extracted_val, (list, dict)) or len(extracted_val) > 0):
                sections_found.append(section)
            else:
                sections_missing.append(section)

        # If any expected sections are missing, we mark this run as unsuccessful
        run_success = success and (len(sections_missing) == 0)

        logger.info(
            f"[Validation] Outcome '{name}': success={run_success} | "
            f"found={sections_found} | missing={sections_missing} | duration={duration}s"
        )

        # If failed, write a detailed failed review report JSON file
        if not run_success:
            try:
                reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", platform)
                os.makedirs(reports_dir, exist_ok=True)
                
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
                report_file_path = os.path.join(reports_dir, f"failed_{safe_name}.json")
                
                failed_data = {
                    "name": name,
                    "url": url,
                    "expected_sections": expected_sections,
                    "sections_found": sections_found,
                    "sections_missing": sections_missing,
                    "errors": errors,
                    "screenshot_path": browser_result.screenshots[0] if (browser_result and browser_result.screenshots) else None,
                    "browser_plan": plan.model_dump() if hasattr(plan, "model_dump") else plan.dict(),
                    "browser_result": (browser_result.model_dump() if hasattr(browser_result, "model_dump") else browser_result.dict()) if browser_result else None,
                    "health_report": dataclasses.asdict(browser_result.health_report) if (browser_result and browser_result.health_report) else None
                }
                
                with open(report_file_path, "w", encoding="utf-8") as f:
                    json.dump(failed_data, f, indent=2, default=str)
                logger.info(f"[Validation] Saved failure analysis report for '{name}' to {report_file_path}")
            except Exception as report_err:
                logger.warning(f"Could not generate validation failure report JSON: {report_err}")

        return ProfileResult(
            name=name,
            url=url,
            platform=platform,
            success=run_success,
            sections_found=sections_found,
            sections_missing=sections_missing,
            duration=duration,
            errors=errors
        )

    async def validate_dataset(self, file_path: str, platform: str) -> BrowserValidationResult:
        """Run validation testing across all candidate configurations inside a dataset JSON file."""
        items = self.load_dataset(file_path)
        results = []

        for item in items:
            try:
                res = await self.validate_profile_item(item, platform)
                results.append(res)
            except Exception as e:
                logger.error(f"[Validation] Critical execution error on item '{item.get('name')}': {e}")
                results.append(ProfileResult(
                    name=item.get("name", "Unknown"),
                    url=item.get("url", ""),
                    platform=platform,
                    success=False,
                    errors=[str(e)]
                ))

        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        success_rate = round(successful / total, 4) if total > 0 else 0.0

        # Calculate average duration
        avg_dur = round(sum(r.duration for r in results) / total, 3) if total > 0 else 0.0

        # Calculate section accuracies
        sec_stats = {}
        for r in results:
            for sec in r.sections_found:
                stats = sec_stats.setdefault(sec, [0, 0])
                stats[0] += 1
                stats[1] += 1
            for sec in r.sections_missing:
                stats = sec_stats.setdefault(sec, [0, 0])
                stats[1] += 1
        
        section_accuracies = {
            sec: round(stats[0] / stats[1], 4)
            for sec, stats in sec_stats.items()
            if stats[1] > 0
        }

        # Failure report categorization
        failure_reasons = {
            "Selector Missing": 0,
            "Timeout": 0,
            "Captcha": 0,
            "Auth Required": 0,
            "Unknown": 0
        }

        for r in results:
            if not r.success:
                matched = False
                for err in r.errors:
                    err_lower = err.lower()
                    if "captcha" in err_lower:
                        failure_reasons["Captcha"] += 1
                        matched = True
                        break
                    elif "timeout" in err_lower:
                        failure_reasons["Timeout"] += 1
                        matched = True
                        break
                    elif "auth" in err_lower or "login" in err_lower:
                        failure_reasons["Auth Required"] += 1
                        matched = True
                        break
                    elif "selector" in err_lower or "not found" in err_lower or "missing" in err_lower:
                        failure_reasons["Selector Missing"] += 1
                        matched = True
                        break
                if not matched:
                    failure_reasons["Unknown"] += 1

        # Write or update validation dashboard JSON
        try:
            dashboard_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "dashboard.json")
            os.makedirs(os.path.dirname(dashboard_path), exist_ok=True)
            
            dashboard_data = {}
            if os.path.exists(dashboard_path):
                try:
                    with open(dashboard_path, "r", encoding="utf-8") as f:
                        dashboard_data = json.load(f)
                except Exception:
                    pass
            
            dashboard_data[platform] = {
                "profiles_tested": total,
                "success_rate": success_rate,
                "avg_duration": avg_dur,
                "captcha_count": failure_reasons["Captcha"],
                "selector_failures": failure_reasons["Selector Missing"],
                "sections": section_accuracies
            }
            
            with open(dashboard_path, "w", encoding="utf-8") as f:
                json.dump(dashboard_data, f, indent=2)
            logger.info(f"[Validation] Updated validation dashboard in {dashboard_path}")
        except Exception as dash_err:
            logger.warning(f"Could not update validation dashboard JSON: {dash_err}")

        return BrowserValidationResult(
            results=results,
            total_profiles=total,
            successful_runs=successful,
            failed_runs=failed,
            overall_success_rate=success_rate,
            section_accuracies=section_accuracies,
            failure_reasons=failure_reasons,
            average_duration=avg_dur
        )

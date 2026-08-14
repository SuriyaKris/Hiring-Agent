"""Discovery Validation Engine — Milestone 5.6.

Compiles search coverage, duplicates ratio, latency averages, and provider success rates.
"""

import json
import os
from typing import Dict, Any
from loguru import logger


class DiscoveryValidationReporter:
    """Compiles and exports search validation statistics to Discovery Reports."""

    def __init__(self, reports_dir: str = None):
        self.reports_dir = reports_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "reports"
        )
        os.makedirs(self.reports_dir, exist_ok=True)

    def generate_report(self, discovery_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compile statistical outcomes from the discovery run context and save report JSON."""
        metrics = discovery_result.get("metrics", {})
        providers = metrics.get("providers", {})

        total_runs = len(providers)
        successful_runs = sum(1 for p in providers.values() if p.get("success"))
        success_rate = round(successful_runs / total_runs, 4) if total_runs > 0 else 0.0

        # Calculate average duration
        total_dur = sum(p.get("duration", 0.0) for p in providers.values())
        avg_dur = round(total_dur / total_runs, 3) if total_runs > 0 else 0.0

        # Platform coverage breakdown
        coverage = {}
        for p_name, p_met in providers.items():
            coverage[p_name] = p_met.get("count_found", 0)

        report = {
            "total_candidates_found": metrics.get("total_found", 0),
            "unique_candidates": metrics.get("unique_found", 0),
            "duplicates_detected": metrics.get("duplicates_removed", 0),
            "duplicate_ratio": round(metrics.get("duplicates_removed", 0) / metrics.get("total_found", 1), 4) if metrics.get("total_found", 0) > 0 else 0.0,
            "overall_search_success_rate": success_rate,
            "average_provider_search_duration": avg_dur,
            "total_execution_duration": metrics.get("total_duration", 0.0),
            "platform_coverage": coverage
        }

        # Write to discovery_report.json
        report_path = os.path.join(self.reports_dir, "discovery_report.json")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info(f"[Discovery Validation] Saved discovery report to {report_path}")
        except Exception as e:
            logger.warning(f"Could not save discovery validation report: {e}")

        return report

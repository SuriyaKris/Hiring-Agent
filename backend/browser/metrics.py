"""Metrics Store — Milestone: Build Metrics.

Tracks per-provider execution time, fields extracted, retries, failures,
and success rate. In-memory by default. Export to JSON for persistence.

When you ask "Why is LinkedIn enrichment suddenly failing?"
— these metrics answer that.
"""

from __future__ import annotations

import json
import threading
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class ExtractionMetric:
    """A single recorded extraction event."""
    provider: str
    session_id: str
    started_at: datetime
    duration_seconds: float = 0.0
    fields_extracted: List[str] = field(default_factory=list)
    fields_empty: List[str] = field(default_factory=list)
    retries: int = 0
    success: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["started_at"] = self.started_at.isoformat()
        return d


@dataclass
class ProviderSummary:
    """Aggregated statistics for a single provider."""
    provider: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_retries: int = 0
    avg_duration_seconds: float = 0.0
    avg_fields_extracted: float = 0.0
    success_rate: float = 0.0          # 0.0 – 1.0

    def to_dict(self) -> dict:
        return asdict(self)


# ── MetricsStore ──────────────────────────────────────────────────────────────

class MetricsStore:
    """Thread/async-safe in-memory metrics store.

    Usage:
        store = MetricsStore.instance()   # singleton
        store.record(metric)
        summary = store.get_summary("LinkedIn")
        store.export_json("metrics.json")
    """

    _instance: Optional[MetricsStore] = None
    _lock = threading.Lock()

    def __init__(self):
        self._metrics: List[ExtractionMetric] = []
        self._write_lock = threading.Lock()

    @classmethod
    def instance(cls) -> MetricsStore:
        """Return the global singleton MetricsStore."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = MetricsStore()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton — useful in tests."""
        with cls._lock:
            cls._instance = None

    # ── Write ─────────────────────────────────────────────────────────────────

    def record(self, metric: ExtractionMetric) -> None:
        """Append an ExtractionMetric to the store."""
        with self._write_lock:
            self._metrics.append(metric)
        status = "✓" if metric.success else "✗"
        logger.info(
            f"[Metrics] {status} {metric.provider} | "
            f"session={metric.session_id} | "
            f"duration={metric.duration_seconds:.2f}s | "
            f"fields={len(metric.fields_extracted)} extracted, "
            f"{len(metric.fields_empty)} empty | "
            f"retries={metric.retries}"
            + (f" | error={metric.error_message}" if metric.error_message else "")
        )

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_all(self) -> List[ExtractionMetric]:
        """Return a snapshot of all recorded metrics."""
        with self._write_lock:
            return list(self._metrics)

    def get_for_provider(self, provider: str) -> List[ExtractionMetric]:
        """Return all metrics for a given provider name."""
        return [m for m in self.get_all() if m.provider == provider]

    def get_summary(self, provider: str) -> ProviderSummary:
        """Compute aggregated statistics for a single provider.

        Args:
            provider: Provider name (e.g. "LinkedIn", "Indeed").

        Returns:
            ProviderSummary with averages computed over all recorded runs.
        """
        records = self.get_for_provider(provider)
        if not records:
            return ProviderSummary(provider=provider)

        total = len(records)
        successes = sum(1 for r in records if r.success)
        total_retries = sum(r.retries for r in records)
        avg_duration = sum(r.duration_seconds for r in records) / total
        avg_fields = sum(len(r.fields_extracted) for r in records) / total

        return ProviderSummary(
            provider=provider,
            total_runs=total,
            successful_runs=successes,
            failed_runs=total - successes,
            total_retries=total_retries,
            avg_duration_seconds=round(avg_duration, 3),
            avg_fields_extracted=round(avg_fields, 2),
            success_rate=round(successes / total, 4),
        )

    def get_all_summaries(self) -> List[ProviderSummary]:
        """Return summaries for every provider seen so far."""
        providers = {m.provider for m in self.get_all()}
        return [self.get_summary(p) for p in sorted(providers)]

    # ── Export ────────────────────────────────────────────────────────────────

    def export_json(self, path: str) -> None:
        """Persist all raw metrics to a JSON file.

        Args:
            path: Absolute or relative path to output .json file.
        """
        records = [m.to_dict() for m in self.get_all()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, default=str)
        logger.info(f"[Metrics] Exported {len(records)} records → {path}")

    def export_summary_json(self, path: str) -> None:
        """Persist provider summaries (aggregated) to a JSON file."""
        summaries = [s.to_dict() for s in self.get_all_summaries()]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summaries, f, indent=2)
        logger.info(f"[Metrics] Exported {len(summaries)} provider summaries → {path}")

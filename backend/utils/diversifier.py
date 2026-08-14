"""Candidate Diversifier — caps per-company representation in a ranked candidate list."""

from collections import defaultdict
from typing import TypeVar, Callable
from loguru import logger

T = TypeVar("T")


def diversify_by_company(
    candidates: list[T],
    get_company: Callable[[T], str],
    max_per_company: int = 3,
    max_total: int | None = None,
) -> list[T]:
    """
    Cap the number of candidates from any single company.

    IMPORTANT: `candidates` must already be sorted by whatever ranking/quality
    signal is available (search relevance order, or feature-engineering score
    if this runs post-scoring) BEFORE calling this function — this function
    preserves order, it does not re-rank. Taking the first N per company only
    makes sense if "first" already means "best."
    """
    company_counts: dict[str, int] = defaultdict(int)
    diversified: list[T] = []
    dropped_count = 0

    for candidate in candidates:
        company_key = (get_company(candidate) or "unknown").strip().lower()
        if company_counts[company_key] < max_per_company:
            diversified.append(candidate)
            company_counts[company_key] += 1
        else:
            dropped_count += 1

        if max_total is not None and len(diversified) >= max_total:
            break

    logger.info(
        f"[Diversity] Kept {len(diversified)} candidates across {len(company_counts)} companies "
        f"(dropped {dropped_count} for exceeding max_per_company={max_per_company})"
    )
    return diversified

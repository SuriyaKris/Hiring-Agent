"""Candidate Diversifier — caps per-company representation in a ranked candidate list."""

from collections import defaultdict
from typing import TypeVar, Callable
from loguru import logger

T = TypeVar("T")


def diversify_by_company(
    candidates: list[T],
    get_company: Callable[[T], str],
    max_per_company: int = 5,
    max_total: int | None = None,
) -> list[T]:
    """
    Cap the number of candidates from any single company while ensuring up to max_total
    candidates are preserved in the result list.
    """
    company_counts: dict[str, int] = defaultdict(int)
    diversified: list[T] = []
    overflow: list[T] = []

    for candidate in candidates:
        company_key = (get_company(candidate) or "unknown").strip().lower()
        if company_counts[company_key] < max_per_company:
            diversified.append(candidate)
            company_counts[company_key] += 1
        else:
            overflow.append(candidate)

        if max_total is not None and len(diversified) >= max_total:
            break

    # If we haven't reached max_total, fill remaining slots from overflow
    if max_total is not None and len(diversified) < max_total:
        needed = max_total - len(diversified)
        diversified.extend(overflow[:needed])

    logger.info(
        f"[Diversity] Kept {len(diversified)} candidates across {len(company_counts)} companies"
    )
    return diversified[:max_total] if max_total else diversified

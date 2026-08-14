"""Candidate Aggregator — Merges candidate lists from diverse sourcing channels."""

from typing import List
from loguru import logger
from schemas.candidate_profile import CandidateProfile


class CandidateAggregator:
    """Consolidates candidates gathered across Apollo, Indeed, and LinkedIn streams."""

    def aggregate(
        self,
        apollo_candidates: List[CandidateProfile],
        fallback_candidates: List[CandidateProfile],
        exclusion_set: set = None,
        role_track_id = None
    ) -> List[CandidateProfile]:
        """Combine lists, maintaining precedence, and filtering duplicate or excluded profiles."""
        logger.info(f"[Candidate Aggregator] Merging {len(apollo_candidates)} Apollo and {len(fallback_candidates)} fallback candidates")
        
        from identity.matching_engine import normalize_val
        
        seen_urls = set()
        unique_candidates = []

        # Helper to check if a candidate is in the exclusion set
        def is_excluded(cand: CandidateProfile) -> bool:
            if not exclusion_set:
                return False
            norm_apollo_id = normalize_val(cand.metadata.apollo_person_id)
            norm_linkedin = normalize_val(cand.basic_info.linkedin_url)
            norm_email = normalize_val(cand.basic_info.email)
            
            if (norm_apollo_id and norm_apollo_id in exclusion_set) or \
               (norm_linkedin and norm_linkedin in exclusion_set) or \
               (norm_email and norm_email in exclusion_set):
                logger.info(f"Excluded {cand.basic_info.full_name} — already surfaced in role_track {role_track_id}")
                return True
            return False

        # We prioritize Apollo profiles first
        for cand in apollo_candidates:
            if is_excluded(cand):
                continue
            url = cand.basic_info.linkedin_url
            if url:
                seen_urls.add(url.strip().lower())
            unique_candidates.append(cand)

        # Merge in fallback profiles without adding duplicate/excluded URLs
        for cand in fallback_candidates:
            if is_excluded(cand):
                continue
            url = cand.basic_info.linkedin_url or cand.basic_info.portfolio_url
            if url:
                norm_url = url.strip().lower()
                if norm_url in seen_urls:
                    logger.debug(f"[Candidate Aggregator] Skipping duplicate URL in aggregator: {url}")
                    continue
                seen_urls.add(norm_url)
            unique_candidates.append(cand)

        logger.info(f"[Candidate Aggregator] Aggregation complete. Total unique candidates: {len(unique_candidates)}")
        return unique_candidates

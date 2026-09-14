import uuid
import hashlib
import json
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import JDSearchSpec
from db import SearchSessionRecord
from nlp.embedding_model import SemanticEmbedder

# Cosine similarity threshold (similarity >= 0.90 <=> distance <= 0.10)
COSINE_DISTANCE_THRESHOLD = 0.10

def canonicalize_spec(spec: JDSearchSpec) -> str:
    """
    Produce a sorted, lowercased, canonical string representation of the sourcing spec.
    Includes job titles, skills, seniorities, and locations.
    """
    def clean_list(lst) -> list[str]:
        if not lst:
            return []
        cleaned = [str(x).strip().lower() for x in lst if x]
        return sorted(list(set(cleaned)))

    titles = clean_list(spec.primary_titles)
    skills = clean_list(spec.required_skills)
    seniorities = clean_list(spec.seniority_levels)
    geos = clean_list(spec.geo_keywords)

    return f"titles:{','.join(titles)}|skills:{','.join(skills)}|seniorities:{','.join(seniorities)}|geos:{','.join(geos)}"


def hash_spec(spec: JDSearchSpec) -> str:
    """Compute the SHA-256 fingerprint hash of the canonical spec string."""
    canonical_str = canonicalize_spec(spec)
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def get_spec_embedding(spec: JDSearchSpec) -> list[float]:
    """
    Convert the search spec to a natural language query and compute its 384-dimensional
    vector embedding using SemanticEmbedder.
    """
    # Build description string representing the spec
    titles_str = ", ".join(spec.primary_titles) if spec.primary_titles else "any"
    skills_str = ", ".join(spec.required_skills) if spec.required_skills else "any"
    locations_str = ", ".join(spec.geo_keywords) if spec.geo_keywords else "any"
    seniorities_str = ", ".join(spec.seniority_levels) if spec.seniority_levels else "any"

    text_to_embed = (
        f"Target Job Titles: {titles_str}. "
        f"Required Skills and Keywords: {skills_str}. "
        f"Target Locations: {locations_str}. "
        f"Seniority Levels: {seniorities_str}."
    )

    embedder = SemanticEmbedder()
    emb_array = embedder.get_embedding(text_to_embed)
    return emb_array.tolist()


async def find_or_create_role_track(
    db: AsyncSession,
    user_id: uuid.UUID,
    new_hash: str,
    new_vector: list[float]
) -> uuid.UUID:
    """
    Determine the role_track_id for a new search.
    1. Query exact spec_fingerprint_hash matches (fast).
    2. Query pgvector cosine-distance (<=>) for matching clusters under similarity threshold.
    3. Generate new UUID if no match.
    """
    # 1. Exact match search
    try:
        stmt = (
            select(SearchSessionRecord.role_track_id)
            .where(SearchSessionRecord.user_id == user_id)
            .where(SearchSessionRecord.spec_fingerprint_hash == new_hash)
            .where(SearchSessionRecord.role_track_id.isnot(None))
            .limit(1)
        )
        res = await db.execute(stmt)
        exact_match = res.scalar_one_or_none()
        if exact_match:
            from loguru import logger
            logger.info(f"Role Track match: Exact fingerprint match found. Reusing role_track_id: {exact_match}")
            return exact_match
    except Exception as e:
        from loguru import logger
        logger.warning(f"Role track exact match query failed: {e}")

    # 2. Vector similarity clustering (Cosine Distance <=> <= 0.10)
    try:
        stmt = (
            select(
                SearchSessionRecord.role_track_id,
                SearchSessionRecord.spec_embedding.cosine_distance(new_vector).label("distance")
            )
            .where(SearchSessionRecord.user_id == user_id)
            .where(SearchSessionRecord.role_track_id.isnot(None))
            .where(SearchSessionRecord.spec_embedding.isnot(None))
            .order_by(text("distance ASC"))
            .limit(1)
        )
        res = await db.execute(stmt)
        row = res.first()
        
        if row:
            matched_track_id, distance = row
            if distance is not None and distance <= COSINE_DISTANCE_THRESHOLD:
                from loguru import logger
                similarity = 1.0 - distance
                logger.info(f"Role Track match: Semantic similarity cluster match found (Similarity: {similarity:.2f}). Reusing role_track_id: {matched_track_id}")
                return matched_track_id
    except Exception as e:
        from loguru import logger
        logger.warning(f"Role track vector similarity query failed: {e}")

    # 3. Create a fresh role track
    new_track_id = uuid.uuid4()
    from loguru import logger
    logger.info(f"Role Track match: No matching fingerprint or cluster found. Generating new role_track_id: {new_track_id}")
    return new_track_id

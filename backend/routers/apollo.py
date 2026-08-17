"""Router: POST /api/apollo/search — triggers Apollo candidate intelligence queries."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from models.schemas import ApolloSearchRequest, SearchResponse, ScoredCandidate
from db import get_db, CandidateRecord
from providers.apollo_search import ApolloSearchProvider
from services.scoring_service import score_candidates_batch

router = APIRouter()


@router.post("/apollo/search", response_model=SearchResponse)
async def apollo_search_candidates(request: ApolloSearchRequest, db: AsyncSession = Depends(get_db)):
    """Search Apollo API using JDSearchSpec specifications and return scored candidate list."""
    try:
        searcher = ApolloSearchProvider()
        profiles = await searcher.search_profiles(request.spec, max_results=request.max_results)
        
        # Evaluate fitment scores
        scored = await score_candidates_batch(profiles, request.spec, concurrency=3)

        # Persist results in PostgreSQL database
        for c in scored:
            existing = await db.execute(
                select(CandidateRecord).where(CandidateRecord.linkedin_url == c.profile.basic_info.linkedin_url)
            )
            if not existing.scalar_one_or_none():
                current_job = c.profile.experience[0] if c.profile.experience else None
                current_title = current_job.title if current_job else (c.profile.basic_info.headline or "")
                current_company = current_job.company_name if current_job else (c.profile.company.name if c.profile.company else "")

                is_open = False
                raw = c.profile.metadata.raw_data or {}
                if raw:
                    is_open = raw.get("is_likely_to_engage", False) or raw.get("is_open_to_work", False)

                db.add(CandidateRecord(
                    linkedin_url=c.profile.basic_info.linkedin_url or "",
                    full_name=c.profile.basic_info.full_name or "Unknown",
                    headline=c.profile.basic_info.headline or "",
                    current_company=current_company,
                    current_title=current_title,
                    location=c.profile.basic_info.location or "",
                    fitment_score=c.fitment_score,
                    score_breakdown_json=json.dumps(c.score_breakdown.model_dump()),
                    score_reasoning=c.score_reasoning,
                    recommended_action=c.recommended_action,
                    email=c.profile.basic_info.email or "",
                    phone=c.profile.basic_info.phone or "",
                    is_open_to_work=is_open,
                    source="apollo",
                    raw_json=json.dumps(c.profile.model_dump(mode="json")),
                    role_name=request.spec.summary or "",
                ))
        await db.commit()

        return SearchResponse(
            candidates=scored,
            total_found=len(scored),
            data_source="apollo",
            search_query_used=request.spec.boolean_search_string,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

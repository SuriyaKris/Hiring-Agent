from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from loguru import logger
import json

from models.schemas import ApolloSearchRequest, SearchResponse, ScoredCandidate
from db import get_db, CandidateRecord
from providers.apollo_search import ApolloSearchProvider
from services.scoring_service import score_candidates_batch

router = APIRouter()


def extract_phone_number(person_data: dict) -> str | None:
    """Extract first valid mobile or sanitized phone number from Apollo person payload."""
    if not person_data or not isinstance(person_data, dict):
        return None
    phone_list = person_data.get("phone_numbers") or []
    if isinstance(phone_list, list) and phone_list:
        for p in phone_list:
            if isinstance(p, dict):
                num = p.get("sanitized_number") or p.get("raw_number")
                if num:
                    return str(num).strip()
            elif isinstance(p, str) and p.strip():
                return p.strip()
    direct_phone = person_data.get("sanitized_phone") or person_data.get("phone_number")
    if direct_phone:
        return str(direct_phone).strip()
    return None


@router.get("/apollo/webhook")
async def apollo_webhook_status():
    """Verify Apollo webhook listener status."""
    return {"status": "ok", "message": "Apollo webhook listener is active"}


@router.post("/apollo/webhook")
async def apollo_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Webhook listener for asynchronous Apollo enrichment updates (phone numbers & waterfall updates)."""
    try:
        data = await request.json()
    except Exception as e:
        logger.warning(f"[Apollo Webhook] Received invalid or non-JSON body: {e}")
        return {"status": "ignored", "reason": "invalid_json"}

    logger.info(f"[Apollo Webhook] Received payload: keys={list(data.keys())}")
    people = data.get("people") or (data.get("webhook_result", {}) or {}).get("people", [])
    if not isinstance(people, list):
        people = []

    updated_count = 0
    for person in people:
        if not isinstance(person, dict):
            continue
        person_id = person.get("id")
        phone = extract_phone_number(person)
        if not phone:
            continue

        conditions = []
        if person_id:
            conditions.append(CandidateRecord.raw_json.ilike(f'%"{person_id}"%'))
        if person.get("email"):
            conditions.append(CandidateRecord.email == person.get("email"))
        if person.get("linkedin_url"):
            conditions.append(CandidateRecord.linkedin_url == person.get("linkedin_url"))

        if not conditions:
            continue

        stmt = select(CandidateRecord).where(or_(*conditions))
        result = await db.execute(stmt)
        matched_records = result.scalars().all()

        for rec in matched_records:
            rec.phone = phone
            try:
                raw = json.loads(rec.raw_json or "{}")
                if "basic_info" in raw and isinstance(raw["basic_info"], dict):
                    raw["basic_info"]["phone"] = phone
                raw["phone_numbers"] = person.get("phone_numbers") or [{"sanitized_number": phone}]
                rec.raw_json = json.dumps(raw)
            except Exception:
                pass
            updated_count += 1

    if updated_count > 0:
        await db.commit()
        logger.info(f"[Apollo Webhook] Successfully updated phone numbers for {updated_count} candidate(s).")

    return {"status": "success", "updated_candidates": updated_count}


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

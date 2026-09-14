"""Router: POST /api/pipeline/run — stateful candidate intelligence workflow gateway."""

import json
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.schemas import PipelineRequest, PipelineResult, JDParseRequest, JDSearchSpec
from services.jd_service import extract_text_from_bytes, parse_jd
from agents.hiring_graph import run_pipeline
from db import get_db, CandidateRecord, SearchSessionRecord
from routers.user_auth import get_current_user
from config import get_settings

router = APIRouter()
settings = get_settings()


def format_error_detail(e: Exception) -> str:
    err_str = str(e)
    if "RateLimitError" in err_str or "429" in err_str:
        return "AI rate limit reached. Please wait a moment and try again."
    if "RetryError" in err_str:
        return "Operation timed out after retries. Please try again."
    return err_str


@router.post("/pipeline/parse", response_model=JDSearchSpec)
async def parse_job_description_criteria(request: JDParseRequest, current_user = Depends(get_current_user)):
    """Parse a JD to extract target criteria and keywords before running the pipeline search."""
    try:
        spec = await parse_jd(request.text, request.role_name)
        return spec
    except Exception as e:
        raise HTTPException(status_code=500, detail=format_error_detail(e))


@router.post("/pipeline/run", response_model=PipelineResult)
async def run_full_pipeline(
    request: PipelineRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Trigger LangGraph candidate intelligence workflow and log results/audit logs in database."""
    try:
        # Resolve JDSearchSpec
        spec = request.spec
        if not spec:
            spec = await parse_jd(request.jd_text, request.role_name)

        # Precompute fingerprint and role track ID before execution to pull exclusion sets
        from services.search_fingerprint import hash_spec, get_spec_embedding, find_or_create_role_track
        from services.deduplication_service import get_excluded_identities

        spec_hash = hash_spec(spec)
        spec_vector = get_spec_embedding(spec)
        track_id = await find_or_create_role_track(db, current_user.id, spec_hash, spec_vector)
        exclusion_identities = await get_excluded_identities(db, track_id)

        # Run pipeline
        result = await run_pipeline(
            jd_text=request.jd_text,
            role_name=request.role_name,
            recruiter_name=request.recruiter_name,
            company_name=request.company_name,
            max_candidates=request.max_candidates,
            spec=spec,
            exclusion_set=list(exclusion_identities),
            role_track_id=str(track_id),
        )

        db.add(SearchSessionRecord(
            session_id=result.run_id,
            role_name=request.role_name,
            jd_text=request.jd_text,
            parsed_spec_json=json.dumps(result.spec.model_dump()),
            apollo_filters_json=json.dumps({}),  # Handled inside search steps
            status="completed",
            audit_trail_json=json.dumps(["Pipeline completed successfully"]),
            user_id=current_user.id,
            role_track_id=track_id,
            spec_fingerprint_hash=spec_hash,
            spec_embedding=spec_vector,
        ))

        # Store candidate details in SQLite database
        for c in result.candidates:
            existing = await db.execute(
                select(CandidateRecord).where(CandidateRecord.linkedin_url == c.profile.basic_info.linkedin_url)
            )
            existing_row = existing.scalar_one_or_none()
            
            current_job = c.profile.experience[0] if c.profile.experience else None
            current_title = current_job.title if current_job else (c.profile.basic_info.headline or "")
            current_company = current_job.company_name if current_job else (c.profile.company.name if c.profile.company else "")

            is_open = False
            raw = c.profile.metadata.raw_data or {}
            if raw:
                is_open = raw.get("is_likely_to_engage", False) or raw.get("is_open_to_work", False)

            if existing_row:
                # Update existing candidate record details
                existing_row.full_name = c.profile.basic_info.full_name or existing_row.full_name
                existing_row.current_company = current_company
                existing_row.current_title = current_title
                existing_row.location = c.profile.basic_info.location or ""
                existing_row.fitment_score = c.fitment_score
                existing_row.score_breakdown_json = json.dumps(c.score_breakdown.model_dump())
                existing_row.score_reasoning = c.score_reasoning
                existing_row.recommended_action = c.recommended_action
                existing_row.email = c.profile.basic_info.email or ""
                existing_row.phone = c.profile.basic_info.phone or ""
                existing_row.is_open_to_work = is_open
                existing_row.raw_json = json.dumps(c.profile.model_dump(mode="json"))
                existing_row.role_name = request.role_name
                existing_row.search_session_id = result.run_id
            else:
                # Add new candidate record
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
                    source=result.data_source,
                    raw_json=json.dumps(c.profile.model_dump(mode="json")),
                    role_name=request.role_name,
                    apollo_person_id=c.profile.metadata.apollo_person_id,
                    apollo_organization_id=c.profile.metadata.apollo_organization_id,
                    search_session_id=result.run_id,
                ))
        await db.commit()

        return result
    except Exception as e:
        from loguru import logger
        logger.exception("Pipeline execution failed")
        raise HTTPException(status_code=500, detail=format_error_detail(e))


@router.post("/pipeline/upload-jd")
async def upload_job_description(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    """Upload a PDF, DOCX, or TXT job description file and extract its text content."""
    try:
        content = await file.read()
        extracted_text = await extract_text_from_bytes(content, file.filename)
        return {"jd_text": extracted_text, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {str(e)}")

"""Router: POST /api/candidates/enrich  ·  POST /api/candidates/rank  ·  GET /api/candidates  ·  GET /api/candidate/{id}"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from typing import List

from models.schemas import EnrichRequest, RankRequest, ScoredCandidate, VerdictUpdate
from db import get_db, CandidateRecord, SearchSessionRecord
from routers.user_auth import get_current_user
from schemas.candidate_profile import CandidateProfile
from providers.apollo_provider import ApolloProvider
from services.scoring_service import score_candidates_batch

router = APIRouter()


@router.post("/candidates/enrich", response_model=CandidateProfile)
async def enrich_candidate(request: EnrichRequest, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """Fetch verified contact details for a candidate using Apollo lookup."""
    try:
        # Load from DB or instantiate a blank candidate
        result = await db.execute(
            select(CandidateRecord)
            .join(SearchSessionRecord, CandidateRecord.search_session_id == SearchSessionRecord.session_id)
            .where(CandidateRecord.linkedin_url == request.candidate_linkedin_url)
            .where(SearchSessionRecord.user_id == current_user.id)
        )
        row = result.scalar_one_or_none()
        
        # Build profile wrapper
        from schemas.candidate_profile import BasicInfo, SchemaMetadata
        profile = None
        if row:
            try:
                profile_dict = json.loads(row.raw_json or "{}")
                if "basic_info" in profile_dict:
                    profile = CandidateProfile.model_validate(profile_dict)
                else:
                    profile = CandidateProfile(
                        basic_info=BasicInfo(
                            full_name=row.full_name or "Unknown",
                            linkedin_url=request.candidate_linkedin_url,
                            email=row.email or "",
                            phone=row.phone or "",
                        ),
                        metadata=SchemaMetadata(source="apollo", raw_data=profile_dict)
                    )
            except Exception:
                pass

        if not profile:
            profile = CandidateProfile(
                basic_info=BasicInfo(
                    full_name=row.full_name if row else "Unknown",
                    linkedin_url=request.candidate_linkedin_url,
                    email=row.email if row else "",
                    phone=row.phone if row else "",
                ),
                metadata=SchemaMetadata(source="apollo")
            )

        enricher = ApolloProvider()
        if await enricher.can_enrich(profile):
            profile = await enricher.enrich(profile)

        # Persist updated details if record exists in database
        if row:
            row.full_name = profile.basic_info.full_name or row.full_name
            row.email = profile.basic_info.email or ""
            row.phone = profile.basic_info.phone or ""
            row.raw_json = json.dumps(profile.model_dump(mode="json"))
            await db.commit()

        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/candidates/rank", response_model=List[ScoredCandidate])
async def rank_candidates(request: RankRequest, current_user = Depends(get_current_user)):
    """Compare candidate lists against specifications and return scored recommendations."""
    try:
        scored = await score_candidates_batch(request.candidates, request.spec, concurrency=3)
        # Sort descending
        scored.sort(key=lambda x: x.fitment_score, reverse=True)
        return scored
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_total_experience_years(employment_history) -> float:
    import datetime
    total_days = 0
    if not employment_history:
        return 0.0
    for job in employment_history:
        start_str = job.get("start_date")
        end_str = job.get("end_date")
        if not start_str:
            continue
        # Try various date formats
        start_dt = None
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                start_dt = datetime.datetime.strptime(start_str, fmt)
                break
            except Exception:
                continue
        if not start_dt:
            continue
        
        end_dt = None
        if end_str:
            for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
                try:
                    end_dt = datetime.datetime.strptime(end_str, fmt)
                    break
                except Exception:
                    continue
        if not end_dt:
            end_dt = datetime.datetime.utcnow()
            
        total_days += (end_dt - start_dt).days
    return round(total_days / 365.25, 1)


def _calculate_time_in_current_role(employment_history) -> str:
    import datetime
    if not employment_history:
        return "N/A"
    current_jobs = [job for job in employment_history if job.get("current")]
    if not current_jobs:
        # Fall back to first job if none marked current
        current_jobs = [employment_history[0]]
    job = current_jobs[0]
    start_str = job.get("start_date")
    if not start_str:
        return "N/A"
        
    start_dt = None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            start_dt = datetime.datetime.strptime(start_str, fmt)
            break
        except Exception:
            continue
    if not start_dt:
        return "N/A"
        
    days = (datetime.datetime.utcnow() - start_dt).days
    years = days // 365
    months = (days % 365) // 30
    if years > 0:
        return f"{years} yr{'s' if years > 1 else ''} {months} mo{'s' if months > 1 else ''}"
    return f"{months} month{'s' if months > 1 else ''}"


def _normalize_raw_json(raw_json_str: str, source: str) -> dict:
    """Parse raw_json string and normalize it to CandidateProfile dict format on the fly if needed."""
    try:
        data = json.loads(raw_json_str or "{}")
        if not data:
            return data
            
        # Case A: Old legacy raw JSON format (no basic_info key)
        if "basic_info" not in data:
            from services.candidate_enrichment import CandidateEnrichmentService
            import providers.apollo_mapper  # registers apollo normalizer
            enricher = CandidateEnrichmentService()
            profile = enricher.enrich(data, "apollo")
            data = profile.model_dump(mode="json")
            
        # Case B: New serialized format, but might have empty lists that can be populated from nested raw_data
        else:
            raw_data = data.get("metadata", {}).get("raw_data", {})
            if raw_data and (not data.get("experience") or not data.get("skills") or not data.get("education") or not data.get("summary") or not data.get("summary", {}).get("about")):
                try:
                    from services.candidate_enrichment import CandidateEnrichmentService
                    import providers.apollo_mapper
                    enricher = CandidateEnrichmentService()
                    profile = enricher.enrich(raw_data, "apollo")
                    profile_dict = profile.model_dump(mode="json")
                    
                    # Merge missing normalized fields
                    if not data.get("experience") and profile_dict.get("experience"):
                        data["experience"] = profile_dict["experience"]
                    if not data.get("skills") and profile_dict.get("skills"):
                        data["skills"] = profile_dict["skills"]
                    if not data.get("education") and profile_dict.get("education"):
                        data["education"] = profile_dict["education"]
                    if (not data.get("summary") or not data.get("summary", {}).get("about")) and profile_dict.get("summary"):
                        data["summary"] = profile_dict["summary"]
                except Exception:
                    pass
                
        # Compute and add custom fields for UI display
        raw_data = data.get("metadata", {}).get("raw_data", {})
        if raw_data:
            emp_history = raw_data.get("employment_history", [])
            total_exp = _calculate_total_experience_years(emp_history)
            time_current = _calculate_time_in_current_role(emp_history)
            
            data["persona"] = f"{raw_data.get('seniority', 'N/A').title()} / {data.get('basic_info', {}).get('headline', 'N/A')}"
            data["email_status"] = raw_data.get("email_status", "N/A")
            data["enrichment_type"] = source.upper()
            data["time_zone"] = raw_data.get("time_zone", "N/A")
            data["total_experience_years"] = f"{total_exp} years" if total_exp > 0 else "N/A"
            data["time_in_current_role"] = time_current
            data["territories"] = raw_data.get("formatted_address") or f"{raw_data.get('city', '')}, {raw_data.get('state', '')}, {raw_data.get('country', '')}".strip(", ") or "N/A"
            data["job_change_count"] = len(emp_history)
            
            # Last job change
            last_change = "N/A"
            if len(emp_history) > 1:
                current_jobs = [j for j in emp_history if j.get("current")]
                if current_jobs and current_jobs[0].get("start_date"):
                    last_change = current_jobs[0].get("start_date")
            data["last_job_change"] = last_change
            
            # Work URLs
            work_urls = []
            if data.get("basic_info", {}).get("linkedin_url"):
                work_urls.append({"name": "LinkedIn Profile", "url": data["basic_info"]["linkedin_url"]})
            if data.get("company", {}).get("website"):
                work_urls.append({"name": "Company Website", "url": data["company"]["website"]})
            data["work_urls"] = work_urls
            
            # Map engineered features & score for UI display
            data["engineered_features"] = raw_data.get("engineered_features")
            data["engineered_fitment_score"] = raw_data.get("engineered_fitment_score")
            
        return data
    except Exception:
        return data
    
    
@router.get("/candidates")
async def get_candidates(role_name: str | None = None, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """Return stored candidates sorted by score."""
    sess_res = await db.execute(
        select(SearchSessionRecord.session_id).where(SearchSessionRecord.user_id == current_user.id)
    )
    user_session_ids = [r[0] for r in sess_res.all()]

    stmt = select(CandidateRecord).where(CandidateRecord.source != "mock")

    if user_session_ids:
        stmt = stmt.where(CandidateRecord.search_session_id.in_(user_session_ids))

    if role_name and role_name.strip() and role_name.strip().lower() != "all":
        stmt = stmt.where(CandidateRecord.role_name == role_name.strip())

    stmt = stmt.order_by(CandidateRecord.fitment_score.desc())
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "linkedin_url": r.linkedin_url,
            "full_name": r.full_name,
            "headline": r.headline,
            "current_company": r.current_company,
            "current_title": r.current_title,
            "location": r.location,
            "fitment_score": r.fitment_score,
            "score_breakdown": json.loads(r.score_breakdown_json or "{}"),
            "score_reasoning": r.score_reasoning,
            "recommended_action": r.recommended_action,
            "email": r.email,
            "phone": r.phone,
            "is_open_to_work": r.is_open_to_work,
            "source": r.source,
            "recruiter_verdict": r.recruiter_verdict,
            "role_name": r.role_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "profile_details": _normalize_raw_json(r.raw_json, r.source),
        }
        for r in rows
    ]


@router.get("/candidate/{candidate_id}")
async def get_candidate_details(candidate_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """Fetch details of a single candidate."""
    result = await db.execute(
        select(CandidateRecord)
        .join(SearchSessionRecord, CandidateRecord.search_session_id == SearchSessionRecord.session_id)
        .where(CandidateRecord.id == candidate_id)
        .where(SearchSessionRecord.user_id == current_user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return {
        "id": row.id,
        "linkedin_url": row.linkedin_url,
        "full_name": row.full_name,
        "headline": row.headline,
        "current_company": row.current_company,
        "current_title": row.current_title,
        "location": row.location,
        "fitment_score": row.fitment_score,
        "score_breakdown": json.loads(row.score_breakdown_json or "{}"),
        "score_reasoning": row.score_reasoning,
        "email": row.email,
        "phone": row.phone,
        "source": row.source,
        "raw_details": _normalize_raw_json(row.raw_json, row.source)
    }


@router.patch("/candidates/verdict")
async def update_verdict(body: VerdictUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """Recruiter marks shortlist / reject / maybe."""
    result = await db.execute(
        select(CandidateRecord)
        .join(SearchSessionRecord, CandidateRecord.search_session_id == SearchSessionRecord.session_id)
        .where(CandidateRecord.linkedin_url == body.candidate_linkedin_url)
        .where(SearchSessionRecord.user_id == current_user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    row.recruiter_verdict = body.verdict
    await db.commit()
    return {"status": "updated", "verdict": body.verdict}


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(candidate_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """Remove a candidate from the pipeline."""
    result = await db.execute(
        select(CandidateRecord)
        .join(SearchSessionRecord, CandidateRecord.search_session_id == SearchSessionRecord.session_id)
        .where(CandidateRecord.id == candidate_id)
        .where(SearchSessionRecord.user_id == current_user.id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Candidate not found")
    await db.delete(row)
    await db.commit()
    return {"status": "deleted"}


@router.get("/candidates/export")
async def export_candidates(db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    """Export all candidates to an Excel sheet."""
    try:
        from fastapi.responses import StreamingResponse
        import io
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        # Fetch candidates ordered by fitment_score desc
        result = await db.execute(
            select(CandidateRecord)
            .join(SearchSessionRecord, CandidateRecord.search_session_id == SearchSessionRecord.session_id)
            .where(SearchSessionRecord.user_id == current_user.id)
            .order_by(CandidateRecord.fitment_score.desc())
        )
        rows = result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = "Candidates"

        # Headers
        headers = [
            "Full Name", "Fitment Score", "Current Title", "Current Company", "Location",
            "Total Experience", "Email", "LinkedIn URL", "Recommended Action",
            "Title Match Score", "Skills Match Score", "CRM Background Score", "Job Stability Score",
            "Geography Score", "Bonuses Score", "Match Reasoning"
        ]
        ws.append(headers)

        # Style header row
        header_font = Font(name="Arial", size=11, bold=True, color="000000")
        header_fill = PatternFill(start_color="EAEAEA", end_color="EAEAEA", fill_type="solid")
        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill

        # Data rows
        for r in rows:
            score_breakdown = json.loads(r.score_breakdown_json or "{}")
            profile_details = _normalize_raw_json(r.raw_json, r.source)
            total_exp = profile_details.get("total_experience_years", "N/A")

            row_data = [
                r.full_name or "Unknown",
                round(r.fitment_score, 1) if r.fitment_score is not None else 0.0,
                r.current_title or "",
                r.current_company or "",
                r.location or "",
                total_exp,
                r.email or "",
                r.linkedin_url or "",
                r.recommended_action or "",
                score_breakdown.get("title_match", 0),
                score_breakdown.get("skills_match", 0),
                score_breakdown.get("crm_background", 0),
                score_breakdown.get("job_stability", 0),
                score_breakdown.get("geography", 0),
                score_breakdown.get("bonuses", 0),
                r.score_reasoning or ""
            ]
            ws.append(row_data)

        # Auto-fit columns
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    # Clip columns that are too long (like match reasoning) to a practical max width
                    max_len = min(len(val_str), 50)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

        # Save workbook to memory buffer
        out = io.BytesIO()
        wb.save(out)
        out.seek(0)

        headers_resp = {
            'Content-Disposition': 'attachment; filename="candidates_export.xlsx"'
        }
        return StreamingResponse(
            out,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers_resp
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

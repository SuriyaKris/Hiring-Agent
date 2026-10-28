"""Router: POST /api/candidates/enrich  ·  POST /api/candidates/rank  ·  GET /api/candidates  ·  GET /api/candidate/{id}"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import asyncio
import httpx
from typing import List

from config import get_settings
from models.schemas import EnrichRequest, BulkEnrichPhoneRequest, RankRequest, ScoredCandidate, VerdictUpdate
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
        rows = result.scalars().all()
        row = rows[0] if rows else None
        
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

        # Persist updated details across all matching records in database
        if rows:
            for r in rows:
                r.full_name = profile.basic_info.full_name or r.full_name
                r.email = profile.basic_info.email or r.email or ""
                r.personal_email = getattr(profile.basic_info, "personal_email", None) or r.personal_email
                r.corporate_email = getattr(profile.basic_info, "corporate_email", None) or r.corporate_email
                r.phone = profile.basic_info.phone or r.phone or ""
                if profile.experience and len(profile.experience) > 0:
                    r.current_title = profile.experience[0].title or r.current_title
                    r.current_company = profile.experience[0].company_name or r.current_company
                elif profile.basic_info.headline:
                    r.current_title = profile.basic_info.headline or r.current_title
                if profile.basic_info.location:
                    r.location = profile.basic_info.location
                if profile.basic_info.headline:
                    r.headline = profile.basic_info.headline
                r.raw_json = json.dumps(profile.model_dump(mode="json"))
            await db.commit()

        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/candidates/bulk-enrich-phone")
@router.post("/candidates/bulk-enrich-contact")
async def bulk_enrich_phone(
    request: BulkEnrichPhoneRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Enrich contact details, personal emails, and mobile numbers for shortlisted candidates using Apollo."""
    try:
        stmt = (
            select(CandidateRecord)
            .join(SearchSessionRecord, CandidateRecord.search_session_id == SearchSessionRecord.session_id)
            .where(SearchSessionRecord.user_id == current_user.id)
        )
        if request.session_id and request.session_id.strip() and request.session_id.strip().lower() != "all":
            stmt = stmt.where(CandidateRecord.search_session_id == request.session_id.strip())
        if request.target_verdict and request.target_verdict.strip() and request.target_verdict.strip().lower() != "all":
            stmt = stmt.where(CandidateRecord.recruiter_verdict == request.target_verdict.strip().lower())

        result = await db.execute(stmt)
        candidates_to_enrich = result.scalars().all()

        from schemas.candidate_profile import BasicInfo, SchemaMetadata
        provider = ApolloProvider()
        settings = get_settings()

        sem = asyncio.Semaphore(5)

        async def _enrich_single(c):
            try:
                profile_dict = json.loads(c.raw_json or "{}")
                if "basic_info" in profile_dict:
                    profile = CandidateProfile.model_validate(profile_dict)
                else:
                    profile = CandidateProfile(
                        basic_info=BasicInfo(
                            full_name=c.full_name or "Unknown",
                            linkedin_url=c.linkedin_url or "",
                            email=c.email or "",
                            phone=c.phone or "",
                        ),
                        metadata=SchemaMetadata(source="apollo", raw_data=profile_dict)
                    )

                if await provider.can_enrich(profile):
                    async with sem:
                        # Step 1: Immediate match for email/details; phone reveal is dispatched with webhook
                        enriched = await provider.enrich(profile, poll_phone=False)
                        return c, enriched
            except Exception:
                pass
            return c, None

        tasks = [_enrich_single(c) for c in candidates_to_enrich]
        matched_pairs = await asyncio.gather(*tasks)

        # Step 2: For candidates without a phone, gather their Apollo phone request_id and poll concurrently
        pending_phone_candidates = []
        for c, enriched in matched_pairs:
            if enriched and not getattr(enriched.basic_info, "phone", None):
                raw = enriched.metadata.raw_data or {}
                req_id = raw.get("apollo_phone_request_id")
                if req_id:
                    pending_phone_candidates.append((c, enriched, req_id))

        if pending_phone_candidates and settings.apollo_api_key:
            # Wait 7 seconds for Apollo telecom carrier waterfall to complete
            await asyncio.sleep(7.0)
            headers = {
                "Content-Type": "application/json",
                "X-Api-Key": settings.apollo_api_key,
            }
            async with httpx.AsyncClient(timeout=15) as client:
                async def _poll_req(c, enriched, req_id):
                    try:
                        resp = await client.get(f"https://api.apollo.io/v1/webhook_result/{req_id}", headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            wr = data.get("webhook_result") or {}
                            people = wr.get("people") or data.get("people") or []
                            if people and isinstance(people, list):
                                phones = people[0].get("phone_numbers") or []
                                if phones:
                                    phone_val = phones[0].get("sanitized_number") or phones[0].get("raw_number")
                                    if phone_val:
                                        enriched.basic_info.phone = str(phone_val).strip()
                    except Exception:
                        pass

                poll_tasks = [_poll_req(c, enriched, req_id) for c, enriched, req_id in pending_phone_candidates]
                await asyncio.gather(*poll_tasks)

        # Step 3: Persist all updated profiles to DB
        updated_candidates = []
        personal_emails_found = 0
        phones_found = 0

        for c, enriched in matched_pairs:
            if not enriched:
                continue
            c.full_name = enriched.basic_info.full_name or c.full_name
            c.email = enriched.basic_info.email or c.email or ""
            c.personal_email = getattr(enriched.basic_info, "personal_email", None) or c.personal_email
            c.corporate_email = getattr(enriched.basic_info, "corporate_email", None) or c.corporate_email
            c.phone = enriched.basic_info.phone or c.phone or ""
            if enriched.experience and len(enriched.experience) > 0:
                c.current_title = enriched.experience[0].title or c.current_title
                c.current_company = enriched.experience[0].company_name or c.current_company
            elif enriched.basic_info.headline:
                c.current_title = enriched.basic_info.headline or c.current_title
            if enriched.basic_info.location:
                c.location = enriched.basic_info.location
            if enriched.basic_info.headline:
                c.headline = enriched.basic_info.headline
            c.raw_json = json.dumps(enriched.model_dump(mode="json"))

            if c.personal_email:
                personal_emails_found += 1
            if c.phone:
                phones_found += 1

            updated_candidates.append({
                "linkedin_url": c.linkedin_url,
                "phone": c.phone,
                "email": c.email,
                "personal_email": c.personal_email,
                "corporate_email": c.corporate_email,
                "full_name": c.full_name
            })

        await db.commit()
        return {
            "status": "success",
            "total_candidates": len(candidates_to_enrich),
            "personal_emails_found": personal_emails_found,
            "phones_found": phones_found,
            "updated": updated_candidates
        }
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
        raw_data = data.get("metadata", {}).get("raw_data", {}) or data
        emp_history = raw_data.get("employment_history", []) or data.get("experience", [])
        total_exp = _calculate_total_experience_years(emp_history)
        time_current = _calculate_time_in_current_role(emp_history)
        
        headline_val = data.get("basic_info", {}).get("headline") or raw_data.get("headline") or raw_data.get("title") or ""
        seniority_val = raw_data.get("seniority") or ""
        clean_headline = headline_val if headline_val and str(headline_val).lower() not in ("none", "null", "n/a") else "HR Executive"
        if seniority_val and str(seniority_val).lower() not in ("n/a", "none", "unknown", "null"):
            data["persona"] = f"{seniority_val.title()} · {clean_headline}"
        else:
            data["persona"] = clean_headline
            
        email_val = data.get("basic_info", {}).get("email") or raw_data.get("email") or ""
        personal_email_val = data.get("basic_info", {}).get("personal_email")
        if not personal_email_val:
            raw_p = raw_data.get("personal_emails") or []
            if isinstance(raw_p, list) and raw_p:
                personal_email_val = raw_p[0]
            elif raw_data.get("personal_email"):
                personal_email_val = raw_data.get("personal_email")

        corporate_email_val = data.get("basic_info", {}).get("corporate_email") or raw_data.get("email") or ""

        PERSONAL_DOMAINS = {
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
            "me.com", "aol.com", "proton.me", "protonmail.com", "zoho.com",
            "mail.com", "yandex.com", "gmx.com", "live.com", "msn.com"
        }
        is_personal = False
        if personal_email_val:
            is_personal = True
            email_val = personal_email_val
        elif email_val and any(email_val.lower().endswith("@" + d) for d in PERSONAL_DOMAINS):
            is_personal = True
            personal_email_val = email_val

        data["personal_email"] = personal_email_val
        data["corporate_email"] = corporate_email_val if corporate_email_val != personal_email_val else None
        data["email"] = email_val
        data["email_type"] = "personal" if is_personal else ("work" if email_val else "none")

        email_status_val = raw_data.get("email_status")
        if email_status_val and str(email_status_val).lower() not in ("none", "null", "", "n/a"):
            data["email_status"] = email_status_val
        elif email_val:
            data["email_status"] = "verified"
        else:
            data["email_status"] = "N/A"
            
        data["enrichment_type"] = source.upper()
        
        # Time zone
        tz = raw_data.get("time_zone")
        if not tz or str(tz).lower() in ("n/a", "none", "", "null"):
            loc_str = str(data.get("basic_info", {}).get("location") or raw_data.get("country") or "").lower()
            if "india" in loc_str:
                tz = "Asia/Kolkata (IST)"
            elif "us" in loc_str or "united states" in loc_str:
                tz = "America/New_York (EST)"
            else:
                tz = "N/A"
        data["time_zone"] = tz
        
        # Total experience
        exp_years_raw = raw_data.get("estimated_num_years_experience") or raw_data.get("total_experience_years")
        if total_exp > 0:
            data["total_experience_years"] = f"{total_exp} years"
        elif exp_years_raw:
            data["total_experience_years"] = f"{exp_years_raw} years"
        else:
            data["total_experience_years"] = "N/A"
            
        data["time_in_current_role"] = time_current
        
        # Territories
        city = raw_data.get("city") or ""
        state = raw_data.get("state") or ""
        country = raw_data.get("country") or ""
        parts = [p.strip() for p in [city, state, country] if p and str(p).lower() not in ("none", "null", "n/a", "")]
        territory_val = raw_data.get("formatted_address") or (", ".join(parts) if parts else None) or data.get("basic_info", {}).get("location") or "N/A"
        data["territories"] = territory_val
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
        
        # Phone
        phone_val = data.get("basic_info", {}).get("phone") or raw_data.get("phone") or raw_data.get("sanitized_phone") or ""
        if not phone_val and raw_data.get("phone_numbers"):
            p_list = raw_data["phone_numbers"]
            if isinstance(p_list, list) and len(p_list) > 0:
                first = p_list[0]
                phone_val = first.get("sanitized_number") or first.get("raw_number") or ""
        data["phone"] = phone_val
        
        # Map engineered features & score for UI display
        data["engineered_features"] = raw_data.get("engineered_features")
        data["engineered_fitment_score"] = raw_data.get("engineered_fitment_score")
        
        return data
    except Exception:
        return data
    
    
@router.get("/candidates")
async def get_candidates(
    role_name: str | None = None,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Return stored candidates sorted by score, optionally filtered by session_id or role_name."""
    sess_res = await db.execute(
        select(SearchSessionRecord.session_id).where(SearchSessionRecord.user_id == current_user.id)
    )
    user_session_ids = [r[0] for r in sess_res.all()]

    stmt = select(CandidateRecord).where(CandidateRecord.source != "mock")

    if session_id and session_id.strip() and session_id.strip().lower() != "all":
        # Specific search session requested
        stmt = stmt.where(CandidateRecord.search_session_id == session_id.strip())
    elif user_session_ids:
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
            "personal_email": r.personal_email,
            "corporate_email": r.corporate_email,
            "email_type": "personal" if (r.personal_email and r.email == r.personal_email) else ("work" if r.email else "none"),
            "phone": r.phone,
            "is_open_to_work": r.is_open_to_work,
            "source": r.source,
            "recruiter_verdict": r.recruiter_verdict,
            "role_name": r.role_name,
            "search_session_id": r.search_session_id,
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
        "personal_email": row.personal_email,
        "corporate_email": row.corporate_email,
        "email_type": "personal" if (row.personal_email and row.email == row.personal_email) else ("work" if row.email else "none"),
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
    rows = result.scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Candidate not found")
    for r in rows:
        r.recruiter_verdict = body.verdict
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
async def export_candidates(
    role_name: str | None = None,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Export candidates to an Excel sheet, optionally filtered by session_id or role_name."""
    try:
        from fastapi.responses import StreamingResponse
        import io
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        # Fetch candidates ordered by fitment_score desc
        stmt = (
            select(CandidateRecord)
            .join(SearchSessionRecord, CandidateRecord.search_session_id == SearchSessionRecord.session_id)
            .where(SearchSessionRecord.user_id == current_user.id)
        )
        if session_id and session_id.strip() and session_id.strip().lower() != "all":
            stmt = stmt.where(CandidateRecord.search_session_id == session_id.strip())
        if role_name and role_name.strip() and role_name.strip().lower() != "all":
            stmt = stmt.where(CandidateRecord.role_name == role_name.strip())

        stmt = stmt.order_by(CandidateRecord.fitment_score.desc())
        result = await db.execute(stmt)
        rows = result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = "Candidates"

        # Headers
        headers = [
            "Full Name", "Fitment Score", "Current Title", "Current Company", "Location",
            "Total Experience", "Email (Primary)", "Email Type", "Personal Email", "Corporate Email", "Phone",
            "LinkedIn URL", "Recommended Action",
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
            email_type = "Personal" if (r.personal_email and r.email == r.personal_email) else ("Work" if r.email else "N/A")

            row_data = [
                r.full_name or "Unknown",
                round(r.fitment_score, 1) if r.fitment_score is not None else 0.0,
                r.current_title or "",
                r.current_company or "",
                r.location or "",
                total_exp,
                r.email or "",
                email_type,
                r.personal_email or "",
                r.corporate_email or "",
                r.phone or "",
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

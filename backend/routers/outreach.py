"""Router: POST /api/outreach  ·  POST /api/outreach/save  ·  GET /api/outreach/history"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.schemas import OutreachRequest, OutreachDraft, OutreachSaveRequest, OutreachReplyUpdate
from services.outreach_service import generate_outreach
from db import get_db, OutreachRecord

router = APIRouter()


@router.post("/outreach/generate", response_model=OutreachDraft)
async def generate_outreach_endpoint(request: OutreachRequest):
    """Generate personalised message pack for one candidate."""
    try:
        return await generate_outreach(
            request.candidate,
            request.role_name,
            request.company_name,
            request.recruiter_name,
            request.tone,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outreach/save")
async def save_outreach(body: OutreachSaveRequest, db: AsyncSession = Depends(get_db)):
    """Record that a message was sent (recruiter confirms after manual send)."""
    db.add(OutreachRecord(
        candidate_linkedin_url=body.candidate_linkedin_url,
        candidate_name=body.candidate_name,
        role_name=body.role_name,
        channel=body.channel,
        message_sent=body.message_sent,
    ))
    await db.commit()
    return {"status": "saved"}


@router.get("/outreach/history")
async def outreach_history(db: AsyncSession = Depends(get_db)):
    """Full outreach history for the pipeline tracker."""
    result = await db.execute(select(OutreachRecord).order_by(OutreachRecord.sent_at.desc()))
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "candidate_name": r.candidate_name,
            "role_name": r.role_name,
            "channel": r.channel,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "replied": r.replied,
            "status": r.status,
            "recruiter_notes": r.recruiter_notes,
        }
        for r in rows
    ]


@router.patch("/outreach/{record_id}/status")
async def update_outreach_status(record_id: int, body: OutreachReplyUpdate, db: AsyncSession = Depends(get_db)):
    """Update outreach status (replied, interested, no_response, etc)."""
    result = await db.execute(select(OutreachRecord).where(OutreachRecord.id == record_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    row.status = body.status
    row.replied = body.status in ("replied", "interested")
    row.recruiter_notes = body.notes
    await db.commit()
    return {"status": "updated"}

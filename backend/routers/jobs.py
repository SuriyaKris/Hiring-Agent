"""Router: POST /api/jobs/analyze — parses Job Description specifications."""

from fastapi import APIRouter, HTTPException, Depends
from models.schemas import JDParseRequest, JDSearchSpec
from services.jd_service import parse_jd
from routers.user_auth import get_current_user

router = APIRouter()


@router.post("/jobs/analyze", response_model=JDSearchSpec)
async def analyze_job(request: JDParseRequest, current_user = Depends(get_current_user)):
    """Analyze and extract structured query filters from raw Job Description text."""
    try:
        spec = await parse_jd(request.text, request.role_name)
        return spec
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

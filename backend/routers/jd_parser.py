"""Router: POST /api/parse-jd and POST /api/parse-jd-file"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from models.schemas import JDParseRequest
from services.jd_service import parse_jd, extract_text_from_bytes, build_boolean_string

router = APIRouter()


@router.post("/parse-jd")
async def parse_jd_text(request: JDParseRequest):
    try:
        spec = await parse_jd(request.text, request.role_name)
        return {
            "spec": spec.model_dump(),
            "search_strings": build_boolean_string(spec),
            "data_source": "text",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-jd-file")
async def parse_jd_file(file: UploadFile = File(...), role_name: str = Form(...)):
    try:
        content = await file.read()
        text = await extract_text_from_bytes(content, file.filename or "jd.txt")
        spec = await parse_jd(text, role_name)
        return {
            "extracted_preview": text[:400] + "..." if len(text) > 400 else text,
            "spec": spec.model_dump(),
            "search_strings": build_boolean_string(spec),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""Router: POST /api/parse-jd and POST /api/parse-jd-file"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from models.schemas import JDParseRequest
from services.jd_service import parse_jd, extract_text_from_bytes, build_boolean_string

router = APIRouter()


def format_error_detail(e: Exception) -> str:
    err_str = str(e)
    if "RateLimitError" in err_str or "429" in err_str:
        return "AI rate limit reached. Please wait a moment and try again."
    if "RetryError" in err_str:
        return "Operation timed out after retries. Please try again."
    return err_str


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
        raise HTTPException(status_code=500, detail=format_error_detail(e))


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
        raise HTTPException(status_code=500, detail=format_error_detail(e))

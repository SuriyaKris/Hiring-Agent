"""
JD Service — parses job descriptions into structured search specs.
Uses LLM abstraction (Groq free / OpenAI paid).
Cost: ~$0.001–0.003 per parse depending on provider.
"""

from pathlib import Path
from models.schemas import JDSearchSpec
from services.llm_service import complete_json
from loguru import logger

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "jd_parser.txt"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()
def merge_role_name_into_titles(role_name: str | None, parsed_titles: list[str]) -> list[str]:
    if not role_name:
        return parsed_titles
    role_name_clean = role_name.strip()
    existing_lower = {t.lower().strip() for t in parsed_titles}
    if role_name_clean.lower() not in existing_lower:
        return [role_name_clean] + parsed_titles
    return parsed_titles



async def parse_jd(jd_text: str, role_name: str) -> JDSearchSpec:
    """
    Parse a JD into a structured search spec.
    Uses fast model (gpt-4o-mini or llama-3.1-8b-instant).
    """
    system_prompt = _load_prompt()
    user_message = f"Role name: {role_name}\n\nJob Description:\n{jd_text}\n\nReturn the search specification JSON now."

    logger.info(f"Parsing JD for role: {role_name}")
    try:
        data = await complete_json(
            system_prompt=system_prompt,
            user_message=user_message,
            use_smart_model=False,   # fast/cheap model is sufficient
            temperature=0.1,
            max_tokens=1500,
        )
    except Exception as e:
        logger.warning(f"LLM parsing failed ({e}). Constructing heuristic search spec fallback.")
        from nlp.keyword_extractor import extract_backup_titles, extract_backup_persona, extract_backup_territory
        fallback_titles = extract_backup_titles(jd_text) or ([role_name.strip()] if role_name else ["Software Engineer"])
        fallback_persona = extract_backup_persona(jd_text)
        fallback_territory = extract_backup_territory(jd_text)
        fallback_geo = [fallback_territory] if fallback_territory else []
        
        # Simple extraction of prominent capitalized terms or common tech skills
        data = {
            "primary_titles": fallback_titles,
            "related_titles": [f"Senior {t}" for t in fallback_titles[:2]] + [f"Lead {t}" for t in fallback_titles[:1]],
            "required_skills": fallback_titles[:3],
            "nice_to_have_skills": [],
            "target_companies": [],
            "excluded_companies": ["Staffing", "Recruiting Agency"],
            "seniority_levels": ["Mid-Level", "Senior"],
            "geo_keywords": fallback_geo,
            "min_experience_years": 2,
            "boolean_search_string": f'("{" OR ".join(fallback_titles[:3])}")' + (f' AND ("{fallback_territory}")' if fallback_territory else ""),
            "summary": f"Targeting {role_name or (fallback_titles[0] if fallback_titles else 'candidates')} with relevant experience.",
            "target_titles": fallback_titles,
            "target_persona": fallback_persona,
            "target_territory": fallback_territory,
            "jd_requirements_text": jd_text,
        }
    
    # Run fallbacks if critical fields are missing
    from nlp.keyword_extractor import extract_backup_titles, extract_backup_persona, extract_backup_territory
    
    if not data.get("target_titles"):
        data["target_titles"] = extract_backup_titles(jd_text)
        if not data["target_titles"]:
            data["target_titles"] = data.get("primary_titles", []) + data.get("related_titles", [])
            
    if not data.get("target_persona"):
        data["target_persona"] = extract_backup_persona(jd_text)
        
    if "target_territory" not in data or data.get("target_territory") is None:
        data["target_territory"] = extract_backup_territory(jd_text)

    if not isinstance(data.get("geo_keywords"), list):
        data["geo_keywords"] = [data["geo_keywords"]] if data.get("geo_keywords") else []

    if "jd_requirements_text" not in data or not data["jd_requirements_text"]:
        data["jd_requirements_text"] = jd_text

    # Store role_name in spec dictionary
    data["role_name"] = role_name

    # Merge role_name into primary and target title lists
    data["primary_titles"] = merge_role_name_into_titles(role_name, data.get("primary_titles", []))
    data["target_titles"] = merge_role_name_into_titles(role_name, data.get("target_titles", []))

    return JDSearchSpec(**data)


async def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from PDF, DOCX, or plain text files."""
    ext = filename.lower().rsplit(".", 1)[-1]

    if ext == "pdf":
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    elif ext in ("docx", "doc"):
        import io
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    else:
        return file_bytes.decode("utf-8", errors="ignore")


def build_apollo_query(spec: JDSearchSpec) -> dict:
    """
    Build the Apollo.io API query payload from the parsed spec.
    Used by apollo_service.apollo_search().
    """
    return {
        "person_titles": spec.primary_titles + spec.related_titles,
        "person_locations": spec.geo_keywords,
        "q_keywords": " ".join(spec.required_skills[:5]),
        "person_seniorities": [s.lower() for s in spec.seniority_levels] if spec.seniority_levels else ["senior", "mid"],
    }


def build_boolean_string(spec: JDSearchSpec) -> dict:
    """Build LinkedIn-compatible Boolean search strings from spec."""
    titles = " OR ".join(f'"{t}"' for t in spec.primary_titles[:4])
    related = " OR ".join(f'"{t}"' for t in spec.related_titles[:3])
    geo = " OR ".join(f'"{g}"' for g in spec.geo_keywords[:4])
    skills = " OR ".join(f'"{s}"' for s in spec.required_skills[:3])

    return {
        "primary": f'({titles}) AND ({geo}) AND ({skills})',
        "broad": f'({titles} OR {related}) AND ({geo})',
        "instructions": (
            "1. Open LinkedIn Sales Navigator or free LinkedIn search\n"
            "2. Paste 'primary' string into keyword search\n"
            "3. Apply Geography filter from spec.geo_keywords\n"
            "4. Copy profile URLs and paste into the agent's search tab"
        ),
    }

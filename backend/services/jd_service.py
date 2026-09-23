"""
JD Service — parses job descriptions into structured search specs.
Uses LLM abstraction (Groq free / OpenAI / Gemini).
Cost: ~$0.001–0.003 per parse depending on provider.
"""

from pathlib import Path
from models.schemas import JDSearchSpec
from services.llm_service import complete_json
from loguru import logger
from nlp.keyword_extractor import (
    extract_backup_titles,
    extract_backup_skills,
    extract_backup_technologies,
    extract_backup_persona,
    extract_backup_territory,
    extract_backup_geo_keywords,
)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "jd_parser.txt"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def merge_role_name_into_titles(role_name: str | None, parsed_titles: list[str]) -> list[str]:
    """Merge role_name only if meaningful and not already present."""
    if not role_name or not role_name.strip():
        return parsed_titles
    role_name_clean = role_name.strip()
    # Don't add generic placeholders
    if role_name_clean.lower() in ("default", "untitled", "role", "job", "position"):
        return parsed_titles
    existing_lower = {t.lower().strip() for t in parsed_titles}
    if role_name_clean.lower() not in existing_lower:
        if parsed_titles:
            return parsed_titles + [role_name_clean]
        return [role_name_clean]
    return parsed_titles


async def parse_jd(jd_text: str, role_name: str = "") -> JDSearchSpec:
    """
    Parse a JD into a structured search spec.
    Extracts canonical titles, deep skills, and accurate city/country locations.
    """
    system_prompt = _load_prompt()
    role_hint = f"Explicit Role Name provided by recruiter: '{role_name.strip()}'\n\n" if (role_name and role_name.strip()) else ""
    user_message = f"{role_hint}Job Description:\n{jd_text}\n\nReturn the search specification JSON now."

    logger.info(f"Parsing JD for role: '{role_name or 'Auto-Detect'}'")
    try:
        data = await complete_json(
            system_prompt=system_prompt,
            user_message=user_message,
            use_smart_model=False,
            temperature=0.1,
            max_tokens=2500,
        )
    except Exception as e:
        logger.warning(f"LLM parsing failed ({e}). Constructing heuristic search spec fallback.")
        fallback_titles = extract_backup_titles(jd_text, role_name=role_name) or ([role_name.strip()] if role_name and role_name.strip() else ["Software Engineer"])
        fallback_skills = extract_backup_skills(jd_text)
        fallback_tech = extract_backup_technologies(jd_text)
        fallback_persona = extract_backup_persona(jd_text)
        fallback_territory = extract_backup_territory(jd_text)
        fallback_geo = extract_backup_geo_keywords(jd_text)
        if not fallback_geo and fallback_territory:
            fallback_geo = [fallback_territory]

        data = {
            "primary_titles": fallback_titles,
            "related_titles": [f"Senior {t}" for t in fallback_titles[:2]] + [f"Lead {t}" for t in fallback_titles[:1]],
            "required_skills": fallback_skills if fallback_skills else ([f"{t} Domain Expertise" for t in fallback_titles[:2]] if fallback_titles else ["Relevant Experience"]),
            "nice_to_have_skills": [],
            "target_companies": [],
            "excluded_companies": ["Staffing", "Recruiting Agency", "Temp Agency"],
            "seniority_levels": ["Mid-Level", "Senior"],
            "geo_keywords": fallback_geo,
            "min_experience_years": 2,
            "boolean_search_string": f'("{" OR ".join(fallback_titles[:3])}")' + (f' AND ("{fallback_territory}")' if fallback_territory else ""),
            "summary": f"Targeting {fallback_titles[0] if fallback_titles else 'candidates'} with relevant experience.",
            "target_titles": fallback_titles,
            "target_persona": fallback_persona,
            "target_territory": fallback_territory,
            "jd_requirements_text": jd_text,
            "currently_using_technology_uids": fallback_tech,
        }

    # Ensure critical fields are properly populated
    if not data.get("primary_titles"):
        data["primary_titles"] = extract_backup_titles(jd_text, role_name=role_name) or ([role_name.strip()] if role_name and role_name.strip() else ["Software Engineer"])

    # If role_name was explicitly passed, ensure it is in primary_titles and target_titles
    if role_name and role_name.strip():
        data["primary_titles"] = merge_role_name_into_titles(role_name, data.get("primary_titles", []))

    if not data.get("target_titles"):
        data["target_titles"] = list(data.get("primary_titles", []))
    elif role_name and role_name.strip() and role_name.strip().lower() not in [t.lower() for t in data["target_titles"]]:
        data["target_titles"] = [role_name.strip()] + data["target_titles"]

    if not data.get("required_skills"):
        data["required_skills"] = extract_backup_skills(jd_text)

    if not data.get("target_persona"):
        data["target_persona"] = extract_backup_persona(jd_text)

    if not data.get("target_territory"):
        data["target_territory"] = extract_backup_territory(jd_text)

    if not data.get("geo_keywords"):
        data["geo_keywords"] = extract_backup_geo_keywords(jd_text)
    elif isinstance(data["geo_keywords"], str):
        data["geo_keywords"] = [data["geo_keywords"]]

    if "jd_requirements_text" not in data or not data["jd_requirements_text"]:
        data["jd_requirements_text"] = jd_text

    # Canonical role name resolution (prefer user's explicit role_name)
    resolved_role = (
        (role_name.strip() if role_name and role_name.strip() else None)
        or data.get("primary_titles", [None])[0]
        or "Software Engineer"
    )
    data["role_name"] = resolved_role

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
        "primary": f'({titles}) AND ({geo}) AND ({skills})' if geo else f'({titles}) AND ({skills})',
        "broad": f'({titles} OR {related}) AND ({geo})' if geo else f'({titles} OR {related})',
        "instructions": (
            "1. Open LinkedIn Sales Navigator or free LinkedIn search\n"
            "2. Paste 'primary' string into keyword search\n"
            "3. Apply Geography filter from spec.geo_keywords\n"
            "4. Copy profile URLs and paste into the agent's search tab"
        ),
    }

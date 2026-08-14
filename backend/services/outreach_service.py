"""
Outreach Service — generates personalised message packs.
Uses fast model (cheap) — drafting doesn't need deep reasoning.
Cost: ~$0.002–0.004 per candidate depending on provider.
"""

from pathlib import Path
from models.schemas import ScoredCandidate, OutreachDraft
from services.llm_service import complete_json
from loguru import logger

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "outreach.txt"


def _load_prompt(company_name: str, recruiter_name: str, tone: str) -> str:
    template = PROMPT_PATH.read_text()
    return (
        template
        .replace("{company_name}", company_name)
        .replace("{recruiter_name}", recruiter_name)
        .replace("{tone}", tone)
    )


def _extract_hooks(candidate: ScoredCandidate) -> list[str]:
    """Extract personalisation hooks from candidate data for the prompt."""
    hooks = []
    p = candidate.profile
    bd = candidate.score_breakdown

    current_job = p.experience[0] if p.experience else None
    current_title = current_job.title if current_job else (p.basic_info.headline or "")
    current_company = current_job.company_name if current_job else (p.company.name if p.company else "")

    is_open = False
    raw = p.metadata.raw_data or {}
    if raw:
        is_open = raw.get("is_likely_to_engage", False) or raw.get("is_open_to_work", False)

    if is_open:
        hooks.append(f"{p.basic_info.full_name} is open to work — higher receptivity expected")
    if current_company:
        hooks.append(f"Currently at {current_company} — reference this specifically")
    if bd.crm_background >= 15:
        hooks.append("Strong CRM background — mention the 4CECloud Salesforce ecosystem angle")
    if bd.title_match >= 25:
        hooks.append(f"Title '{current_title}' is a direct match — reference it")
    if p.skills:
        skills_str = ", ".join([s.name for s in p.skills[:3]])
        hooks.append(f"Key skills to mention: {skills_str}")
    if not p.basic_info.email:
        hooks.append("No email available — focus on LinkedIn connection note + InMail")

    return hooks


def _build_candidate_context(candidate: ScoredCandidate, role_name: str) -> str:
    p = candidate.profile
    hooks = _extract_hooks(candidate)

    current_job = p.experience[0] if p.experience else None
    current_title = current_job.title if current_job else (p.basic_info.headline or "")
    current_company = current_job.company_name if current_job else (p.company.name if p.company else "")
    skills_str = ", ".join([s.name for s in p.skills[:8]])

    return f"""CANDIDATE:
Name: {p.basic_info.full_name}
Current role: {current_title} at {current_company}
Location: {p.basic_info.location or ""}
Headline: {p.basic_info.headline or ""}
Top skills: {skills_str}
Open to work: {any("open to work" in h.lower() for h in hooks)}
Has email: {bool(p.basic_info.email)}
Fitment score: {candidate.fitment_score:.0f}/100
Why they fit: {candidate.score_reasoning}

ROLE BEING HIRED: {role_name}

PERSONALISATION HOOKS (use the most relevant):
{chr(10).join(f'- {h}' for h in hooks)}

Generate all message variants now. Return valid JSON only."""


async def generate_outreach(
    candidate: ScoredCandidate,
    role_name: str,
    company_name: str = "4CECloud Labs",
    recruiter_name: str = "Meghana",
    tone: str = "professional-warm",
) -> OutreachDraft:
    """
    Generate a full message pack for one candidate.
    Uses fast model (cheap) — message writing doesn't need deep reasoning.
    Recruiter reviews and sends manually. AI never sends autonomously.
    """
    system_prompt = _load_prompt(company_name, recruiter_name, tone)
    user_message = _build_candidate_context(candidate, role_name)

    logger.info(f"Generating outreach for {candidate.profile.basic_info.full_name}")

    data = await complete_json(
        system_prompt=system_prompt,
        user_message=user_message,
        use_smart_model=False,   # fast/cheap model is fine for drafting
        temperature=0.7,         # slight creativity for natural messages
        max_tokens=2000,
    )

    # Enforce 300-char limit on LinkedIn connection note
    note = data.get("linkedin_connection_note", "")
    if len(note) > 300:
        note = note[:297] + "..."

    return OutreachDraft(
        linkedin_connection_note=note,
        linkedin_inmail_subject=data.get("linkedin_inmail_subject", ""),
        linkedin_inmail_body=data.get("linkedin_inmail_body", ""),
        email_subject=data.get("email_subject", ""),
        email_body=data.get("email_body", ""),
        follow_up_1=data.get("follow_up_1", ""),
        follow_up_2=data.get("follow_up_2", ""),
        personalisation_hooks=data.get("personalisation_hooks", []),
    )

"""
Scoring Service — AI-powered candidate ranking.
Uses smart model (gpt-4o or mixtral) for better reasoning quality.
Cost: ~$0.005–0.015 per candidate depending on provider.
"""

import asyncio
from pathlib import Path
from models.schemas import CandidateProfile, JDSearchSpec, ScoredCandidate, ScoreBreakdown
from services.llm_service import complete_json
from loguru import logger

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "scorer.txt"


def _load_prompt() -> str:
    return PROMPT_PATH.read_text()


def _build_profile_summary(profile: CandidateProfile, spec: JDSearchSpec) -> str:
    current_job = profile.experience[0] if profile.experience else None
    current_title = current_job.title if current_job else (profile.basic_info.headline or "")
    current_company = current_job.company_name if current_job else (profile.company.name if profile.company else "")

    # Estimate years of experience from employment history
    years = 0
    for job in profile.experience:
        start = job.start_date or ""
        end = job.end_date or ""
        try:
            s_year = int(start[:4]) if start else 2020
            e_year = int(end[:4]) if end else 2024
            years += max(0, e_year - s_year)
        except (ValueError, TypeError):
            pass

    is_open = False
    raw = profile.metadata.raw_data or {}
    if raw:
        is_open = raw.get("is_likely_to_engage", False) or raw.get("is_open_to_work", False)

    skills_str = ", ".join([s.name for s in profile.skills[:12]])

    return f"""CANDIDATE PROFILE:
Name: {profile.basic_info.full_name}
Current title: {current_title}
Current company: {current_company}
Location: {profile.basic_info.location or ""}
Headline: {profile.basic_info.headline or ""}
Skills: {skills_str}
Years experience: {years or 'Unknown'}
Open to work: {is_open}
Has verified email: {bool(profile.basic_info.email)}

JOB SPECIFICATION:
Role summary: {spec.summary}
Primary titles: {', '.join(spec.primary_titles[:5])}
Required skills: {', '.join(spec.required_skills[:8])}
Target companies: {', '.join(spec.target_companies[:6])}
Seniority: {', '.join(spec.seniority_levels)}
Geography: {', '.join(spec.geo_keywords[:4])}

Score this candidate now."""


async def score_candidate(profile: CandidateProfile, spec: JDSearchSpec) -> ScoredCandidate:
    """Score a single candidate against the job spec using the smart LLM model."""
    system_prompt = _load_prompt()
    user_message = _build_profile_summary(profile, spec)

    try:
        data = await asyncio.wait_for(
            complete_json(
                system_prompt=system_prompt,
                user_message=user_message,
                use_smart_model=True,
                temperature=0.1,
                max_tokens=2000,
            ),
            timeout=12.0
        )

        raw_breakdown = data.get("score_breakdown", {})
        breakdown = ScoreBreakdown(
            title_match=int(raw_breakdown.get("title_match", 0)),
            skills_match=int(raw_breakdown.get("skills_match", 0)),
            crm_background=int(raw_breakdown.get("crm_background", 0)),
            job_stability=int(raw_breakdown.get("job_stability", 0)),
            geography=int(raw_breakdown.get("geography", 0)),
            bonuses=int(raw_breakdown.get("bonuses", 0)),
        )

        score = min(100.0, float(data.get("fitment_score", 50.0)))

        return ScoredCandidate(
            profile=profile,
            fitment_score=score,
            score_breakdown=breakdown,
            score_reasoning=data.get("score_reasoning", ""),
            recommended_action=data.get("recommended_action", "Consider"),
        )

    except Exception as e:
        logger.warning(f"Scoring failed or timed out for {profile.basic_info.full_name}: {e}. Using fallback score.")
        return _rule_based_fallback_score(profile, spec)


def _rule_based_fallback_score(profile: CandidateProfile, spec: JDSearchSpec) -> ScoredCandidate:
    """Simple rule-based fallback scorer — no LLM needed."""
    score = 35.0  # base

    current_job = profile.experience[0] if profile.experience else None
    current_title = current_job.title if current_job else (profile.basic_info.headline or "")

    is_open = False
    raw = profile.metadata.raw_data or {}
    if raw:
        is_open = raw.get("is_likely_to_engage", False) or raw.get("is_open_to_work", False)

    # Title match
    title_lower = current_title.lower()
    if any(t.lower() in title_lower for t in spec.primary_titles):
        score += 30
    elif any(t.lower() in title_lower for t in (spec.related_titles or [])):
        score += 15

    # Skills
    profile_skills = {s.name.lower() for s in profile.skills}
    matched = sum(1 for s in spec.required_skills if s.lower() in profile_skills)
    score += min(25, matched * 5)

    # Open to work
    if is_open:
        score += 5

    breakdown = ScoreBreakdown(
        title_match=30 if any(t.lower() in title_lower for t in spec.primary_titles) else 0,
        skills_match=min(25, matched * 5),
        crm_background=10,
        job_stability=10,
        geography=10,
        bonuses=5 if is_open else 0,
    )

    target_role = spec.role_name or (spec.primary_titles[0] if spec.primary_titles else "the target role")
    if matched > 0:
        reasoning = f"Matched {matched} key skill{'s' if matched != 1 else ''} for {target_role}."
    elif any(t.lower() in title_lower for t in spec.primary_titles):
        reasoning = f"Title alignment as {current_title} for {target_role}."
    else:
        reasoning = ""

    action = "Reach out now" if score >= 75 else ("Consider" if score >= 50 else "Skip")

    return ScoredCandidate(
        profile=profile,
        fitment_score=min(100.0, score),
        score_breakdown=breakdown,
        score_reasoning=reasoning,
        recommended_action=action,
    )


async def score_candidates_batch(
    profiles: list[CandidateProfile],
    spec: JDSearchSpec,
    concurrency: int = 3,
) -> list[ScoredCandidate]:
    """
    Score a list of candidates.
    For free tier providers (gemini / groq), scores all candidates with instant rule-based scoring
    and enhances the top 3 candidates with deep LLM evaluation to respect 15 RPM rate limits.
    For paid providers (openai), evaluates all candidates concurrently with LLM.
    """
    if not profiles:
        return []

    from config import get_settings
    settings = get_settings()

    # Pre-score all with fast rule-based scorer
    initial_scored = [_rule_based_fallback_score(p, spec) for p in profiles]
    initial_scored.sort(key=lambda c: c.fitment_score, reverse=True)

    if settings.llm_provider in ("gemini", "groq"):
        # Enrich top 3 candidates with LLM reasoning concurrently
        top_profiles = [c.profile for c in initial_scored[:3]]
        llm_results = await asyncio.gather(*[score_candidate(p, spec) for p in top_profiles], return_exceptions=True)
        
        final_scored = []
        for idx, res in enumerate(llm_results):
            if isinstance(res, ScoredCandidate):
                final_scored.append(res)
            else:
                final_scored.append(initial_scored[idx])
        
        # Append remaining candidates scored with rule-based
        final_scored.extend(initial_scored[3:])
        return sorted(final_scored, key=lambda c: c.fitment_score, reverse=True)

    # For OpenAI / production paid tier, score all with LLM
    semaphore = asyncio.Semaphore(concurrency)
    async def score_with_limit(profile: CandidateProfile) -> ScoredCandidate:
        async with semaphore:
            return await score_candidate(profile, spec)

    results = await asyncio.gather(*[score_with_limit(p) for p in profiles], return_exceptions=True)
    scored = []
    for idx, r in enumerate(results):
        if isinstance(r, ScoredCandidate):
            scored.append(r)
        else:
            scored.append(initial_scored[idx])

    return sorted(scored, key=lambda c: c.fitment_score, reverse=True)

"""
test_pipeline.py — End-to-end integration test for the full hiring pipeline.
Tests Gemini (or Groq/OpenAI) + Apollo (or mock) and validates each step.

Usage (run from hiring-agent-v2 folder):
    python scripts/test_pipeline.py
"""

import asyncio
import sys
import os

# ── Path fix: works when run from any directory ───────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR  = os.path.join(PROJECT_ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

# Change working dir to backend so .env and db file are found
os.chdir(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


async def test_all():
    print("\n" + "=" * 55)
    print("  4CECloud AI Hiring Agent -- Integration Tests")
    print("=" * 55)

    from config import get_settings
    settings = get_settings()
    print(f"\n  Config: LLM={settings.llm_provider} | model={settings.fast_model}")
    print(f"  Data source: {'Mock Data' if settings.using_mock_data else 'Apollo.io Live'}\n")

    sample_jd = """
    We are hiring an Inside Sales Representative for US region.
    Requirements:
    - 3+ years inside sales experience in SaaS/CRM
    - Salesforce or HubSpot experience required
    - US-based, remote-friendly
    - Strong outbound prospecting skills
    - Experience with Outreach.io or Salesloft preferred
    """

    spec = None
    scored = None
    profiles = []

    # ── Test 1: JD Parser ─────────────────────────────────────
    print("[1] Testing JD Parser (LLM call)...")
    try:
        from services.jd_service import parse_jd
        spec = await parse_jd(sample_jd, "Inside Sales - US Region")
        assert spec.primary_titles, "No primary titles extracted"
        assert spec.geo_keywords,   "No geo keywords extracted"
        print(f"    OK  Titles: {spec.primary_titles[:3]}")
        print(f"        Geo:    {spec.geo_keywords[:3]}")
    except Exception as e:
        print(f"    FAIL: {e}")
        if "GEMINI_API_KEY" not in str(e) and "GROQ_API_KEY" not in str(e):
            print("         --> Check that GEMINI_API_KEY or GROQ_API_KEY is set in your .env file")
        # Build a minimal spec so later tests can still run
        from models.schemas import JDSearchSpec
        spec = JDSearchSpec(
            primary_titles=["Inside Sales Representative"],
            related_titles=["SDR", "BDR"],
            required_skills=["Salesforce", "HubSpot"],
            geo_keywords=["United States"],
            seniority_levels=["mid", "senior"],
            summary="US Inside Sales role",
        )

    # ── Test 2: Candidate search ──────────────────────────────
    print("\n[2] Testing candidate search...")
    try:
        from services.apollo_service import apollo_search
        profiles = await apollo_search(spec, max_results=5)
        if profiles:
            print(f"    OK  {len(profiles)} candidates sourced")
            print(f"        First: {profiles[0].full_name} -- {profiles[0].current_title} at {profiles[0].current_company}")
        else:
            print("    INFO: 0 candidates returned from search (check Apollo filters or API key)")
    except Exception as e:
        print(f"    FAIL: {e}")
        profiles = []

    # ── Test 3: Candidate scoring ─────────────────────────────
    print("\n[3] Testing AI scorer (LLM call)...")
    try:
        if profiles:
            from services.candidate_enrichment import CandidateEnrichmentService
            import providers.apollo_mapper
            enrich_service = CandidateEnrichmentService()
            canonical_profile = enrich_service.enrich(profiles[0].raw_data or {}, profiles[0].source or "apollo")

            from services.scoring_service import score_candidate
            scored = await score_candidate(canonical_profile, spec)
            assert 0 <= scored.fitment_score <= 100
            print(f"    OK  {scored.profile.basic_info.full_name}: {scored.fitment_score:.0f}/100")
            print(f"        Action: {scored.recommended_action}")
        else:
            print("    SKIP (no profiles from step 2)")
    except Exception as e:
        print(f"    FAIL: {e}")

    # ── Test 4: Outreach generation ───────────────────────────
    print("\n[4] Testing outreach generator (LLM call)...")
    try:
        if scored:
            from services.outreach_service import generate_outreach
            draft = await generate_outreach(
                scored, "Inside Sales - US Region",
                "4CECloud Labs", "Meghana", "professional-warm"
            )
            assert draft.linkedin_connection_note
            assert len(draft.linkedin_connection_note) <= 300
            print(f"    OK  Note ({len(draft.linkedin_connection_note)} chars): {draft.linkedin_connection_note[:60]}...")
            print(f"        Subject: {draft.linkedin_inmail_subject}")
        else:
            print("    SKIP (no scored candidate from step 3)")
    except Exception as e:
        print(f"    FAIL: {e}")

    # ── Test 5: Full LangGraph pipeline ──────────────────────
    print("\n[5] Testing full LangGraph pipeline (all steps)...")
    try:
        from agents.hiring_graph import run_pipeline
        result = await run_pipeline(
            jd_text=sample_jd,
            role_name="Inside Sales - US Region",
            max_candidates=3
        )
        assert result.candidates
        print(f"    OK  run_id={result.run_id}")
        print(f"        Sourced: {result.total_sourced} from {result.data_source}")
        print(f"        Top: {result.candidates[0].profile.basic_info.full_name} ({result.candidates[0].fitment_score:.0f}/100)")
    except Exception as e:
        print(f"    FAIL: {e}")

    print("\n" + "=" * 55)
    print("  Done. Integration tests completed.")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(test_all())

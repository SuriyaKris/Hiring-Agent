"""
seed_mock.py — Load mock candidates into the database.

Run from the hiring-agent-v2 folder:
    backend\venv\Scripts\python.exe scripts\seed_mock.py   (Windows)
    python scripts/seed_mock.py                            (Mac/Linux)
"""

import asyncio
import sys
import os
import json

# ── Resolve paths regardless of where script is called from ──────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR  = os.path.join(PROJECT_ROOT, "backend")

# Add backend to Python path so imports work
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Set working dir to backend so DB file and .env are found correctly
os.chdir(BACKEND_DIR)

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from db import init_db, AsyncSessionLocal, CandidateRecord


MOCK_CANDIDATES = [
    {
        "linkedin_url": "https://linkedin.com/in/sarah-johnson-salesforce",
        "full_name": "Sarah Johnson",
        "headline": "Senior Inside Sales AE | Salesforce | CRM Expert | Open to Work",
        "current_company": "Salesforce",
        "current_title": "Senior Inside Sales Account Executive",
        "location": "Austin, TX, United States",
        "fitment_score": 91.0,
        "score_breakdown_json": json.dumps({"title_match": 30, "skills_match": 23, "crm_background": 20, "job_stability": 13, "geography": 10, "bonuses": 10}),
        "score_reasoning": "Direct title match as Inside Sales AE at Salesforce. Open to work and US-based. 6 years shows stability.",
        "recommended_action": "Reach out now",
        "email": "sarah.j@sample.com",
        "phone": "+1-512-555-0001",
        "is_open_to_work": True,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "Inside Sales - US Region",
    },
    {
        "linkedin_url": "https://linkedin.com/in/priya-sharma-salesexec",
        "full_name": "Priya Sharma",
        "headline": "US Sales Executive | Salesforce CRM | $2M+ ARR Closed | Chicago Remote",
        "current_company": "ZoomInfo",
        "current_title": "US Sales Executive",
        "location": "Chicago, IL, United States",
        "fitment_score": 94.0,
        "score_breakdown_json": json.dumps({"title_match": 30, "skills_match": 24, "crm_background": 20, "job_stability": 15, "geography": 10, "bonuses": 8}),
        "score_reasoning": "Exact title match for US Sales Executive at ZoomInfo. $2M+ ARR closed. Open to work.",
        "recommended_action": "Reach out now",
        "email": "priya.s@sample.com",
        "phone": "+1-312-555-0002",
        "is_open_to_work": True,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "US Sales Executive",
    },
    {
        "linkedin_url": "https://linkedin.com/in/james-chen-bdr-hubspot",
        "full_name": "James Chen",
        "headline": "BDR to SDR to AE | HubSpot | SaaS Sales | Dallas TX",
        "current_company": "HubSpot",
        "current_title": "Business Development Representative",
        "location": "Dallas, TX, United States",
        "fitment_score": 72.0,
        "score_breakdown_json": json.dumps({"title_match": 18, "skills_match": 20, "crm_background": 18, "job_stability": 10, "geography": 10, "bonuses": 0}),
        "score_reasoning": "BDR at HubSpot. CRM ecosystem experience. Related but not direct title match.",
        "recommended_action": "Consider",
        "email": "james.c@sample.com",
        "phone": "",
        "is_open_to_work": False,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "Inside Sales - US Region",
    },
    {
        "linkedin_url": "https://linkedin.com/in/ashley-williams-salesloft",
        "full_name": "Ashley Williams",
        "headline": "Inside Sales Rep | Salesloft | CRM | Remote US | Open to Opportunities",
        "current_company": "Salesloft",
        "current_title": "Inside Sales Representative",
        "location": "Atlanta, GA, United States",
        "fitment_score": 84.0,
        "score_breakdown_json": json.dumps({"title_match": 28, "skills_match": 22, "crm_background": 18, "job_stability": 12, "geography": 10, "bonuses": 5}),
        "score_reasoning": "Direct title match at Salesloft. Strong CRM knowledge. Open to work.",
        "recommended_action": "Reach out now",
        "email": "ashley.w@sample.com",
        "phone": "+1-404-555-0003",
        "is_open_to_work": True,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "Inside Sales - US Region",
    },
    {
        "linkedin_url": "https://linkedin.com/in/michael-torres-veeva",
        "full_name": "Michael Torres",
        "headline": "Account Executive | SMB and Mid-Market | Veeva | Salesforce Partner | NY",
        "current_company": "Veeva Systems",
        "current_title": "Account Executive",
        "location": "New York, NY, United States",
        "fitment_score": 79.0,
        "score_breakdown_json": json.dumps({"title_match": 22, "skills_match": 20, "crm_background": 20, "job_stability": 13, "geography": 10, "bonuses": 5}),
        "score_reasoning": "Account Executive at Veeva (Salesforce ecosystem). NY East Coast location.",
        "recommended_action": "Reach out now",
        "email": "",
        "phone": "",
        "is_open_to_work": False,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "US Sales Executive",
    },
    {
        "linkedin_url": "https://linkedin.com/in/carlos-mendez-ncino",
        "full_name": "Carlos Mendez",
        "headline": "Sales Executive | B2B SaaS | nCino | Salesforce Stack | Austin TX",
        "current_company": "nCino",
        "current_title": "Sales Executive",
        "location": "Austin, TX, United States",
        "fitment_score": 88.0,
        "score_breakdown_json": json.dumps({"title_match": 28, "skills_match": 22, "crm_background": 18, "job_stability": 12, "geography": 10, "bonuses": 8}),
        "score_reasoning": "Sales Executive at nCino with Salesforce stack. Open to work. Austin TX timezone ideal.",
        "recommended_action": "Reach out now",
        "email": "carlos.m@sample.com",
        "phone": "",
        "is_open_to_work": True,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "US Sales Executive",
    },
    {
        "linkedin_url": "https://linkedin.com/in/jennifer-lee-mulesoft",
        "full_name": "Jennifer Lee",
        "headline": "CRM Sales Specialist | MuleSoft | Seattle WA | Open to Work",
        "current_company": "MuleSoft",
        "current_title": "CRM Sales Specialist",
        "location": "Seattle, WA, United States",
        "fitment_score": 81.0,
        "score_breakdown_json": json.dumps({"title_match": 22, "skills_match": 23, "crm_background": 20, "job_stability": 12, "geography": 10, "bonuses": 8}),
        "score_reasoning": "CRM Sales Specialist at MuleSoft (Salesforce company). Top-tier CRM credential. Open to work.",
        "recommended_action": "Reach out now",
        "email": "jennifer.l@sample.com",
        "phone": "+1-206-555-0005",
        "is_open_to_work": True,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "US Sales Executive",
    },
    {
        "linkedin_url": "https://linkedin.com/in/david-kim-gong-sdr",
        "full_name": "David Kim",
        "headline": "SDR | Outbound Sales | Gong.io | Seeking AE role | SF Bay Area",
        "current_company": "Gong",
        "current_title": "Sales Development Representative",
        "location": "San Francisco, CA, United States",
        "fitment_score": 62.0,
        "score_breakdown_json": json.dumps({"title_match": 12, "skills_match": 18, "crm_background": 15, "job_stability": 8, "geography": 10, "bonuses": 5}),
        "score_reasoning": "SDR at Gong. Below target seniority. 2.5 years. Open to work and seeking AE role.",
        "recommended_action": "Consider",
        "email": "david.k@sample.com",
        "phone": "",
        "is_open_to_work": True,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "Inside Sales - US Region",
    },
    {
        "linkedin_url": "https://linkedin.com/in/rachel-green-copado",
        "full_name": "Rachel Green",
        "headline": "VP Inside Sales | Ex-Salesforce | Copado | US Remote",
        "current_company": "Copado",
        "current_title": "VP of Inside Sales",
        "location": "Denver, CO, United States",
        "fitment_score": 76.0,
        "score_breakdown_json": json.dumps({"title_match": 20, "skills_match": 22, "crm_background": 20, "job_stability": 15, "geography": 10, "bonuses": 5}),
        "score_reasoning": "VP-level may be overqualified for IC role but strong Copado/Salesforce background.",
        "recommended_action": "Consider",
        "email": "rachel.g@sample.com",
        "phone": "+1-720-555-0004",
        "is_open_to_work": False,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "Inside Sales - US Region",
    },
    {
        "linkedin_url": "https://linkedin.com/in/tom-bradley-zoho",
        "full_name": "Tom Bradley",
        "headline": "Inside Sales | Zoho CRM | SMB Focus | Houston TX",
        "current_company": "Zoho",
        "current_title": "Inside Sales Representative",
        "location": "Houston, TX, United States",
        "fitment_score": 54.0,
        "score_breakdown_json": json.dumps({"title_match": 20, "skills_match": 12, "crm_background": 10, "job_stability": 8, "geography": 10, "bonuses": 0}),
        "score_reasoning": "Inside Sales title match but Zoho is lower-tier. Only 1.5 years. Lower priority.",
        "recommended_action": "Skip",
        "email": "",
        "phone": "",
        "is_open_to_work": False,
        "source": "mock",
        "raw_json": "{}",
        "role_name": "Inside Sales - US Region",
    },
]


async def seed():
    await init_db()
    from services.candidate_enrichment import CandidateEnrichmentService
    import providers.mock_mapper # Ensure normalizer is registered
    enricher = CandidateEnrichmentService()
    
    count = 0
    async with AsyncSessionLocal() as db:
        from sqlalchemy import delete
        await db.execute(delete(CandidateRecord))
        await db.commit()
        
        for c in MOCK_CANDIDATES:
            try:
                profile = enricher.enrich(c, "mock")
                c["raw_json"] = json.dumps(profile.model_dump(mode="json"))
            except Exception as e:
                print(f"Failed to normalize seeded candidate {c.get('full_name')}: {e}")
                c["raw_json"] = "{}"
            db.add(CandidateRecord(**c))
            count += 1
        await db.commit()
    print(f"\n  Seeded {count} mock candidates into hiring_agent.db")
    print("  Open http://localhost:5173 -> Candidates tab to see them\n")


if __name__ == "__main__":
    asyncio.run(seed())

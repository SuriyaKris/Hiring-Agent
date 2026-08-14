"""Pydantic request/response schemas for all API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── JD Parser ────────────────────────────────────────────────

class JDParseRequest(BaseModel):
    text: str
    role_name: str


class JDSearchSpec(BaseModel):
    primary_titles: list[str]
    related_titles: list[str]
    required_skills: list[str]
    nice_to_have_skills: list[str] = []
    target_companies: list[str] = []
    excluded_companies: list[str] = []
    seniority_levels: list[str] = []
    geo_keywords: list[str] = []
    min_experience_years: int = 2
    boolean_search_string: str = ""
    summary: str = ""
    # New Phase 1 fields for Feature Engineering
    target_titles: list[str] = []
    target_persona: str = ""
    target_territory: str = ""
    jd_requirements_text: Optional[str] = None
    role_name: Optional[str] = None
    currently_using_technology_uids: list[str] = []



from schemas.candidate_profile import CandidateProfile


class LegacyCandidateProfile(BaseModel):
    linkedin_url: str
    full_name: str
    headline: str = ""
    current_company: str = ""
    current_title: str = ""
    location: str = ""
    years_experience: Optional[float] = None
    skills: list[str] = []
    is_open_to_work: bool = False
    email: Optional[str] = None
    phone: Optional[str] = None
    source: str = "apollo"          # "apollo" | "mock" | "proxycurl"
    raw_data: Optional[dict] = None




class ScoreBreakdown(BaseModel):
    title_match: int = 0
    skills_match: int = 0
    crm_background: int = 0
    job_stability: int = 0
    geography: int = 0
    bonuses: int = 0


class CandidateFeatures(BaseModel):
    title_keyword_match: Optional[float] = None
    title_semantic_sim: Optional[float] = None
    about_semantic_sim: Optional[float] = 0.0
    about_semantic_sim_raw: Optional[float] = 0.0
    experience_semantic_sim: Optional[float] = 0.0
    experience_semantic_sim_raw: Optional[float] = 0.0
    total_experience_years: Optional[float] = None
    relevant_experience_years: Optional[float] = None
    territory_match: Optional[float] = None


class ScoredCandidate(BaseModel):
    profile: CandidateProfile
    fitment_score: float
    score_breakdown: ScoreBreakdown
    score_reasoning: str
    recommended_action: str      # "Reach out now" | "Consider" | "Skip"
    features: Optional[CandidateFeatures] = None


# ── Search ───────────────────────────────────────────────────

class SearchRequest(BaseModel):
    spec: JDSearchSpec
    max_results: int = Field(25, le=100)
    enrich_contacts: bool = False


class SearchResponse(BaseModel):
    candidates: list[ScoredCandidate]
    total_found: int
    data_source: str             # "apollo" | "mock"
    search_query_used: str = ""


# ── Outreach ─────────────────────────────────────────────────

class OutreachRequest(BaseModel):
    candidate: ScoredCandidate
    role_name: str
    company_name: str = "4CECloud Labs"
    recruiter_name: str = "Meghana"
    tone: str = "professional-warm"


class OutreachDraft(BaseModel):
    linkedin_connection_note: str
    linkedin_inmail_subject: str
    linkedin_inmail_body: str
    email_subject: str
    email_body: str
    follow_up_1: str
    follow_up_2: str
    personalisation_hooks: list[str]


# ── Pipeline (full auto run) ─────────────────────────────────

class PipelineRequest(BaseModel):
    jd_text: str
    role_name: str
    recruiter_name: str = "Meghana"
    company_name: str = "4CECloud Labs"
    max_candidates: int = Field(20, le=50)
    data_source: str = "apollo"
    spec: Optional[JDSearchSpec] = None


class PipelineResult(BaseModel):
    spec: JDSearchSpec
    candidates: list[ScoredCandidate]
    data_source: str
    total_sourced: int
    run_id: str


# ── Dashboard / tracking ─────────────────────────────────────

class VerdictUpdate(BaseModel):
    candidate_linkedin_url: str
    verdict: str               # "shortlist" | "reject" | "maybe"


class OutreachSaveRequest(BaseModel):
    candidate_linkedin_url: str
    candidate_name: str
    role_name: str
    channel: str               # "linkedin_connect" | "linkedin_inmail" | "email"
    message_sent: str


class OutreachReplyUpdate(BaseModel):
    record_id: int
    status: str                # "replied" | "not_interested" | "interested" | "no_response"
    notes: str = ""


# ── Candidate Intelligence Additions ──────────────────────────────────────────

class ApolloSearchRequest(BaseModel):
    spec: JDSearchSpec
    max_results: int = 25


class UrlSearchRequest(BaseModel):
    session_id: Optional[str] = None
    linkedin_search_url: Optional[str] = None
    indeed_search_url: Optional[str] = None
    max_results: int = 10


class EnrichRequest(BaseModel):
    candidate_linkedin_url: str


class RankRequest(BaseModel):
    spec: JDSearchSpec
    candidates: list[CandidateProfile]


class SearchSessionCreateRequest(BaseModel):
    jd_text: str
    role_name: str
    linkedin_search_url: Optional[str] = None
    indeed_search_url: Optional[str] = None
    max_candidates: int = 20


"""LangGraph Sourcing Pipeline — Stateful orchestration of the Candidate Intelligence workflow."""

import uuid
import json
from typing import TypedDict, Optional, List
from loguru import logger

from models.schemas import JDSearchSpec, ScoredCandidate, CandidateProfile, PipelineResult
from services.jd_service import parse_jd
from services.apollo_search_planner import ApolloSearchPlanner
from providers.apollo_search import ApolloSearchProvider
from services.candidate_aggregator import CandidateAggregator
from services.candidate_normalizer import CandidateNormalizer
from providers.apollo_provider import ApolloProvider
from services.deduplication_service import DeduplicationService
from services.scoring_service import score_candidates_batch
from config import get_settings

settings = get_settings()


class HiringState(TypedDict):
    """Shared state object passed between all LangGraph nodes."""
    run_id: str
    jd_text: str
    role_name: str
    recruiter_name: str
    company_name: str
    max_candidates: int

    # Node-filled details
    spec_input: Optional[dict]         # Pre-parsed/edited JDSearchSpec as dict
    spec: Optional[dict]               # JDSearchSpec as dict
    apollo_filters: Optional[dict]     # Compiled Apollo query parameters
    raw_profiles: Optional[list]       # Sourced raw profiles list
    enriched_profiles: Optional[list]  # Normalized and resolved profiles
    scored_candidates: Optional[list]  # Evaluated fitment scores list
    data_source: str
    error: Optional[str]
    status: str                        # "running" | "completed" | "error"
    audit_trail: List[str]             # Step logging history list
    exclusion_set: Optional[list]      # List of identity values to exclude
    role_track_id: Optional[str]       # Matched role track ID for search session


# ── Node Definitions ──────────────────────────────────────────────────────────

async def node_parse_jd(state: HiringState) -> HiringState:
    """1. JD Understanding Agent: Parses input job requirements."""
    logger.info(f"[{state['run_id']}] Node: parse_jd")
    state["audit_trail"].append("Started JD analysis")
    try:
        if state.get("spec_input"):
            state["spec"] = state["spec_input"]
            state["audit_trail"].append("Using pre-edited sourcing criteria spec")
        else:
            spec = await parse_jd(state["jd_text"], state["role_name"])
            state["spec"] = spec.model_dump()
            state["audit_trail"].append(f"Successfully parsed JD requirements for role '{state['role_name']}'")
    except Exception as e:
        state["error"] = f"JD parsing failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] JD parse error: {e}")
    return state


async def node_apollo_planner(state: HiringState) -> HiringState:
    """2. Apollo Search Planner: Maps parsed requirements to Apollo filter models."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: apollo_planner")
    state["audit_trail"].append("Compiling Apollo query filters")
    try:
        spec = JDSearchSpec(**state["spec"])
        planner = ApolloSearchPlanner()
        # Compile base (level 0) filters
        filters = planner.compile_filters(spec, broadening_level=0)
        state["apollo_filters"] = filters
        state["audit_trail"].append("Completed Apollo filters planning")
    except Exception as e:
        state["error"] = f"Search planning failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] Planner error: {e}")
    return state


async def node_apollo_search(state: HiringState) -> HiringState:
    """3. Apollo Discovery Agent: Queries Apollo mixed people search API."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: apollo_search")
    state["audit_trail"].append("Executing Apollo search")
    try:
        spec = JDSearchSpec(**state["spec"])
        searcher = ApolloSearchProvider()
        
        # Load compiled filters and extract max candidates limit
        target_count = state["max_candidates"]
        overfetch_count = min(target_count + 5, 25)
        profiles = await searcher.search_profiles(spec, max_results=overfetch_count)
        logger.info(f"[Diversity] Requested {overfetch_count} candidates (target: {target_count}) for company diversification")
        
        state["raw_profiles"] = [p.model_dump() for p in profiles]
        state["audit_trail"].append(f"Discovered {len(profiles)} profiles via Apollo Sourcing (overfetched from target {target_count})")
    except Exception as e:
        # Gracefully log search failures and fall back to auxiliary URLs
        logger.error(f"[{state['run_id']}] Apollo search error: {e}")
        state["raw_profiles"] = []
        state["audit_trail"].append(f"Apollo search execution failed: {e}")
    return state





async def node_candidate_aggregator(state: HiringState) -> HiringState:
    """5. Candidate Aggregator: Combines Apollo and fallback URL profiles."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: candidate_aggregator")
    try:
        from schemas.candidate_profile import CandidateProfile as AppProfile
        apollo_list = [AppProfile(**p) for p in (state.get("raw_profiles") or [])]
        fallback_list = [AppProfile(**p) for p in (state.get("enriched_profiles") or [])]
        
        aggregator = CandidateAggregator()
        merged = aggregator.aggregate(
            apollo_list,
            fallback_list,
            exclusion_set=set(state.get("exclusion_set") or []),
            role_track_id=state.get("role_track_id")
        )
        
        state["raw_profiles"] = [p.model_dump() for p in merged]
        state["audit_trail"].append(f"Aggregated candidates into unified list (Total: {len(merged)})")
    except Exception as e:
        state["error"] = f"Candidate aggregation failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] Aggregation error: {e}")
    return state


async def node_candidate_normalizer(state: HiringState) -> HiringState:
    """6. Candidate Normalizer: Standardizes naming casing, companies, titles."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: candidate_normalizer")
    try:
        from schemas.candidate_profile import CandidateProfile as AppProfile
        profiles = [AppProfile(**p) for p in (state.get("raw_profiles") or [])]
        
        normalizer = CandidateNormalizer()
        normalized = [normalizer.normalize(p) for p in profiles]
        
        state["raw_profiles"] = [p.model_dump() for p in normalized]
        state["audit_trail"].append(f"Standardized metadata for {len(normalized)} candidates")
    except Exception as e:
        state["error"] = f"Candidate normalization failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] Normalization error: {e}")
    return state


async def node_apollo_enrichment(state: HiringState) -> HiringState:
    """7. Apollo Enrichment Agent: Resolves verified contact details and socials."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: apollo_enrichment")
    try:
        import asyncio
        from schemas.candidate_profile import CandidateProfile as AppProfile
        profiles = [AppProfile(**p) for p in (state.get("raw_profiles") or [])]
        
        enricher = ApolloProvider()
        sem = asyncio.Semaphore(5)

        async def enrich_candidate(p: AppProfile) -> AppProfile:
            async with sem:
                try:
                    if await enricher.can_enrich(p):
                        return await enricher.enrich(p)
                except Exception as ex:
                    logger.warning(f"Enrichment failed for '{p.basic_info.full_name}': {ex}")
                return p

        enriched = await asyncio.gather(*[enrich_candidate(p) for p in profiles])
            
        state["raw_profiles"] = [p.model_dump() for p in enriched]
        state["audit_trail"].append("Enriched candidate contact profiles via Apollo Lookup")
    except Exception as e:
        state["error"] = f"Candidate enrichment failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] Enrichment error: {e}")
    return state


async def node_identity_resolution(state: HiringState) -> HiringState:
    """8. Identity Resolution & Deduplication: Removes duplicate records."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: identity_resolution")
    try:
        from schemas.candidate_profile import CandidateProfile as AppProfile
        profiles = [AppProfile(**p) for p in (state.get("raw_profiles") or [])]
        
        dedup = DeduplicationService()
        unique = dedup.deduplicate(profiles)
        
        state["raw_profiles"] = [p.model_dump() for p in unique]
        state["audit_trail"].append(f"Resolved duplicate identities (Unique: {len(unique)})")
    except Exception as e:
        state["error"] = f"Identity resolution failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] Resolution error: {e}")
    return state


async def node_score_candidates(state: HiringState) -> HiringState:
    """9. AI Match Agent: Scores candidate match fitments against requirements."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: score_candidates")
    try:
        from schemas.candidate_profile import CandidateProfile as AppProfile
        spec = JDSearchSpec(**state["spec"])
        profiles = [AppProfile(**p) for p in (state.get("raw_profiles") or [])]
        
        if not profiles:
            state["scored_candidates"] = []
            return state
            
        scored = await score_candidates_batch(profiles, spec, concurrency=3)
        
        # Compute and embed feature engineered metrics in raw_data to persist in database raw_json
        from services.feature_engineering_service import add_engineered_metrics
        for c in scored:
            metrics = add_engineered_metrics(c.profile, spec)
            if metrics:
                c.profile.metadata.raw_data.update(metrics)
                
        state["scored_candidates"] = [c.model_dump() for c in scored]
        state["audit_trail"].append("Completed AI profile match scoring and feature engineering")
    except Exception as e:
        state["error"] = f"Fitment scoring failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] Scoring error: {e}")
    return state



async def node_ranking_agent(state: HiringState) -> HiringState:
    """10. Ranking Agent: Sorts and updates state metrics."""
    if state.get("status") == "error":
        return state
    logger.info(f"[{state['run_id']}] Node: ranking_agent")
    try:
        scored = [ScoredCandidate(**c) for c in (state.get("scored_candidates") or [])]
        
        # Sort candidates descending by fitment score
        scored.sort(key=lambda x: x.fitment_score, reverse=True)
        
        # Apply company diversity filtering on the sorted scored candidates list
        from utils.diversifier import diversify_by_company
        target_count = state["max_candidates"]
        
        def get_company(c: ScoredCandidate) -> str:
            p = c.profile
            current_job = p.experience[0] if p.experience else None
            return current_job.company_name if current_job else (p.company.name if p.company else "")
            
        diversified = diversify_by_company(
            scored,
            get_company=get_company,
            max_per_company=3,
            max_total=target_count,
        )
        
        state["scored_candidates"] = [c.model_dump() for c in diversified]
        state["status"] = "completed"
        state["audit_trail"].append(f"Ranked and applied company diversity filter (retained {len(diversified)} of target {target_count})")
    except Exception as e:
        state["error"] = f"Ranking failed: {e}"
        state["status"] = "error"
        logger.error(f"[{state['run_id']}] Ranking error: {e}")
    return state


# ── Build Graph ──────────────────────────────────────────────────────────────

def build_graph():
    """Build the state graph workflow using LangGraph."""
    try:
        from langgraph.graph import StateGraph, END
        
        graph = StateGraph(HiringState)
        
        graph.add_node("parse_jd", node_parse_jd)
        graph.add_node("apollo_planner", node_apollo_planner)
        graph.add_node("apollo_search", node_apollo_search)
        graph.add_node("candidate_aggregator", node_candidate_aggregator)
        graph.add_node("candidate_normalizer", node_candidate_normalizer)
        graph.add_node("apollo_enrichment", node_apollo_enrichment)
        graph.add_node("identity_resolution", node_identity_resolution)
        graph.add_node("score_candidates", node_score_candidates)
        graph.add_node("ranking_agent", node_ranking_agent)
        
        graph.set_entry_point("parse_jd")
        graph.add_edge("parse_jd", "apollo_planner")
        graph.add_edge("apollo_planner", "apollo_search")
        graph.add_edge("apollo_search", "candidate_aggregator")
        graph.add_edge("candidate_aggregator", "candidate_normalizer")
        graph.add_edge("candidate_normalizer", "apollo_enrichment")
        graph.add_edge("apollo_enrichment", "identity_resolution")
        graph.add_edge("identity_resolution", "score_candidates")
        graph.add_edge("score_candidates", "ranking_agent")
        graph.add_edge("ranking_agent", END)
        
        return graph.compile()
    except ImportError:
        logger.warning("LangGraph not available — using manual sequential fallback pipeline")
        return None


_graph = None


async def run_pipeline(
    jd_text: str,
    role_name: str,
    recruiter_name: str = "Meghana",
    company_name: str = "4CECloud Labs",
    max_candidates: int = 20,
    spec: Optional[JDSearchSpec] = None,
    exclusion_set: Optional[list] = None,
    role_track_id: Optional[str] = None,
) -> PipelineResult:
    """Entry point to execute the candidate intelligence workflow."""
    global _graph
    run_id = str(uuid.uuid4())[:8]

    initial_state: HiringState = {
        "run_id": run_id,
        "jd_text": jd_text,
        "role_name": role_name,
        "recruiter_name": recruiter_name,
        "company_name": company_name,
        "max_candidates": max_candidates,
        "spec_input": spec.model_dump() if spec else None,
        "spec": None,
        "apollo_filters": None,
        "raw_profiles": None,
        "enriched_profiles": None,
        "scored_candidates": None,
        "data_source": "apollo",
        "error": None,
        "status": "running",
        "audit_trail": [],
        "exclusion_set": exclusion_set,
        "role_track_id": role_track_id,
    }

    if _graph is None:
        _graph = build_graph()

    if _graph is not None:
        logger.info(f"[{run_id}] Executing LangGraph pipeline")
        final_state = await _graph.ainvoke(initial_state)
    else:
        logger.info(f"[{run_id}] Executing manual fallback pipeline")
        state = initial_state
        state = await node_parse_jd(state)
        state = await node_apollo_planner(state)
        state = await node_apollo_search(state)
        state = await node_candidate_aggregator(state)
        state = await node_candidate_normalizer(state)
        state = await node_apollo_enrichment(state)
        state = await node_identity_resolution(state)
        state = await node_score_candidates(state)
        state = await node_ranking_agent(state)
        final_state = state

    if final_state.get("error"):
        raise RuntimeError(final_state["error"])

    spec = JDSearchSpec(**final_state["spec"]) if final_state.get("spec") else JDSearchSpec(
        primary_titles=[], related_titles=[], required_skills=[], summary=role_name
    )
    scored = [ScoredCandidate(**c) for c in (final_state.get("scored_candidates") or [])]

    return PipelineResult(
        spec=spec,
        candidates=scored,
        data_source="apollo",
        total_sourced=len(scored),
        run_id=run_id,
    )

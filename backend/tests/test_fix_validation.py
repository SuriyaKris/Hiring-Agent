"""
Unit tests validating fixes for:
1. Deep JD parsing & Bangalore location preservation
2. Role matching without stale role title pollution
3. Geographic sourcing filters
4. Complete absence of fake/fallback mock candidate generation
"""

import pytest
from models.schemas import JDSearchSpec
from services.apollo_search_planner import ApolloSearchPlanner, clean_geo_locations_for_apollo
from nlp.keyword_extractor import (
    extract_backup_titles,
    extract_backup_territory,
    extract_backup_geo_keywords,
)
from services.jd_service import merge_role_name_into_titles
import services.apollo_service as apollo_service
import providers.apollo_provider as apollo_provider


def test_bangalore_location_preservation():
    """Verify Bangalore is preserved as city/territory and not collapsed to India only."""
    jd_bangalore = """
    Job Title: Senior Backend Engineer
    Company: Acme Tech
    Location: Bangalore, Karnataka, India
    
    We are seeking an experienced Backend Engineer to build scalable microservices.
    Requirements:
    - 5+ years of Python and FastAPI experience
    - Deep knowledge of PostgreSQL and Redis
    - Cloud experience with AWS (ECS, Lambda, S3)
    """
    territory = extract_backup_territory(jd_bangalore)
    assert "Bangalore" in territory or "Bengaluru" in territory

    geo_kw = extract_backup_geo_keywords(jd_bangalore)
    assert any(k.lower() in ("bangalore", "bengaluru") for k in geo_kw)
    assert "India" in geo_kw

    # Check that Apollo planner receives Bangalore in person_locations
    spec = JDSearchSpec(
        primary_titles=["Senior Backend Engineer"],
        related_titles=["Backend Engineer"],
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        geo_keywords=geo_kw,
        target_territory=territory,
        summary="Backend Engineer in Bangalore"
    )
    planner = ApolloSearchPlanner()
    filters = planner.compile_filters(spec, broadening_level=0)
    assert "person_locations" in filters
    locs = [loc.lower() for loc in filters["person_locations"]]
    assert any("bangalore" in l or "bengaluru" in l for l in locs)


def test_role_title_isolation():
    """Verify that a stale role_name does not pollute or override parsed JD primary titles."""
    # When JD has specific titles, merge_role_name_into_titles should not prioritize a stale role
    parsed_from_jd = ["Senior React Developer", "Frontend Engineer"]
    
    # Passing an unrelated or default role name
    merged = merge_role_name_into_titles("Inside Sales – US Region", parsed_from_jd)
    # The primary title (first element) must remain the actual JD title
    assert merged[0] == "Senior React Developer"

    # Apollo planner should search for the JD title
    spec = JDSearchSpec(
        primary_titles=["Senior React Developer"],
        related_titles=["Frontend Developer"],
        required_skills=["React", "TypeScript"],
        role_name="Inside Sales – US Region",  # stale role name in spec
        summary="React Developer"
    )
    planner = ApolloSearchPlanner()
    filters = planner.compile_filters(spec, broadening_level=0)
    assert filters["person_titles"] == ["Senior React Developer"]


def test_no_mock_candidate_generators():
    """Verify that synthetic mock candidate generation and enrichment functions are deleted."""
    assert not hasattr(apollo_service, "_get_mock_candidates"), "_get_mock_candidates must not exist"
    assert not hasattr(apollo_provider.ApolloProvider, "_enrich_with_mock_data"), "_enrich_with_mock_data must not exist"


def test_clean_geo_locations_preserves_cities():
    """Verify clean_geo_locations_for_apollo preserves cities like Bangalore, London, Austin."""
    locations = ["Bangalore", "Bengaluru", "India", "Remote", "Austin", "Texas", "US Remote"]
    cleaned = clean_geo_locations_for_apollo(locations)
    assert "Bangalore" in cleaned
    assert "Bengaluru" in cleaned
    assert "India" in cleaned
    assert "Austin" in cleaned
    assert "Texas" in cleaned
    assert "Remote" not in cleaned
    assert "US Remote" not in cleaned

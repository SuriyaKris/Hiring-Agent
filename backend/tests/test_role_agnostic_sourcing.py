"""Tests for role-agnostic parsing, geographic location extraction, and search planning."""

import pytest
from models.schemas import JDSearchSpec
from services.apollo_search_planner import ApolloSearchPlanner, clean_geo_locations_for_apollo
from nlp.keyword_extractor import extract_backup_territory, extract_backup_titles, extract_backup_persona
from services.feature_engineering_service import check_territory_match


def test_clean_geo_locations_for_apollo():
    """Verify non-geographic keywords like Remote, Hybrid, Anywhere are filtered out."""
    input_geos = ["Remote", "London", "US Remote", "Berlin", "Hybrid", "Anywhere"]
    cleaned = clean_geo_locations_for_apollo(input_geos)
    assert cleaned == ["London", "Berlin"]

    remote_only = ["Remote", "Anywhere", "Worldwide"]
    assert clean_geo_locations_for_apollo(remote_only) == []


def test_search_planner_with_remote_and_no_location():
    """Verify search planner does not inject US locations when role is remote or unspecified."""
    spec_remote = JDSearchSpec(
        primary_titles=["Full Stack Engineer"],
        related_titles=["Software Engineer", "Backend Developer"],
        required_skills=["React", "Node.js", "TypeScript"],
        geo_keywords=["Remote"],
        target_territory="Remote",
        summary="Remote Full Stack Engineer",
        role_name="Full Stack Engineer"
    )
    planner = ApolloSearchPlanner()
    filters_remote = planner.compile_filters(spec_remote, broadening_level=0)
    
    # Locations should be empty so Apollo searches globally
    assert filters_remote["person_locations"] == []
    assert "Full Stack Engineer" in filters_remote["person_titles"]


def test_search_planner_with_non_us_location():
    """Verify search planner preserves explicit non-US locations."""
    spec_uk = JDSearchSpec(
        primary_titles=["Frontend Developer"],
        related_titles=["UI Engineer"],
        required_skills=["Vue.js", "CSS"],
        geo_keywords=["London", "United Kingdom"],
        target_territory="United Kingdom",
        summary="London Frontend Developer",
        role_name="Frontend Developer"
    )
    planner = ApolloSearchPlanner()
    filters_uk = planner.compile_filters(spec_uk, broadening_level=0)
    
    assert filters_uk["person_locations"] == ["London", "United Kingdom"]
    assert "United States" not in filters_uk["person_locations"]


def test_territory_match_remote_and_global():
    """Verify territory matching correctly matches any candidate for remote/global roles."""
    assert check_territory_match("Austin, TX", "Remote") == 1.0
    assert check_territory_match("London, UK", "Remote") == 1.0
    assert check_territory_match("Bengaluru, India", "") == 1.0
    assert check_territory_match("Berlin, Germany", "Global") == 1.0
    assert check_territory_match("Toronto, Canada", "Worldwide") == 1.0


def test_backup_extraction_utilities():
    """Verify heuristic extraction works across various domains and territories."""
    tech_jd = """
    We are hiring a Senior Backend Engineer to join our core infrastructure team.
    Requirements:
    - 5+ years of Python, PostgreSQL, and FastAPI experience
    - Experience designing scalable distributed systems
    Location: Remote (Work from home)
    """
    titles = extract_backup_titles(tech_jd)
    assert any("Backend" in t or "Software" in t or "Engineer" in t for t in titles)
    
    territory = extract_backup_territory(tech_jd)
    assert territory == "Remote"

    uk_jd = """
    Position: Lead Product Designer
    Location: London, United Kingdom
    """
    assert extract_backup_territory(uk_jd) in ("United Kingdom", "London")
    assert "Product Designer" in extract_backup_titles(uk_jd)

"""
Unit tests for Feature Engineering fixes (Interval-merging, is_current fallback, explicit date warning, and region disambiguation).
"""

import sys
import os
import logging
from loguru import logger

# Add backend directory to Python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from models.schemas import JDSearchSpec
from schemas.candidate_profile import CandidateProfile, BasicInfo, SchemaMetadata, ExperienceItem
from services.feature_engineering_service import FeatureEngineeringService, parse_date_to_year_fraction, merge_intervals, check_territory_match


def test_interval_merging():
    print("\n--- Running Test: Interval Merging ---")
    # Non-overlapping
    assert merge_intervals([(2020.0, 2021.0), (2022.0, 2023.0)]) == [(2020.0, 2021.0), (2022.0, 2023.0)]
    
    # Overlapping
    assert merge_intervals([(2020.0, 2022.0), (2021.0, 2023.0)]) == [(2020.0, 2023.0)]
    
    # Fully nested
    assert merge_intervals([(2020.0, 2023.0), (2021.0, 2022.0)]) == [(2020.0, 2023.0)]
    
    # Adjacent
    assert merge_intervals([(2020.0, 2021.0), (2021.0, 2022.0)]) == [(2020.0, 2022.0)]
    
    print("Interval Merging Tests: PASSED")


def test_candidate_overlapping_experience():
    print("\n--- Running Test: Candidate Overlapping Experience ---")
    spec = JDSearchSpec(
        primary_titles=["Account Executive"],
        related_titles=[],
        required_skills=[],
        target_titles=["Account Executive"],
        target_persona="Account Executive",
        target_territory="California"
    )
    
    # Candidate with overlapping roles
    profile = CandidateProfile(
        basic_info=BasicInfo(
            full_name="Alex Smith",
            headline="Account Executive",
            location="San Francisco, CA",
            linkedin_url="https://linkedin.com/in/alex-smith-ae"
        ),
        experience=[
            ExperienceItem(
                company_name="Company A",
                title="Account Executive",
                start_date="2020-01",
                end_date="2022-01",
                is_current=False
            ),
            ExperienceItem(
                company_name="Company B (Concurrent)",
                title="Account Executive",
                start_date="2021-01",
                end_date="2021-12",
                is_current=False
            )
        ],
        metadata=SchemaMetadata(
            source="mock",
            raw_data={"years_experience": 1.0}  # Apollo says 1, history shows 2.0 (overlapping)
        )
    )
    
    service = FeatureEngineeringService()
    features = service.compute_features(profile, spec)
    
    assert features is not None
    # 2020-01 to 2022-01 is exactly 2.0 years.
    # The concurrent role (2021-01 to 2021-12) is fully nested, so total tenure should be exactly 2.0.
    # Without merge, it would be 2.0 + 0.92 = 2.92.
    print(f"Computed total experience years: {features.total_experience_years:.2f}")
    assert round(features.total_experience_years, 2) == 2.0
    assert round(features.relevant_experience_years, 2) == 2.0
    print("Candidate Overlapping Experience Tests: PASSED")


def test_is_current_selection():
    print("\n--- Running Test: Current Job Selection ---")
    spec = JDSearchSpec(
        primary_titles=["Senior Account Executive"],
        related_titles=[],
        required_skills=[],
        target_titles=["Senior Account Executive"],
        target_persona="Senior Account Executive",
        target_territory="California"
    )
    
    # Candidate where current role is at index 1
    profile = CandidateProfile(
        basic_info=BasicInfo(
            full_name="Jordan Lee",
            headline="Salesperson",
            location="San Francisco, CA",
            linkedin_url="https://linkedin.com/in/jordan-lee-sae"
        ),
        experience=[
            ExperienceItem(
                company_name="Past Company",
                title="Sales Intern",
                start_date="2018-01",
                end_date="2019-01",
                is_current=False
            ),
            ExperienceItem(
                company_name="Current Company",
                title="Senior Account Executive",
                start_date="2020-01",
                end_date="Present",
                is_current=True
            )
        ],
        metadata=SchemaMetadata(source="mock")
    )
    
    service = FeatureEngineeringService()
    features = service.compute_features(profile, spec)
    assert features is not None
    # If it correctly selected index 1 ("Senior Account Executive") instead of fallback index 0 ("Sales Intern"):
    # then title_keyword_match should be 1.0.
    print(f"Jordan Lee title_keyword_match: {features.title_keyword_match}")
    assert features.title_keyword_match == 1.0
    print("Current Job Selection Tests: PASSED")


def test_date_parse_failures():
    print("\n--- Running Test: Date Parse Failures ---")
    
    # Test that parse_date_to_year_fraction returns None on genuine parse failures
    assert parse_date_to_year_fraction("NotADate") is None
    
    # Verify that experience loops log warning and skip items rather than crashing
    spec = JDSearchSpec(
        primary_titles=["Account Executive"],
        related_titles=[],
        required_skills=[],
        target_titles=["Account Executive"],
        target_persona="Account Executive",
        target_territory="California"
    )
    
    profile = CandidateProfile(
        basic_info=BasicInfo(full_name="Robin Miller", location="San Francisco, CA", linkedin_url="https://linkedin.com/in/robin"),
        experience=[
            ExperienceItem(
                company_name="Company X",
                title="Account Executive",
                start_date="InvalidDateStr",
                end_date="2022-01",
                is_current=False
            ),
            ExperienceItem(
                company_name="Company Y",
                title="Account Executive",
                start_date="2020-01",
                end_date="2021-01",
                is_current=False
            )
        ],
        metadata=SchemaMetadata(source="mock")
    )
    
    service = FeatureEngineeringService()
    features = service.compute_features(profile, spec)
    assert features is not None
    # Robin Miller's first job should be skipped, so total timeline should only reflect second job (exactly 1.0 years).
    print(f"Robin Miller total_experience_years: {features.total_experience_years:.2f}")
    assert round(features.total_experience_years, 2) == 1.0
    print("Date Parse Failure Tests: PASSED")


def test_territory_disambiguation():
    print("\n--- Running Test: Territory Disambiguation ---")
    
    # 1. New Orleans, LA vs California (should NOT match California)
    assert check_territory_match("New Orleans, LA", "California") == 0.0
    
    # 2. Los Angeles, CA vs California (should match California)
    assert check_territory_match("Los Angeles, CA", "California") == 1.0
    
    # 3. Portland, OR vs West Coast (should match West Coast/Oregon)
    assert check_territory_match("Portland, OR", "West Coast") == 1.0
    
    # 4. Portland, OR vs Oregon (should match Oregon)
    assert check_territory_match("Portland, OR", "Oregon") == 1.0
    
    print("Territory Disambiguation Tests: PASSED")


def run_all_tests():
    test_interval_merging()
    test_candidate_overlapping_experience()
    test_is_current_selection()
    test_date_parse_failures()
    test_territory_disambiguation()
    print("\nALL AUTOMATED FIX TESTS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    run_all_tests()

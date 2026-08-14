"""Test/Verification script for Candidate Profile Validator."""

import sys
import os
from datetime import datetime

# Path setup to import backend files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from schemas.candidate_profile import (
    CandidateProfile,
    BasicInfo,
    ProfileSummary,
    ExperienceItem,
    SkillItem,
    EducationItem,
    CertificationItem,
    LanguageItem,
    ProjectItem,
    AwardItem,
    CompanyDetails,
    SchemaMetadata,
)
from services.profile_validator import validate_profile


def test_validator():
    # 1. Test case: Fully populated profile
    complete_profile = CandidateProfile(
        basic_info=BasicInfo(
            full_name="Sarah Johnson",
            headline="Senior Inside Sales Account Executive",
            location="Austin, TX, United States",
            linkedin_url="https://linkedin.com/in/sarah-johnson-sales",
            email="sarah.j.sample@email.com",
            phone="+1-512-555-0001",
        ),
        summary=ProfileSummary(
            about="Experienced SaaS sales professional.",
            tagline="SaaS Sales Expert"
        ),
        experience=[
            ExperienceItem(
                company_name="Salesforce",
                title="Senior Inside Sales Account Executive",
                start_date="2020-01",
                end_date="Present",
                description="Enterprise software sales",
                is_current=True,
            )
        ],
        skills=[SkillItem(name="Salesforce CRM")],
        education=[EducationItem(school_name="University of Texas")],
        certifications=[CertificationItem(name="Salesforce Certified Administrator")],
        languages=[LanguageItem(language="English")],
        projects=[ProjectItem(name="Outbound Campaign")],
        awards=[AwardItem(title="President's Club")],
        company=CompanyDetails(name="Salesforce"),
        metadata=SchemaMetadata(source="mock"),
    )

    result_complete = validate_profile(complete_profile)
    print("Complete profile validation status:", result_complete.is_valid)
    assert result_complete.is_valid is True
    assert len(result_complete.missing_fields) == 0

    # 2. Test case: Incomplete profile
    incomplete_profile = CandidateProfile(
        basic_info=BasicInfo(
            full_name="John Doe",
            headline="SDR",
            linkedin_url="https://linkedin.com/in/john-doe",
            # missing email, phone, location
        ),
        summary=None,  # missing summary
        experience=[
            ExperienceItem(
                company_name="Acme Corp",
                title="SDR",
                is_current=True,
                # missing description
            )
        ],
        skills=[],  # missing skills
        education=[],  # missing education
        metadata=SchemaMetadata(source="mock"),
    )

    result_incomplete = validate_profile(incomplete_profile)
    print("Incomplete profile validation status:", result_incomplete.is_valid)
    print("Missing fields:", result_incomplete.missing_fields)

    assert result_incomplete.is_valid is False
    assert "Email" in result_incomplete.missing_fields
    assert "Phone" in result_incomplete.missing_fields
    assert "Location" in result_incomplete.missing_fields
    assert "Summary" in result_incomplete.missing_fields
    assert "Skills" in result_incomplete.missing_fields
    assert "Experience Description" in result_incomplete.missing_fields
    assert "Education" in result_incomplete.missing_fields
    print("Validation assertions: OK")


if __name__ == "__main__":
    test_validator()

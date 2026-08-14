"""Test/Verification script for profile merger."""

import sys
import os

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
    CompanyDetails,
    ProjectItem,
    SchemaMetadata,
)
from utils.profile_merger import merge_profiles


def test_merger():
    # 1. Profile 1 (Apollo source)
    profile1 = CandidateProfile(
        basic_info=BasicInfo(
            full_name="Sarah Johnson",
            email="sarah.j.sample@email.com",
            linkedin_url="https://linkedin.com/in/sarah-johnson-sales",
        ),
        company=CompanyDetails(name="Salesforce", website="https://salesforce.com"),
        metadata=SchemaMetadata(source="apollo", confidence=0.8, enriched=False),
    )

    # 2. Profile 2 (Playwright source)
    profile2 = CandidateProfile(
        basic_info=BasicInfo(
            full_name="Sarah Johnson",
            headline="Senior Inside Sales AE",
            location="Austin, TX",
        ),
        summary=ProfileSummary(about="SaaS and CRM Expert bio."),
        skills=[SkillItem(name="Salesforce CRM"), SkillItem(name="HubSpot")],
        experience=[
            ExperienceItem(
                company_name="Salesforce",
                title="Senior Inside Sales Account Executive",
                is_current=True,
                description="",  # Blank description
            )
        ],
        metadata=SchemaMetadata(source="playwright", confidence=0.9, enriched=False),
    )

    # 3. Profile 3 (Resume source)
    profile3 = CandidateProfile(
        basic_info=BasicInfo(
            full_name="Sarah Johnson",
        ),
        experience=[
            ExperienceItem(
                company_name="Salesforce",
                title="Senior Inside Sales Account Executive",
                is_current=True,
                description="Managed mid-market pipeline and closed CRM deals.",  # Rich description
            )
        ],
        projects=[
            ProjectItem(name="CRM Optimization Campaign", description="Optimized Salesforce pipelines")
        ],
        metadata=SchemaMetadata(source="resume", confidence=0.7, enriched=False),
    )

    # First merge (Apollo + Playwright)
    merged = merge_profiles(profile1, profile2)
    print("First Merge completed.")

    # Asserts for first merge
    assert merged.basic_info.full_name == "Sarah Johnson"
    assert merged.basic_info.email == "sarah.j.sample@email.com"
    assert merged.basic_info.headline == "Senior Inside Sales AE"
    assert merged.summary.about == "SaaS and CRM Expert bio."
    assert len(merged.skills) == 2
    assert len(merged.experience) == 1
    assert merged.experience[0].company_name == "Salesforce"
    assert merged.experience[0].description == ""  # still empty since profile2 had empty

    # Metadata asserts for first merge
    assert merged.metadata.enriched is True
    # Combined confidence should be (0.8 + 0.9) / 2 = 0.85
    assert merged.metadata.confidence == 0.85
    assert merged.metadata.last_updated is not None

    # Source assertions
    assert merged.metadata.field_sources["basic_info.email"] == "apollo"
    assert merged.metadata.field_sources["basic_info.headline"] == "playwright"
    assert merged.metadata.field_sources["summary.about"] == "playwright"

    # Second merge (Merged + Resume)
    final_profile = merge_profiles(merged, profile3)
    print("Second Merge completed.")

    # Asserts for second merge
    assert final_profile.basic_info.email == "sarah.j.sample@email.com"
    assert final_profile.basic_info.headline == "Senior Inside Sales AE"
    assert len(final_profile.experience) == 1
    # Check that the description was updated to the richer one from the resume source
    assert final_profile.experience[0].description == "Managed mid-market pipeline and closed CRM deals."
    assert len(final_profile.projects) == 1
    assert final_profile.projects[0].name == "CRM Optimization Campaign"

    # Metadata asserts for second merge
    assert final_profile.metadata.enriched is True
    # Combined confidence should be (0.85 + 0.7) / 2 = 0.775 -> rounded to 0.78 (or 0.77 due to float precision)
    assert abs(final_profile.metadata.confidence - 0.78) <= 0.02
    assert final_profile.metadata.last_updated is not None

    # Check sources
    assert final_profile.metadata.field_sources["experience[salesforce:::senior inside sales account executive].description"] == "resume"
    assert final_profile.metadata.field_sources["projects[crm optimization campaign]"] == "resume"

    print("Profile Merger Assertions: OK")


if __name__ == "__main__":
    test_merger()

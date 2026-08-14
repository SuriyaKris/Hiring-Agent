"""Test/Verification script for CandidateProfile schema."""

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


def test_schema():
    # 1. Create a dummy profile
    profile = CandidateProfile(
        basic_info=BasicInfo(
            full_name="Sarah Johnson",
            headline="Senior Inside Sales Account Executive",
            location="Austin, TX, United States",
            linkedin_url="https://linkedin.com/in/sarah-johnson-sales",
            email="sarah.j.sample@email.com",
        ),
        summary=ProfileSummary(
            about="Passionate sales professional with 6+ years of experience in SaaS and CRM ecosystems.",
            tagline="SaaS Sales Expert"
        ),
        experience=[
            ExperienceItem(
                company_name="Salesforce",
                title="Senior Inside Sales Account Executive",
                start_date="2020-01",
                end_date="Present",
                description="Managing mid-market pipeline and closing CRM deals.",
                location="Austin, TX",
                is_current=True,
            )
        ],
        skills=[
            SkillItem(name="Salesforce CRM", category="Software"),
            SkillItem(name="HubSpot", category="Software"),
            SkillItem(name="Cold Calling", category="Sales"),
        ],
        education=[
            EducationItem(
                school_name="University of Texas",
                degree="Bachelor of Business Administration",
                field_of_study="Marketing",
                start_date="2012",
                end_date="2016",
            )
        ],
        certifications=[
            CertificationItem(
                name="Salesforce Certified Administrator",
                authority="Salesforce",
                start_date="2021-06",
            )
        ],
        languages=[
            LanguageItem(language="English", proficiency="Native"),
            LanguageItem(language="Spanish", proficiency="Conversational"),
        ],
        projects=[
            ProjectItem(
                name="Outbound Automation Campaign",
                description="Designed outreach templates increasing response rate by 25%.",
            )
        ],
        awards=[
            AwardItem(
                title="President's Club 2023",
                issuer="Salesforce",
                issue_date="2023-12",
            )
        ],
        company=CompanyDetails(
            name="Salesforce",
            website="https://salesforce.com",
            size="10000+",
            industry="Software",
        ),
        metadata=SchemaMetadata(
            source="mock",
            extracted_at=datetime.utcnow(),
            raw_data={"some_key": "some_value"},
        ),
    )

    # 2. Serialize to JSON
    json_data = profile.model_dump_json()
    print("Serialization: OK")

    # 3. Deserialize from JSON
    deserialized = CandidateProfile.model_validate_json(json_data)
    print("Deserialization: OK")

    # 4. Verify fields
    assert deserialized.basic_info.full_name == "Sarah Johnson"
    assert len(deserialized.experience) == 1
    assert deserialized.experience[0].company_name == "Salesforce"
    assert deserialized.metadata.source == "mock"
    assert deserialized.metadata.raw_data == {"some_key": "some_value"}
    print("Verification: OK")


if __name__ == "__main__":
    test_schema()

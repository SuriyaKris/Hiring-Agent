"""Unit tests for Rule-Based Enrichment Planner."""

import sys
import os
import asyncio
import unittest

# Path setup to import backend files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from schemas.candidate_profile import (
    CandidateProfile, BasicInfo, SchemaMetadata, ExperienceItem, ProfileSummary,
    SkillItem, EducationItem, CertificationItem, LanguageItem, ProjectItem, AwardItem, CompanyDetails
)
from services.profile_validator import validate_profile
from services.enrichment_planner import EnrichmentPlanner


class TestEnrichmentPlanner(unittest.TestCase):
    def setUp(self):
        self.planner = EnrichmentPlanner()

    def test_plan_schedules_resume(self):
        """Test that Resume is scheduled when resume document exists and projects/experience are missing."""
        profile = CandidateProfile(
            basic_info=BasicInfo(full_name="Sarah Johnson"),
            metadata=SchemaMetadata(
                source="test",
                raw_data={"has_resume": True}
            ),
        )
        val_result = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, val_result))

        self.assertIn("Resume", plan.providers)
        self.assertIn("Running Resume due to missing:", plan.reason)
        # Cost check: Resume cost is 0.02
        self.assertGreaterEqual(plan.estimated_cost, 0.02)
        self.assertGreaterEqual(plan.estimated_time, 5.0)

    def test_plan_schedules_github(self):
        """Test that GitHub is scheduled when github_url exists and projects/languages are missing."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                github_url="https://github.com/sarah-j"
            ),
            metadata=SchemaMetadata(source="test", raw_data={}),
        )
        val_result = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, val_result))

        self.assertIn("GitHub", plan.providers)
        self.assertIn("Running GitHub due to missing:", plan.reason)

    def test_plan_schedules_company(self):
        """Test that Company is scheduled when company details are missing but company name is known."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                email="sarah@salesforce.com"
            ),
            experience=[ExperienceItem(company_name="Salesforce", title="AE", description="Sold CRM", is_current=True)],
            metadata=SchemaMetadata(source="test", raw_data={}),
        )
        val_result = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, val_result))

        self.assertIn("Company", plan.providers)
        self.assertIn("Running Company due to missing: Company", plan.reason)
        # Cost check: Company cost is 0.01
        self.assertGreaterEqual(plan.estimated_cost, 0.01)

    def test_plan_empty_when_complete(self):
        """Test that the planner returns an empty plan when all fields are complete."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                first_name="Sarah",
                last_name="Johnson",
                full_name="Sarah Johnson",
                headline="AE at Salesforce",
                location="Austin, TX",
                linkedin_url="https://linkedin.com/in/sarah-j",
                email="sarah@salesforce.com",
                phone="+12345",
            ),
            summary=ProfileSummary(about="About Sarah"),
            experience=[ExperienceItem(company_name="Salesforce", title="AE", description="Sold CRM", is_current=True)],
            skills=[SkillItem(name="Salesforce")],
            education=[EducationItem(school_name="UT")],
            certifications=[CertificationItem(name="Admin")],
            languages=[LanguageItem(language="English")],
            projects=[ProjectItem(name="Sales Bot")],
            awards=[AwardItem(title="MVP")],
            company=CompanyDetails(name="Salesforce"),
            metadata=SchemaMetadata(source="test", raw_data={}),
        )
        val_result = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, val_result))

        self.assertEqual(plan.providers, [])
        self.assertEqual(plan.estimated_cost, 0.0)
        self.assertEqual(plan.estimated_time, 0.0)
        self.assertEqual(plan.reason, "No enrichment needed.")


if __name__ == "__main__":
    unittest.main()

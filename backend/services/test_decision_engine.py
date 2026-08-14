"""Unit tests for Enrichment Decision Engine."""

import sys
import os
import asyncio
import unittest

# Path setup to import backend files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from schemas.candidate_profile import CandidateProfile, BasicInfo, SchemaMetadata
from services.enrichment_decision_engine import EnrichmentDecisionEngine
from providers.apollo_provider import ApolloProvider
from providers.browser_automation_provider import BrowserAutomationProvider
from providers.resume_provider import ResumeProvider
from providers.github_provider import GitHubProvider


class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = EnrichmentDecisionEngine()
        self.providers = [
            ApolloProvider(),
            BrowserAutomationProvider(),
            ResumeProvider(),
            GitHubProvider(),
        ]

    def test_decision_on_minimal_profile(self):
        """Test decision on a minimal profile with only full name."""
        profile = CandidateProfile(
            basic_info=BasicInfo(full_name="Sarah Johnson"),
            metadata=SchemaMetadata(source="test", raw_data={}),
        )

        decision = asyncio.run(self.engine.decide_enrichment(profile, self.providers))

        # 1. Missing fields should include basic info keys, skills, projects, summary, etc.
        self.assertIn("Email", decision.missing_fields)
        self.assertIn("Skills", decision.missing_fields)
        self.assertIn("Projects", decision.missing_fields)

        # 2. Apollo is eligible (can_enrich is True, has missing fields, priority 1).
        # GitHub is not eligible (github_url missing).
        # Playwright is not eligible (linkedin_url missing).
        # Resume is not eligible (has_resume is false/missing).
        self.assertIn("Apollo", decision.eligible_providers)
        self.assertNotIn("GitHub", decision.eligible_providers)
        self.assertNotIn("Playwright", decision.eligible_providers)

        # 3. Apollo should be the first provider to run
        self.assertEqual(decision.provider_to_run, "Apollo")
        self.assertFalse(decision.should_stop)

    def test_decision_after_apollo_sourcing(self):
        """Test decision after Apollo has sourced basic details (email, linkedin_url, location)."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                email="sarah@salesforce.com",
                linkedin_url="https://linkedin.com/in/sarah-j",
                location="Austin, TX",
            ),
            metadata=SchemaMetadata(
                source="apollo",
                raw_data={"executed_providers": ["Apollo"]},
            ),
        )

        decision = asyncio.run(self.engine.decide_enrichment(profile, self.providers))

        # 1. Apollo should be skipped/already run
        self.assertNotIn("Apollo", decision.eligible_providers)
        self.assertIn("Apollo", decision.providers_to_skip)

        # 2. Playwright should now be eligible (linkedin_url is present, priority 2)
        self.assertIn("Playwright", decision.eligible_providers)

        # 3. Resume and GitHub should be skipped (lack resume document and github_url respectively)
        self.assertNotIn("Resume", decision.eligible_providers)
        self.assertNotIn("GitHub", decision.eligible_providers)

        # 4. Playwright should run first
        self.assertEqual(decision.provider_to_run, "Playwright")
        self.assertFalse(decision.should_stop)

    def test_prerequisite_activation(self):
        """Test that GitHub provider activates when github_url is present."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                github_url="https://github.com/sarah-j",
            ),
            metadata=SchemaMetadata(source="test", raw_data={}),
        )

        decision = asyncio.run(self.engine.decide_enrichment(profile, self.providers))

        # GitHub should be eligible because github_url is present
        self.assertIn("GitHub", decision.eligible_providers)

    def test_enrichment_stops_when_no_eligible_provider(self):
        """Test that the pipeline stops when there are no eligible providers left to run."""
        # A profile with missing fields, but all providers have already run
        profile = CandidateProfile(
            basic_info=BasicInfo(full_name="Sarah Johnson"),
            metadata=SchemaMetadata(
                source="test",
                raw_data={"executed_providers": ["Apollo", "Playwright", "Resume", "GitHub"]},
            ),
        )

        decision = asyncio.run(self.engine.decide_enrichment(profile, self.providers))

        self.assertEqual(decision.eligible_providers, [])
        self.assertIsNone(decision.provider_to_run)
        self.assertTrue(decision.should_stop)

    def test_enrichment_stops_when_complete(self):
        """Test that the engine stops enrichment when all fields are complete (valid profile)."""
        from schemas.candidate_profile import (
            BasicInfo, ProfileSummary, ExperienceItem, SkillItem,
            EducationItem, CertificationItem, LanguageItem, ProjectItem, AwardItem, CompanyDetails
        )
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

        decision = asyncio.run(self.engine.decide_enrichment(profile, self.providers))

        self.assertEqual(decision.missing_fields, [])
        self.assertTrue(decision.should_stop)


if __name__ == "__main__":
    unittest.main()

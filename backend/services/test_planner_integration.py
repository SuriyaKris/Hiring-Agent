"""Integration tests for Milestone 2.6 — Planner wired into node_enrich_candidates."""

import sys
import os
import asyncio
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from schemas.candidate_profile import (
    CandidateProfile, BasicInfo, SchemaMetadata,
    ExperienceItem, SkillItem, EducationItem
)
from services.profile_validator import validate_profile
from services.enrichment_planner import EnrichmentPlanner
from providers.registry import AVAILABLE_PROVIDERS


class TestPlannerIntegration(unittest.TestCase):
    """Verify that the planner correctly routes profiles to the right providers."""

    def setUp(self):
        self.planner = EnrichmentPlanner()
        self.provider_map = {p.provider_name: p for p in AVAILABLE_PROVIDERS}

    # ── Routing tests ─────────────────────────────────────────────────────────



    def test_resume_path_routes_to_resume_provider(self):
        """Profile with resume_path in raw_data + missing fields → Planner schedules Resume."""
        profile = CandidateProfile(
            basic_info=BasicInfo(full_name="John Smith"),
            metadata=SchemaMetadata(
                source="apollo",
                raw_data={"resume_path": "/tmp/john_smith.pdf"},
            ),
        )
        validation = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, validation))

        self.assertIn("Resume", plan.providers)
        self.assertNotIn("Playwright", plan.providers)

    def test_github_url_routes_to_github_provider(self):
        """Profile with GitHub URL + missing Projects → Planner schedules GitHub."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Liam Dev",
                github_url="https://github.com/liamdev",
            ),
            metadata=SchemaMetadata(source="apollo", raw_data={}),
        )
        validation = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, validation))

        self.assertIn("GitHub", plan.providers)

    def test_complete_profile_no_providers_scheduled(self):
        """Complete profile → Planner returns empty provider list."""
        from schemas.candidate_profile import (
            ProfileSummary, CertificationItem, LanguageItem,
            ProjectItem, AwardItem, CompanyDetails
        )
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Complete Candidate",
                first_name="Complete", last_name="Candidate",
                headline="VP Sales", location="Austin, TX",
                email="complete@example.com", phone="+1234",
                linkedin_url="https://linkedin.com/in/complete",
            ),
            summary=ProfileSummary(about="Senior leader with proven track record."),
            experience=[ExperienceItem(company_name="Acme", title="VP", description="Led sales.", is_current=True)],
            skills=[SkillItem(name="Salesforce")],
            education=[EducationItem(school_name="MIT")],
            certifications=[CertificationItem(name="CRM Admin")],
            languages=[LanguageItem(language="English")],
            projects=[ProjectItem(name="AI Bot")],
            awards=[AwardItem(title="Top AE")],
            company=CompanyDetails(name="Acme"),
            metadata=SchemaMetadata(source="test", raw_data={}),
        )
        validation = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, validation))

        self.assertEqual(plan.providers, [])
        self.assertEqual(plan.reason, "No enrichment needed.")

    def test_executed_providers_not_rescheduled(self):
        """Providers already in executed_providers must not be scheduled again."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
            ),
            metadata=SchemaMetadata(
                source="apollo",
                raw_data={"has_resume": True, "executed_providers": ["Resume"]},
            ),
        )
        validation = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, validation))

        self.assertNotIn("Resume", plan.providers)

    # ── Full enrichment execution loop ────────────────────────────────────────

    def test_enrichment_execution_loop_runs_providers(self):
        """Verify the execution loop calls provider.enrich() for each planned provider."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                email="sarah@salesforce.com",
            ),
            experience=[ExperienceItem(
                company_name="Salesforce",
                title="AE",
                description="Closed $1M ARR.",
                is_current=True,
            )],
            metadata=SchemaMetadata(source="apollo", raw_data={}),
        )

        async def run():
            validation = validate_profile(profile)
            plan = await self.planner.plan(profile, validation)
            enriched = profile

            for provider_name in plan.providers:
                provider = self.provider_map.get(provider_name)
                if provider and await provider.can_enrich(enriched):
                    enriched = await provider.enrich(enriched)

            return enriched, plan

        enriched, plan = asyncio.run(run())

        # Company provider should have run since Salesforce is in experience
        if "Company" in plan.providers:
            self.assertIsNotNone(enriched.company)
            self.assertEqual(enriched.metadata.field_sources.get("company"), "Company")

        # Provider must be marked as executed
        executed = enriched.metadata.raw_data.get("executed_providers", [])
        for provider_name in plan.providers:
            if provider_name in ["Company", "GitHub"]:
                self.assertIn(provider_name, executed)

    # ── Plan cost / time accuracy ─────────────────────────────────────────────

    def test_plan_accumulates_cost_correctly(self):
        """Verify EnrichmentPlan sums cost correctly from provider registry."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Multi Provider",
                github_url="https://github.com/multi",
            ),
            metadata=SchemaMetadata(source="test", raw_data={"has_resume": True}),
        )
        validation = validate_profile(profile)
        plan = asyncio.run(self.planner.plan(profile, validation))

        # Each provider's cost should be summed
        expected_cost = sum(
            self.provider_map[name].cost
            for name in plan.providers
            if name in self.provider_map
        )
        self.assertAlmostEqual(plan.estimated_cost, round(expected_cost, 4))


if __name__ == "__main__":
    unittest.main()

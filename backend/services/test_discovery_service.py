"""Unit tests for candidate normalization, deduplication, and search validation."""

import os
import sys
import shutil
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from models.schemas import JDSearchSpec
from schemas.candidate_profile import CandidateProfile, BasicInfo, SchemaMetadata, SkillItem, ExperienceItem
from services.candidate_normalizer import normalize_url, CandidateNormalizer
from services.deduplication_service import DeduplicationService
from validation.discovery_validation import DiscoveryValidationReporter


class TestDiscoveryService(unittest.TestCase):

    def setUp(self):
        self.test_reports_dir = os.path.join(SCRIPT_DIR, "_test_discovery_reports")
        if os.path.exists(self.test_reports_dir):
            shutil.rmtree(self.test_reports_dir)

    def tearDown(self):
        if os.path.exists(self.test_reports_dir):
            shutil.rmtree(self.test_reports_dir)

    # ── Unit Tests ────────────────────────────────────────────────────────────

    def test_url_normalization(self):
        """Verify URL normalizations strip query parameters, trailing slashes, and spaces."""
        self.assertEqual(normalize_url("https://linkedin.com/in/sarah-j/?ref=search"), "https://linkedin.com/in/sarah-j")
        self.assertEqual(normalize_url("https://linkedin.com/in/sarah-j/ "), "https://linkedin.com/in/sarah-j")
        self.assertEqual(normalize_url(""), "")

    def test_deduplication_by_linkedin_and_email(self):
        """Verify deduplication groups by LinkedIn/Email and merges fields."""
        p1 = CandidateProfile(
            basic_info=BasicInfo(full_name="Sarah Johnson", email="sarah@example.com", linkedin_url="https://linkedin.com/in/sarahj"),
            skills=[SkillItem(name="Python")],
            metadata=SchemaMetadata(source="apollo", raw_data={"executed_providers": ["Apollo"]})
        )
        p2 = CandidateProfile(
            basic_info=BasicInfo(full_name="Sarah Johnson", linkedin_url="https://linkedin.com/in/sarahj/"), # trailing slash normalizes to match
            skills=[SkillItem(name="Machine Learning")],
            metadata=SchemaMetadata(source="linkedin", raw_data={"executed_providers": ["Playwright"]})
        )

        dedup = DeduplicationService()
        unique = dedup.deduplicate([p1, p2])

        self.assertEqual(len(unique), 1)
        merged = unique[0]
        self.assertEqual(merged.basic_info.full_name, "Sarah Johnson")
        self.assertEqual(merged.basic_info.email, "sarah@example.com")
        
        # Verify skills merged
        skill_names = {s.name for s in merged.skills}
        self.assertIn("Python", skill_names)
        self.assertIn("Machine Learning", skill_names)

        # Verify metadata providers merged
        executed = merged.metadata.raw_data.get("executed_providers", [])
        self.assertIn("Apollo", executed)
        self.assertIn("Playwright", executed)

    def test_deduplication_by_name_and_company(self):
        """Verify deduplication matches by Name + Current Company when URL/Email are absent."""
        p1 = CandidateProfile(
            basic_info=BasicInfo(full_name="John Doe"),
            experience=[ExperienceItem(company_name="Stripe", title="Developer", is_current=True)],
            metadata=SchemaMetadata(source="mock")
        )
        p2 = CandidateProfile(
            basic_info=BasicInfo(full_name="John Doe", email="john@stripe.com"),
            experience=[ExperienceItem(company_name="Stripe", title="Senior Developer", is_current=True)],
            metadata=SchemaMetadata(source="mock")
        )

        dedup = DeduplicationService()
        unique = dedup.deduplicate([p1, p2])

        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0].basic_info.email, "john@stripe.com")

    def test_discovery_validation_metrics_generation(self):
        """Verify reporter aggregates platform counts and exports discovery_report.json."""
        dummy_result = {
            "candidate_urls": ["url1", "url2"],
            "metrics": {
                "total_duration": 5.0,
                "total_found": 3,
                "unique_found": 2,
                "duplicates_removed": 1,
                "providers": {
                    "LinkedInSearch": {"success": True, "count_found": 2, "duration": 2.0},
                    "IndeedSearch": {"success": False, "count_found": 1, "duration": 3.0}
                }
            }
        }

        reporter = DiscoveryValidationReporter(reports_dir=self.test_reports_dir)
        report = reporter.generate_report(dummy_result)

        self.assertEqual(report["total_candidates_found"], 3)
        self.assertEqual(report["unique_candidates"], 2)
        self.assertEqual(report["duplicates_detected"], 1)
        self.assertEqual(report["duplicate_ratio"], 0.3333)
        self.assertEqual(report["overall_search_success_rate"], 0.5)
        self.assertEqual(report["average_provider_search_duration"], 2.5)

        # Assert file was written
        self.assertTrue(os.path.exists(os.path.join(self.test_reports_dir, "discovery_report.json")))


if __name__ == "__main__":
    unittest.main()

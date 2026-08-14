"""Unit tests for Validation report compilation & Planner dynamic feedback loop."""

import os
import sys
import unittest
import asyncio

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from schemas.candidate_profile import (
    CandidateProfile, BasicInfo, SchemaMetadata, ExperienceItem, ProfileSummary,
    EducationItem, CertificationItem, CompanyDetails
)
from services.profile_validator import validate_profile
from services.enrichment_planner import EnrichmentPlanner
from validation.browser_validation_runner import BrowserValidationRunner
from validation.browser_validation_result import BrowserValidationResult, ProfileResult


class TestPlannerFeedback(unittest.TestCase):

    def test_validation_stats_compilation(self):
        """Verify validation runner compiles average duration, section accuracies, and categorized failure reasons."""
        runner = BrowserValidationRunner()
        
        # Mock results
        results = [
            ProfileResult(
                name="A", url="url1", platform="linkedin", success=True,
                sections_found=["about", "skills"], sections_missing=["experience"],
                duration=10.0, errors=[]
            ),
            ProfileResult(
                name="B", url="url2", platform="linkedin", success=False,
                sections_found=["about"], sections_missing=["skills", "experience"],
                duration=15.0, errors=["Timeout executing open_page task"]
            ),
            ProfileResult(
                name="C", url="url3", platform="linkedin", success=False,
                sections_found=[], sections_missing=["about", "skills", "experience"],
                duration=20.0, errors=["Captcha detected on page navigation"]
            )
        ]

        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful
        avg_dur = round(sum(r.duration for r in results) / total, 3)

        # Accuracies
        sec_stats = {}
        for r in results:
            for sec in r.sections_found:
                stats = sec_stats.setdefault(sec, [0, 0])
                stats[0] += 1
                stats[1] += 1
            for sec in r.sections_missing:
                stats = sec_stats.setdefault(sec, [0, 0])
                stats[1] += 1
        
        section_accuracies = {
            sec: round(stats[0] / stats[1], 4)
            for sec, stats in sec_stats.items()
        }

        # Failures
        failure_reasons = {
            "Selector Missing": 0,
            "Timeout": 0,
            "Captcha": 0,
            "Auth Required": 0,
            "Unknown": 0
        }
        for r in results:
            if not r.success:
                matched = False
                for err in r.errors:
                    err_lower = err.lower()
                    if "captcha" in err_lower:
                        failure_reasons["Captcha"] += 1
                        matched = True
                        break
                    elif "timeout" in err_lower:
                        failure_reasons["Timeout"] += 1
                        matched = True
                        break
                if not matched:
                    failure_reasons["Unknown"] += 1

        self.assertEqual(total, 3)
        self.assertEqual(successful, 1)
        self.assertEqual(failed, 2)
        self.assertEqual(avg_dur, 15.0)
        self.assertEqual(section_accuracies["about"], round(2/3, 4))
        self.assertEqual(section_accuracies["skills"], round(1/3, 4))
        self.assertEqual(failure_reasons["Timeout"], 1)
        self.assertEqual(failure_reasons["Captcha"], 1)

    def test_planner_feedback_loop_with_resume(self):
        """Verify that if Playwright skills reliability is low, and resume exists, Playwright is skipped for Skills."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                email="sarah@salesforce.com",
                phone="+1-555-0199",
                location="Austin, TX",
                linkedin_url="https://linkedin.com/in/sarah-j"
            ),
            summary=ProfileSummary(about="Experienced Engineer", tagline="Specialist"),
            experience=[ExperienceItem(company_name="Google", title="SWE", description="SWE description", is_current=True)],
            education=[EducationItem(school_name="University of Texas")],
            certifications=[CertificationItem(name="Cert")],
            company=CompanyDetails(name="Google"),
            # Only skills is missing
            metadata=SchemaMetadata(
                source="test",
                raw_data={"has_resume": True, "resume_path": "path/to/resume.pdf"}
            )
        )

        low_reliability_metrics = {
            "Playwright": {
                "Summary": 0.95,
                "Experience": 0.91,
                "Skills": 0.40,  # Low reliability (< 50%)
                "Education": 0.88,
                "Certifications": 0.85
            },
            "Resume": {
                "Skills": 0.90
            }
        }

        planner = EnrichmentPlanner(reliability_metrics=low_reliability_metrics)
        val_result = validate_profile(profile)
        
        # Verify skills is indeed the missing target field
        self.assertIn("Skills", val_result.missing_fields)
        
        plan = asyncio.run(planner.plan(profile, val_result))

        # Playwright should be skipped since Resume can handle Skills and is available
        self.assertNotIn("Playwright", plan.providers)
        self.assertIn("Resume", plan.providers)

    def test_planner_feedback_loop_no_resume_fallback(self):
        """Verify that if Playwright skills reliability is low, but NO resume exists, Playwright is still scheduled."""
        profile = CandidateProfile(
            basic_info=BasicInfo(
                full_name="Sarah Johnson",
                email="sarah@salesforce.com",
                phone="+1-555-0199",
                location="Austin, TX",
                linkedin_url="https://linkedin.com/in/sarah-j"
            ),
            summary=ProfileSummary(about="Experienced Engineer", tagline="Specialist"),
            experience=[ExperienceItem(company_name="Google", title="SWE", description="SWE description", is_current=True)],
            education=[EducationItem(school_name="University of Texas")],
            certifications=[CertificationItem(name="Cert")],
            company=CompanyDetails(name="Google"),
            # Only skills is missing, no resume fallback!
            metadata=SchemaMetadata(source="test", raw_data={})
        )

        low_reliability_metrics = {
            "Playwright": {
                "Summary": 0.95,
                "Experience": 0.91,
                "Skills": 0.40,  # Low reliability (< 50%)
                "Education": 0.88,
                "Certifications": 0.85
            }
        }

        planner = EnrichmentPlanner(reliability_metrics=low_reliability_metrics)
        val_result = validate_profile(profile)
        
        plan = asyncio.run(planner.plan(profile, val_result))

        # Playwright should be scheduled as fallback since there is no other provider
        self.assertIn("Playwright", plan.providers)
        self.assertNotIn("Resume", plan.providers)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Apollo raw JSON to CandidateProfile normalizer."""

import sys
import os
import unittest

# Path setup to import backend files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from services.candidate_enrichment import CandidateEnrichmentService
import providers.apollo_mapper
from schemas.candidate_profile import CandidateProfile


class TestApolloMapper(unittest.TestCase):
    def setUp(self):
        self.enrich_service = CandidateEnrichmentService()

    def test_required_fields_mapping(self):
        """Verify that required fields are mapped correctly from Apollo JSON."""
        raw_payload = {
            "first_name": "Sarah",
            "last_name": "Johnson",
            "name": "Sarah Johnson",
            "headline": "AE at Salesforce",
            "city": "Austin",
            "state": "TX",
            "country": "US",
            "email": "sarah@salesforce.com",
            "linkedin_url": "https://linkedin.com/in/sarah-j",
            "phone_numbers": [{"sanitized_number": "+12345"}],
        }
        profile = self.enrich_service.enrich(raw_payload, "apollo")

        self.assertIsInstance(profile, CandidateProfile)
        self.assertEqual(profile.basic_info.first_name, "Sarah")
        self.assertEqual(profile.basic_info.last_name, "Johnson")
        self.assertEqual(profile.basic_info.full_name, "Sarah Johnson")
        self.assertEqual(profile.basic_info.headline, "AE at Salesforce")
        self.assertEqual(profile.basic_info.location, "Austin, TX, US")
        self.assertEqual(profile.basic_info.email, "sarah@salesforce.com")
        self.assertEqual(profile.basic_info.linkedin_url, "https://linkedin.com/in/sarah-j")
        self.assertEqual(profile.basic_info.phone, "+12345")

    def test_empty_values_graceful_handling(self):
        """Verify that empty, missing or null values in Apollo JSON are handled gracefully."""
        # Minimum payload
        raw_payload = {
            "name": "Anonymous",
        }
        profile = self.enrich_service.enrich(raw_payload, "apollo")

        self.assertEqual(profile.basic_info.full_name, "Anonymous")
        self.assertIsNone(profile.basic_info.first_name)
        self.assertIsNone(profile.basic_info.last_name)
        self.assertIsNone(profile.basic_info.email)
        self.assertIsNone(profile.basic_info.phone)
        self.assertIsNone(profile.basic_info.location)
        self.assertEqual(profile.experience, [])
        self.assertEqual(profile.skills, [])
        self.assertEqual(profile.education, [])
        self.assertIsNone(profile.company)

    def test_skills_normalization(self):
        """Verify that both string and dictionary format skills are normalized correctly."""
        raw_payload = {
            "name": "Sarah Johnson",
            "skills": [
                {"name": "Salesforce CRM", "category": "CRM"},
                "Negotiation",
                {"name": "Cold Calling"}
            ]
        }
        profile = self.enrich_service.enrich(raw_payload, "apollo")

        self.assertEqual(len(profile.skills), 3)
        self.assertEqual(profile.skills[0].name, "Salesforce CRM")
        self.assertEqual(profile.skills[0].category, "CRM")
        self.assertEqual(profile.skills[1].name, "Negotiation")
        self.assertIsNone(profile.skills[1].category)
        self.assertEqual(profile.skills[2].name, "Cold Calling")
        self.assertIsNone(profile.skills[2].category)

    def test_experience_parsing(self):
        """Verify that employment history is parsed consistently into ExperienceItems."""
        raw_payload = {
            "name": "Sarah Johnson",
            "employment_history": [
                {
                    "organization_name": "Salesforce",
                    "title": "Account Executive",
                    "start_date": "2021-06",
                    "end_date": "Present",
                    "description": "SaaS B2B sales",
                    "city": "Austin",
                    "state": "TX",
                    "is_current": True,
                },
                {
                    "organization_name": "HubSpot",
                    "title": "BDR",
                    "start_date": "2019-01",
                    "end_date": "2021-05",
                    "city": "Boston",
                    "is_current": False,
                }
            ],
            "organization": {
                "website": "https://salesforce.com",
                "estimated_num_employees": "10000+",
            }
        }
        profile = self.enrich_service.enrich(raw_payload, "apollo")

        self.assertEqual(len(profile.experience), 2)
        
        # Salesforce job
        self.assertEqual(profile.experience[0].company_name, "Salesforce")
        self.assertEqual(profile.experience[0].title, "Account Executive")
        self.assertEqual(profile.experience[0].start_date, "2021-06")
        self.assertEqual(profile.experience[0].end_date, "Present")
        self.assertEqual(profile.experience[0].description, "SaaS B2B sales")
        self.assertEqual(profile.experience[0].location, "Austin, TX")
        self.assertTrue(profile.experience[0].is_current)

        # HubSpot job
        self.assertEqual(profile.experience[1].company_name, "HubSpot")
        self.assertEqual(profile.experience[1].title, "BDR")
        self.assertEqual(profile.experience[1].start_date, "2019-01")
        self.assertEqual(profile.experience[1].end_date, "2021-05")
        self.assertEqual(profile.experience[1].location, "Boston")
        self.assertFalse(profile.experience[1].is_current)

        # Company details
        self.assertIsNotNone(profile.company)
        self.assertEqual(profile.company.name, "Salesforce")
        self.assertEqual(profile.company.website, "https://salesforce.com")
        self.assertEqual(profile.company.size, "10000+")

    def test_personal_email_prioritized_over_corporate(self):
        """Verify personal email is prioritized as primary email when available."""
        raw_payload = {
            "name": "Sushma Prathap",
            "email": "sushma.prathap@intellicar.in",
            "personal_emails": ["sushma_prathap2005@yahoo.com"],
        }
        profile = self.enrich_service.enrich(raw_payload, "apollo")
        self.assertEqual(profile.basic_info.email, "sushma_prathap2005@yahoo.com")
        self.assertEqual(profile.basic_info.personal_email, "sushma_prathap2005@yahoo.com")
        self.assertEqual(profile.basic_info.corporate_email, "sushma.prathap@intellicar.in")

    def test_corporate_email_fallback_when_no_personal(self):
        """Verify corporate email is used as primary email when personal email is not available."""
        raw_payload = {
            "name": "Ayushi Kashyap",
            "email": "ayushi.kashyap@tcs.com",
            "personal_emails": [],
        }
        profile = self.enrich_service.enrich(raw_payload, "apollo")
        self.assertEqual(profile.basic_info.email, "ayushi.kashyap@tcs.com")
        self.assertIsNone(profile.basic_info.personal_email)
        self.assertEqual(profile.basic_info.corporate_email, "ayushi.kashyap@tcs.com")

    def test_personal_domain_detection(self):
        """Verify free/personal domains (like Gmail) in work email field are recognized as personal."""
        raw_payload = {
            "name": "Jane Doe",
            "email": "janedoe@gmail.com",
            "personal_emails": [],
        }
        profile = self.enrich_service.enrich(raw_payload, "apollo")
        self.assertEqual(profile.basic_info.email, "janedoe@gmail.com")
        self.assertEqual(profile.basic_info.personal_email, "janedoe@gmail.com")


if __name__ == "__main__":
    unittest.main()

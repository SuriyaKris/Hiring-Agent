"""Unit tests for ApolloSearchPlanner."""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from models.schemas import JDSearchSpec
from services.apollo_search_planner import ApolloSearchPlanner


class TestSearchPlanner(unittest.TestCase):

    def test_strict_filters_generation(self):
        """Verify strict filters are successfully compiled from the spec."""
        spec = JDSearchSpec(
            primary_titles=["Sales Development Representative"],
            related_titles=["SDR"],
            required_skills=["Salesforce", "Outbound"],
            nice_to_have_skills=[],
            target_companies=[],
            excluded_companies=[],
            seniority_levels=["mid"],
            geo_keywords=["Texas"],
            min_experience_years=2,
            summary="SDR role"
        )
        planner = ApolloSearchPlanner()
        filters = planner.compile_filters(spec, broadening_level=0)

        self.assertEqual(filters["person_titles"], ["Sales Development Representative"])
        self.assertEqual(filters["person_locations"], ["Texas"])
        self.assertEqual(filters["person_seniorities"], ["mid"])

    def test_broadening_level_includes_related_titles(self):
        """Verify broadening level 1 adds related titles to the query list."""
        spec = JDSearchSpec(
            primary_titles=["Sales Development Representative"],
            related_titles=["SDR"],
            required_skills=["Salesforce", "Outbound"],
            nice_to_have_skills=[],
            target_companies=[],
            excluded_companies=[],
            seniority_levels=["mid"],
            geo_keywords=["Texas"],
            min_experience_years=2,
            summary="SDR role"
        )
        planner = ApolloSearchPlanner()
        filters = planner.compile_filters(spec, broadening_level=1)

        self.assertIn("SDR", filters["person_titles"])
        self.assertIn("Sales Development Representative", filters["person_titles"])


if __name__ == "__main__":
    unittest.main()

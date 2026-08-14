"""Unit tests for EnrichmentObjective model."""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from browser.models.enrichment_objective import EnrichmentObjective


class TestBrowserObjective(unittest.TestCase):
    def test_enrichment_objective_validation(self):
        """Verify model validation and defaults for EnrichmentObjective."""
        objective = EnrichmentObjective(
            goal="Enrich Candidate",
            site="linkedin",
            url="https://www.linkedin.com/in/sarah-j",
            sections=["about", "skills"]
        )

        self.assertEqual(objective.goal, "Enrich Candidate")
        self.assertEqual(objective.site, "linkedin")
        self.assertEqual(objective.url, "https://www.linkedin.com/in/sarah-j")
        self.assertEqual(objective.sections, ["about", "skills"])
        self.assertEqual(objective.priority, 1)  # Default value
        self.assertEqual(objective.timeout, 30000)  # Default value


if __name__ == "__main__":
    unittest.main()

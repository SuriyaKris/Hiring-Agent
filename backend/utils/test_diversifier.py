import unittest
from utils.diversifier import diversify_by_company

class TestDiversifier(unittest.TestCase):
    def test_diversify_by_company(self):
        candidates = [
            {"name": "Alice", "company": "Salesforce"},
            {"name": "Bob", "company": "salesforce"},
            {"name": "Charlie", "company": "Salesforce"},
            {"name": "Dave", "company": "Salesforce"},
            {"name": "Eve", "company": "HubSpot"},
            {"name": "Frank", "company": "HubSpot"},
            {"name": "Grace", "company": "Google"},
        ]

        # max_per_company = 2
        result = diversify_by_company(
            candidates,
            get_company=lambda x: x["company"],
            max_per_company=2
        )

        names = [r["name"] for r in result]
        # Should drop Charlie and Dave because Salesforce count exceeds 2
        self.assertEqual(names, ["Alice", "Bob", "Eve", "Frank", "Grace"])

        # max_total = 3
        result_max = diversify_by_company(
            candidates,
            get_company=lambda x: x["company"],
            max_per_company=2,
            max_total=3
        )
        names_max = [r["name"] for r in result_max]
        self.assertEqual(names_max, ["Alice", "Bob", "Eve"])

if __name__ == "__main__":
    unittest.main()

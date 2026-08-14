"""Test/Verification script for CandidateEnrichmentService."""

import sys
import os
from datetime import datetime
from pydantic import ValidationError

# Path setup to import backend files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from services.candidate_enrichment import CandidateEnrichmentService, BaseNormalizer, register_normalizer
from schemas.candidate_profile import CandidateProfile


# 1. Define a dummy normalizer for "test_source"
class TestSourceNormalizer(BaseNormalizer):
    def normalize(self, raw_data: dict) -> dict:
        # Map raw fields to canonical format structure
        return {
            "basic_info": {
                "full_name": raw_data.get("name_str", ""),
                "headline": raw_data.get("position_headline", ""),
                "email": raw_data.get("contact_email", ""),
            },
            "summary": {
                "about": raw_data.get("summary_paragraph", ""),
            },
            "experience": [
                {
                    "company_name": exp.get("company", ""),
                    "title": exp.get("role", ""),
                    "start_date": exp.get("started"),
                    "end_date": exp.get("ended"),
                    "is_current": exp.get("current", False),
                }
                for exp in raw_data.get("jobs", [])
            ],
            "metadata": {
                "source": "test_source",
                "extracted_at": datetime.utcnow().isoformat(),
                "raw_data": raw_data,
            }
        }


def test_enrichment():
    # 2. Register normalizer
    register_normalizer("test_source", TestSourceNormalizer())

    # 3. Create dummy raw payload
    raw_payload = {
        "name_str": "Jane Doe",
        "position_headline": "Senior Inside Sales Executive",
        "contact_email": "jane.d@example.com",
        "summary_paragraph": "Experienced sales rep.",
        "jobs": [
            {
                "company": "SaaS Corp",
                "role": "Inside Sales Specialist",
                "started": "2021-01",
                "ended": "Present",
                "current": True,
            }
        ]
    }

    # 4. Instantiate service
    service = CandidateEnrichmentService()

    # 5. Enrich candidate
    profile = service.enrich(raw_payload, "test_source")
    print("Normalise & Validate: OK")

    # 6. Assertions
    assert isinstance(profile, CandidateProfile)
    assert profile.basic_info.full_name == "Jane Doe"
    assert profile.basic_info.email == "jane.d@example.com"
    assert profile.summary.about == "Experienced sales rep."
    assert len(profile.experience) == 1
    assert profile.experience[0].company_name == "SaaS Corp"
    assert profile.metadata.source == "test_source"
    print("Verification assertions: OK")

    # 7. Check validation error handling (missing required fields)
    bad_payload = {
        # Missing 'name_str' will cause full_name to be empty string, which is OK, but if we don't have basic_info at all, or a missing required block:
    }
    # Let's write a normalizer that fails validation
    class BadNormalizer(BaseNormalizer):
        def normalize(self, raw_data: dict) -> dict:
            return {}  # Missing basic_info and metadata

    register_normalizer("bad_source", BadNormalizer())
    try:
        service.enrich({}, "bad_source")
        raise RuntimeError("Validation should have failed!")
    except ValidationError:
        print("Pydantic Validation Error Catching: OK")


if __name__ == "__main__":
    test_enrichment()

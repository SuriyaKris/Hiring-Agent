import unittest
from agents.hiring_graph import build_graph, HiringState, node_candidate_normalizer, node_ranking_agent
from schemas.candidate_profile import CandidateProfile, BasicInfo, SchemaMetadata, ExperienceItem
from models.schemas import ScoredCandidate, ScoreBreakdown

class TestPipelineDiversity(unittest.IsolatedAsyncioTestCase):
    async def test_diversity_pipeline_nodes(self):
        # Build mock raw profiles with duplicate companies
        raw_profiles = [
            # 4 Salesforce candidates
            CandidateProfile(
                basic_info=BasicInfo(full_name="A", linkedin_url="li-1"),
                experience=[ExperienceItem(company_name="Salesforce", title="AE")],
                metadata=SchemaMetadata(source="apollo")
            ),
            CandidateProfile(
                basic_info=BasicInfo(full_name="B", linkedin_url="li-2"),
                experience=[ExperienceItem(company_name="salesforce", title="AE")],
                metadata=SchemaMetadata(source="apollo")
            ),
            CandidateProfile(
                basic_info=BasicInfo(full_name="C", linkedin_url="li-3"),
                experience=[ExperienceItem(company_name="Salesforce Inc", title="AE")],
                metadata=SchemaMetadata(source="apollo")
            ),
            CandidateProfile(
                basic_info=BasicInfo(full_name="D", linkedin_url="li-4"),
                experience=[ExperienceItem(company_name="Salesforce LLC", title="AE")],
                metadata=SchemaMetadata(source="apollo")
            ),
            # 2 HubSpot candidates
            CandidateProfile(
                basic_info=BasicInfo(full_name="E", linkedin_url="li-5"),
                experience=[ExperienceItem(company_name="HubSpot", title="AE")],
                metadata=SchemaMetadata(source="apollo")
            ),
            CandidateProfile(
                basic_info=BasicInfo(full_name="F", linkedin_url="li-6"),
                experience=[ExperienceItem(company_name="HubSpot Corp", title="AE")],
                metadata=SchemaMetadata(source="apollo")
            )
        ]

        state: HiringState = {
            "run_id": "test-run",
            "jd_text": "Need sales representatives.",
            "role_name": "Inside Sales",
            "recruiter_name": "Meghana",
            "company_name": "4CECloud Labs",
            "max_candidates": 5,
            "spec": {},
            "apollo_filters": None,
            "raw_profiles": [p.model_dump() for p in raw_profiles],
            "enriched_profiles": None,
            "scored_candidates": None,
            "data_source": "apollo",
            "error": None,
            "status": "running",
            "audit_trail": [],
            "exclusion_set": None,
            "role_track_id": None
        }

        # 1. Run candidate normalizer (which standardizes metadata but doesn't filter anymore)
        state = await node_candidate_normalizer(state)
        self.assertIsNone(state.get("error"))
        self.assertEqual(len(state["raw_profiles"]), 6)

        # Map back to CandidateProfile objects to mock the scored state
        from schemas.candidate_profile import CandidateProfile as AppProfile
        normalized_profiles = [AppProfile(**p) for p in state["raw_profiles"]]

        # 2. Mock node_score_candidates output by populating scored_candidates
        # We assign fitment scores in descending order to match expected rank ordering
        scored = []
        for i, p in enumerate(normalized_profiles):
            scored.append(ScoredCandidate(
                profile=p,
                fitment_score=100.0 - i,  # A=100, B=99, C=98, D=97, E=96, F=95
                score_breakdown=ScoreBreakdown(title_match=10, skills_match=10, crm_background=10, job_stability=10, geography=10, bonuses=10),
                score_reasoning="Good fit",
                recommended_action="Consider"
            ))
        state["scored_candidates"] = [c.model_dump() for c in scored]

        # 3. Run ranking agent (which applies sorting & company diversity filter)
        state = await node_ranking_agent(state)
        self.assertIsNone(state.get("error"))

        # Check scored candidates count (should be capped at max_candidates = 5)
        scored_out = state["scored_candidates"]
        self.assertLessEqual(len(scored_out), 5)

        names = [c["profile"]["basic_info"]["full_name"] for c in scored_out]
        # Should have dropped "D" because Salesforce exceeds max_per_company = 3
        # (since Salesforce, salesforce, Salesforce Inc, Salesforce LLC normalize to 'Salesforce')
        self.assertNotIn("D", names)
        # Should contain A, B, C (Salesforce) and E, F (HubSpot) in fitment score order
        self.assertEqual(names, ["A", "B", "C", "E", "F"])

if __name__ == "__main__":
    unittest.main()

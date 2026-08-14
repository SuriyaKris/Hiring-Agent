import sys
import os
import unittest

# Add backend directory to Python path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from models.schemas import JDSearchSpec, CandidateFeatures
from schemas.candidate_profile import CandidateProfile, BasicInfo, SchemaMetadata, ExperienceItem
from services.feature_engineering_service import FeatureEngineeringService, add_engineered_metrics
from nlp.title_taxonomy import ABOUT_SEMANTIC_SIM_FLOOR, ABOUT_SEMANTIC_SIM_CEILING, EXP_SEMANTIC_SIM_FLOOR, EXP_SEMANTIC_SIM_CEILING

class TestScorecardCalibrations(unittest.TestCase):

    def setUp(self):
        self.service = FeatureEngineeringService()
        self.spec = JDSearchSpec(
            primary_titles=["Account Executive"],
            related_titles=[],
            required_skills=[],
            target_titles=["Account Executive"],
            target_persona="Senior / Account Executive - Enterprise",
            target_territory="United States",
            jd_requirements_text="Looking for a Senior Account Executive with Salesforce sales experience.",
            seniority_levels=["senior"]
        )

    def test_persona_match_removed(self):
        # Verify persona_match is not in features schema fields
        features_dict = CandidateFeatures.model_fields
        self.assertNotIn("persona_match", features_dict)

    def test_semantic_calibrations(self):
        profile = CandidateProfile(
            basic_info=BasicInfo(full_name="Jane Doe", headline="Senior Account Executive"),
            metadata=SchemaMetadata(source="apollo", raw_data={}),
            experience=[ExperienceItem(company_name="Salesforce", title="Senior Account Executive", is_current=True)]
        )
        features = self.service.compute_features(profile, self.spec)
        # Verify raw fields exist and are floats
        self.assertIsNotNone(features.about_semantic_sim_raw)
        self.assertIsNotNone(features.experience_semantic_sim_raw)
        
        # Verify calibrated fields exist and are rescaled
        self.assertIsNotNone(features.about_semantic_sim)
        self.assertIsNotNone(features.experience_semantic_sim)
        
        # Checking calibration math for a hypothetical raw score
        # e.g., if raw about score is below ABOUT_SEMANTIC_SIM_FLOOR (0.20), calibrated should be 0.0
        from services.feature_engineering_service import rescale_similarity
        self.assertEqual(rescale_similarity(0.15, ABOUT_SEMANTIC_SIM_FLOOR, ABOUT_SEMANTIC_SIM_CEILING), 0.0)
        self.assertEqual(rescale_similarity(0.65, ABOUT_SEMANTIC_SIM_FLOOR, ABOUT_SEMANTIC_SIM_CEILING), 1.0)
        rescaled = rescale_similarity(0.40, ABOUT_SEMANTIC_SIM_FLOOR, ABOUT_SEMANTIC_SIM_CEILING)
        self.assertAlmostEqual(rescaled, (0.40 - 0.20) / (0.60 - 0.20))

    def test_relevant_experience_multiplier(self):
        profile = CandidateProfile(
            basic_info=BasicInfo(full_name="Jane Doe", headline="Senior Account Executive"),
            metadata=SchemaMetadata(source="apollo", raw_data={}),
            experience=[
                ExperienceItem(
                    company_name="Salesforce",
                    title="Account Executive",
                    start_date="2020-01",
                    end_date="2021-06", # 1.5 years
                    is_current=True
                )
            ]
        )
        # Using add_engineered_metrics to test score computation
        metrics = add_engineered_metrics(profile, self.spec)
        features = metrics["engineered_features"]
        
        # 1.4167 years * 5.0 = 7.083 points (out of 10 max points)
        self.assertAlmostEqual(features["relevant_experience_years"], 1.4167, places=3)
        # fitment score should be bounded properly
        score = metrics["engineered_fitment_score"]
        self.assertTrue(0.0 <= score <= 100.0)

    def test_clean_role_name_for_search(self):
        from nlp.title_taxonomy import clean_role_name_for_search
        
        # Test clean string with delimiters
        self.assertEqual(clean_role_name_for_search("Inside Sales – US Region"), ["Inside Sales – US Region", "Inside Sales"])
        self.assertEqual(clean_role_name_for_search("Software Engineer | Full Stack"), ["Software Engineer | Full Stack", "Software Engineer"])
        self.assertEqual(clean_role_name_for_search("Account Executive - Mid-Market"), ["Account Executive - Mid-Market", "Account Executive"])
        
        # Test clean string without delimiters
        self.assertEqual(clean_role_name_for_search("Inside Sales Representative"), ["Inside Sales Representative"])
        
        # Test edge cases
        self.assertEqual(clean_role_name_for_search(None), [])
        self.assertEqual(clean_role_name_for_search("   "), [])

if __name__ == "__main__":
    unittest.main()

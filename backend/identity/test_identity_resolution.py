"""Unit tests for Candidate Identity Resolution and Similarity Matching Engine."""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from schemas.candidate_profile import CandidateProfile, BasicInfo, SkillItem, ExperienceItem, SchemaMetadata
from identity.candidate_identity import CandidateIdentity
from identity.matching_engine import MatchingEngine
from services.deduplication_service import merge_profiles


class TestIdentityResolution(unittest.TestCase):

    def setUp(self):
        self.engine = MatchingEngine(match_threshold=0.85)
        self.meta = SchemaMetadata(source="test")

    def test_hard_signals_match_exact(self):
        """Verify hard signals (email, LinkedIn, GitHub) yield exact 1.0 match score."""
        p1 = CandidateProfile(
            basic_info=BasicInfo(full_name="Sarah Connor", email="sconnor@cyberdyne.com"),
            skills=[],
            metadata=self.meta
        )
        p2 = CandidateProfile(
            basic_info=BasicInfo(full_name="S. Connor", email="sconnor@cyberdyne.com"), # name is soft mismatch but email matches
            skills=[],
            metadata=self.meta
        )

        score = self.engine.compute_match_score(p1, p2)
        self.assertEqual(score, 1.0)
        self.assertTrue(self.engine.is_match(p1, p2))

        # Check Apollo ID matching
        p1_ap = CandidateProfile(
            basic_info=BasicInfo(full_name="Apollo User"),
            metadata=SchemaMetadata(source="apollo", apollo_person_id="person_123")
        )
        p2_ap = CandidateProfile(
            basic_info=BasicInfo(full_name="Different Name"),
            metadata=SchemaMetadata(source="apollo", apollo_person_id="person_123")
        )
        self.assertEqual(self.engine.compute_match_score(p1_ap, p2_ap), 1.0)
        self.assertTrue(self.engine.is_match(p1_ap, p2_ap))

        # Check LinkedIn matching
        p3 = CandidateProfile(
            basic_info=BasicInfo(full_name="John Connor", linkedin_url="https://www.linkedin.com/in/johnconnor"),
            skills=[],
            metadata=self.meta
        )
        p4 = CandidateProfile(
            basic_info=BasicInfo(full_name="Connor John", linkedin_url="http://linkedin.com/in/johnconnor/"), # trailing slash/protocol normalization
            skills=[],
            metadata=self.meta
        )
        self.assertEqual(self.engine.compute_match_score(p3, p4), 1.0)

    def test_soft_signals_weighted_similarity(self):
        """Verify soft signals (name, company, title, location) calculate weighted similarity scores."""
        # High matching profiles
        p1 = CandidateProfile(
            basic_info=BasicInfo(full_name="Donald Knuth", location="Stanford, CA"),
            experience=[ExperienceItem(company_name="Stanford University", title="Professor of Computer Science", is_current=True)],
            metadata=self.meta
        )
        p2 = CandidateProfile(
            basic_info=BasicInfo(full_name="Donald E Knuth", location="Stanford University, California"),
            experience=[ExperienceItem(company_name="Stanford Univ.", title="Computer Science Professor", is_current=True)],
            metadata=self.meta
        )

        score = self.engine.compute_match_score(p1, p2)
        self.assertGreaterEqual(score, 0.7)  # High similarity score due to string proximity
        self.assertTrue(score > 0.7)

        # Mismatching profiles
        p3 = CandidateProfile(
            basic_info=BasicInfo(full_name="Ada Lovelace", location="London"),
            experience=[ExperienceItem(company_name="Babbage Analytical Engine", title="Programmer", is_current=True)],
            metadata=self.meta
        )
        self.assertLess(self.engine.compute_match_score(p1, p3), 0.3)
        self.assertFalse(self.engine.is_match(p1, p3))

    def test_candidate_identity_compilation(self):
        """Verify matched profiles are aggregated into a resolved CandidateIdentity structure."""
        p1 = CandidateProfile(
            basic_info=BasicInfo(full_name="Linus Torvalds", email="torvalds@linuxfoundation.org"),
            skills=[SkillItem(name="C"), SkillItem(name="Git")],
            metadata=self.meta
        )
        p2 = CandidateProfile(
            basic_info=BasicInfo(full_name="Linus B Torvalds", github_url="https://github.com/torvalds"),
            skills=[SkillItem(name="Linux Kernel Architecture")],
            metadata=self.meta
        )

        # Merge profiles and build identity wrapper
        merged_profile = merge_profiles(p1, p2)
        
        identity = CandidateIdentity(
            confidence=1.0,
            sources=["git", "linux_fdn"],
            primary_profile=merged_profile,
            aliases=["Linus Torvalds", "Linus B Torvalds"],
            matched_profiles=[p1, p2]
        )

        self.assertEqual(identity.primary_profile.basic_info.email, "torvalds@linuxfoundation.org")
        self.assertEqual(identity.primary_profile.basic_info.github_url, "https://github.com/torvalds")
        
        skills = {s.name for s in identity.primary_profile.skills}
        self.assertIn("Git", skills)
        self.assertIn("Linux Kernel Architecture", skills)
        self.assertEqual(len(identity.matched_profiles), 2)


if __name__ == "__main__":
    unittest.main()

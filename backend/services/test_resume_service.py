"""Unit tests for Milestone 2.5 — Resume Pipeline Service."""

import os
import sys
import unittest
import textwrap
import pypdf

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from services.resume_service import ResumeService


SAMPLE_RESUME_TEXT = textwrap.dedent("""
    John Smith
    john@example.com | +1-555-1234

    Summary
    Seasoned software engineer with 8 years building scalable cloud systems.

    Experience

    Senior Software Engineer
    Stripe
    Led the redesign of the payments reconciliation engine, processing $2B/day.

    Software Engineer
    Google
    Built internal tooling for ML pipeline orchestration teams.

    Education

    MIT
    Master of Science
    Computer Science

    Skills
    Python, AWS, Kubernetes, Terraform, PostgreSQL, React

    Projects

    PayFlow
    Open-source payment retry scheduler built with FastAPI and Redis.

    Certifications
    AWS Certified Solutions Architect
    Certified Kubernetes Administrator

    Awards
    Stripe Engineering Excellence Award 2023
""").strip()


def _write_temp_resume(dir_path: str, content: str, filename: str = "resume.txt") -> str:
    """Write a plain-text resume to a temporary file."""
    path = os.path.join(dir_path, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class TestResumeService(unittest.TestCase):
    def setUp(self):
        self.service = ResumeService()
        self.tmp_dir = os.path.join(SCRIPT_DIR, "_test_resume_tmp")
        os.makedirs(self.tmp_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    # ── Section splitting ────────────────────────────────────────────────────

    def test_split_sections_detects_experience(self):
        """Verify section splitter detects Experience header."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        self.assertIn("experience", sections)
        self.assertIn("Stripe", sections["experience"])

    def test_split_sections_detects_education(self):
        """Verify section splitter detects Education header."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        self.assertIn("education", sections)
        self.assertIn("MIT", sections["education"])

    def test_split_sections_detects_skills(self):
        """Verify section splitter detects Skills header."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        self.assertIn("skills", sections)
        self.assertIn("Python", sections["skills"])

    def test_split_sections_detects_projects(self):
        """Verify section splitter detects Projects header."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        self.assertIn("projects", sections)
        self.assertIn("PayFlow", sections["projects"])

    def test_split_sections_detects_certifications(self):
        """Verify section splitter detects Certifications header."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        self.assertIn("certifications", sections)
        self.assertIn("AWS Certified Solutions Architect", sections["certifications"])

    def test_split_sections_detects_awards(self):
        """Verify section splitter detects Awards header."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        self.assertIn("awards", sections)
        self.assertIn("Stripe Engineering Excellence Award", sections["awards"])

    def test_split_sections_detects_summary(self):
        """Verify section splitter detects Summary header."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        self.assertIn("summary", sections)
        self.assertIn("cloud systems", sections["summary"])

    # ── Section parsers ──────────────────────────────────────────────────────

    def test_parse_experience_returns_list(self):
        """Verify _parse_experience returns ExperienceItem list."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        result = self.service._parse_experience(sections.get("experience", ""))
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].company_name, "Stripe")
        self.assertEqual(result[0].title, "Senior Software Engineer")

    def test_parse_education_returns_list(self):
        """Verify _parse_education returns EducationItem list."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        result = self.service._parse_education(sections.get("education", ""))
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].school_name, "MIT")
        self.assertEqual(result[0].degree, "Master of Science")

    def test_parse_skills_returns_list(self):
        """Verify _parse_skills returns SkillItem list."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        result = self.service._parse_skills(sections.get("skills", ""))
        skill_names = [s.name for s in result]
        self.assertIn("Python", skill_names)
        self.assertIn("AWS", skill_names)
        self.assertIn("Kubernetes", skill_names)

    def test_parse_certifications_returns_list(self):
        """Verify _parse_certifications returns CertificationItem list."""
        sections = self.service._split_sections(SAMPLE_RESUME_TEXT)
        result = self.service._parse_certifications(sections.get("certifications", ""))
        cert_names = [c.name for c in result]
        self.assertIn("AWS Certified Solutions Architect", cert_names)

    def test_empty_section_returns_empty_list(self):
        """Verify parsers return empty lists for empty input without crashing."""
        self.assertEqual(self.service._parse_experience(""), [])
        self.assertEqual(self.service._parse_education(""), [])
        self.assertEqual(self.service._parse_skills(""), [])
        self.assertEqual(self.service._parse_projects(""), [])
        self.assertEqual(self.service._parse_certifications(""), [])
        self.assertEqual(self.service._parse_awards(""), [])

    # ── Full parse integration ────────────────────────────────────────────────

    def test_parse_docx_produces_canonical_profile(self):
        """Verify parse() on a DOCX file produces a valid CandidateProfile."""
        from docx import Document

        # Write a minimal DOCX
        docx_path = os.path.join(self.tmp_dir, "resume.docx")
        doc = Document()
        for line in SAMPLE_RESUME_TEXT.split("\n"):
            doc.add_paragraph(line)
        doc.save(docx_path)

        profile = self.service.parse(docx_path, candidate_name="John Smith")

        self.assertEqual(profile.basic_info.full_name, "John Smith")
        self.assertGreater(len(profile.experience), 0)
        self.assertGreater(len(profile.education), 0)
        self.assertGreater(len(profile.skills), 0)
        self.assertEqual(profile.metadata.source, "Resume")

    def test_unsupported_format_raises_error(self):
        """Verify extract_text raises ValueError on unsupported file formats."""
        bad_path = os.path.join(self.tmp_dir, "resume.txt")
        with open(bad_path, "w") as f:
            f.write("content")
        with self.assertRaises(ValueError):
            self.service.extract_text(bad_path)


if __name__ == "__main__":
    unittest.main()

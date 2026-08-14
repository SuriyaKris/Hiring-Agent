"""Resume Pipeline Service — Milestone 2.5.

Standalone service responsible for:
1. Extracting raw text from PDF and DOCX resume files.
2. Parsing text into canonical CandidateProfile sections using heuristic anchor matching.

This service knows nothing about LinkedIn, Playwright, or Apollo.
It only knows resume files.
"""

import re
from typing import List, Dict, Tuple, Optional
import pypdf
from docx import Document
from loguru import logger

from schemas.candidate_profile import (
    CandidateProfile, BasicInfo, SchemaMetadata,
    ExperienceItem, EducationItem, SkillItem,
    CertificationItem, ProjectItem, AwardItem, ProfileSummary
)


# ─── Section anchor definitions ────────────────────────────────────────────────
# Each entry maps a canonical section name to a list of keyword anchors.
# The parser scans lines top-to-bottom looking for these headers.

SECTION_ANCHORS: Dict[str, List[str]] = {
    "experience": [
        "experience", "work experience", "work history",
        "employment history", "professional experience",
    ],
    "education": [
        "education", "academic background", "academic history",
        "qualifications", "degrees",
    ],
    "skills": [
        "skills", "technical skills", "core competencies",
        "competencies", "key skills", "technologies",
    ],
    "projects": [
        "projects", "portfolio", "side projects",
        "personal projects", "notable projects",
    ],
    "certifications": [
        "certifications", "licenses", "credentials",
        "professional certifications",
    ],
    "awards": [
        "awards", "achievements", "honors",
        "recognitions", "accomplishments",
    ],
    "summary": [
        "summary", "professional summary", "profile",
        "objective", "about me", "career objective",
    ],
}


class ResumeService:
    """Extracts text from resume files and parses them into canonical profile sections."""

    # ─── Text Extraction ────────────────────────────────────────────────────────

    def extract_text(self, file_path: str) -> str:
        """Extract raw text from a PDF or DOCX resume file.

        Args:
            file_path: Absolute path to the resume file.

        Returns:
            Raw text content of the resume.

        Raises:
            ValueError: If the file format is unsupported.
        """
        logger.info(f"Extracting text from resume: {file_path}")
        file_path_lower = file_path.lower()

        if file_path_lower.endswith(".pdf"):
            return self._extract_pdf(file_path)
        elif file_path_lower.endswith(".docx"):
            return self._extract_docx(file_path)
        else:
            raise ValueError(f"Unsupported resume format: {file_path}. Expected .pdf or .docx")

    def _extract_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file page by page."""
        text_parts = []
        try:
            reader = pypdf.PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            logger.info(f"Extracted {len(reader.pages)} page(s) from PDF.")
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise
        return "\n".join(text_parts)

    def _extract_docx(self, file_path: str) -> str:
        """Extract text from a DOCX file paragraph by paragraph."""
        try:
            doc = Document(file_path)
            lines = [p.text for p in doc.paragraphs if p.text.strip()]
            logger.info(f"Extracted {len(lines)} paragraph(s) from DOCX.")
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise

    # ─── Section Splitting ──────────────────────────────────────────────────────

    def _split_sections(self, text: str) -> Dict[str, str]:
        """Split raw resume text into labelled sections using anchor-keyword matching."""
        lines = text.split("\n")
        sections: Dict[str, List[str]] = {}
        current_section = "header"
        sections[current_section] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                sections[current_section].append("")
                continue

            # Check if this line is a section header
            matched_section = self._match_section_header(stripped)
            if matched_section:
                current_section = matched_section
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections[current_section].append(stripped)

        return {k: "\n".join(v).strip() for k, v in sections.items()}

    def _match_section_header(self, line: str) -> Optional[str]:
        """Return the canonical section name if the line matches a section anchor, else None."""
        normalized = line.lower().strip(":•-– ").strip()
        for section, anchors in SECTION_ANCHORS.items():
            for anchor in anchors:
                # Only match if the line IS the anchor (not just contains it)
                if normalized == anchor or re.match(rf"^{re.escape(anchor)}[\s:]*$", normalized):
                    return section
        return None

    # ─── Section Parsers ────────────────────────────────────────────────────────

    def _parse_experience(self, text: str) -> List[ExperienceItem]:
        """Parse raw experience section text into ExperienceItem list."""
        items = []
        # Split on blank lines as entry separators
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        for block in blocks[:5]:  # cap at 5 entries
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if len(lines) >= 2:
                items.append(ExperienceItem(
                    title=lines[0],
                    company_name=lines[1],
                    description=" ".join(lines[2:]) if len(lines) > 2 else None,
                    is_current="present" in " ".join(lines).lower(),
                ))
        return items

    def _parse_education(self, text: str) -> List[EducationItem]:
        """Parse raw education section text into EducationItem list."""
        items = []
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        for block in blocks[:3]:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if lines:
                items.append(EducationItem(
                    school_name=lines[0],
                    degree=lines[1] if len(lines) > 1 else None,
                    field_of_study=lines[2] if len(lines) > 2 else None,
                ))
        return items

    def _parse_skills(self, text: str) -> List[SkillItem]:
        """Parse raw skills section text into SkillItem list."""
        # Split on commas, bullets, newlines, or semicolons
        raw = re.split(r"[,•\n;|/]+", text)
        return [SkillItem(name=s.strip()) for s in raw if s.strip()]

    def _parse_projects(self, text: str) -> List[ProjectItem]:
        """Parse raw projects section text into ProjectItem list."""
        items = []
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
        for block in blocks[:4]:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if lines:
                items.append(ProjectItem(
                    name=lines[0],
                    description=" ".join(lines[1:]) if len(lines) > 1 else None,
                ))
        return items

    def _parse_certifications(self, text: str) -> List[CertificationItem]:
        """Parse raw certifications section text into CertificationItem list."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return [CertificationItem(name=line) for line in lines[:6]]

    def _parse_awards(self, text: str) -> List[AwardItem]:
        """Parse raw awards section text into AwardItem list."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return [AwardItem(title=line) for line in lines[:4]]

    # ─── Main Entry Point ───────────────────────────────────────────────────────

    def parse(self, file_path: str, candidate_name: str = "Unknown") -> CandidateProfile:
        """Parse a resume file into a canonical CandidateProfile.

        Args:
            file_path: Absolute path to the .pdf or .docx resume file.
            candidate_name: Optional name to assign to the profile.

        Returns:
            A fully populated CandidateProfile.
        """
        logger.info(f"Parsing resume for: {candidate_name}")

        # 1. Extract raw text
        text = self.extract_text(file_path)

        # 2. Split into labelled sections
        sections = self._split_sections(text)
        logger.debug(f"Detected sections: {list(sections.keys())}")

        # 3. Parse summary
        summary_text = sections.get("summary", "")
        summary = ProfileSummary(about=summary_text) if summary_text else None

        # 4. Parse each section independently
        experience = self._parse_experience(sections.get("experience", ""))
        education = self._parse_education(sections.get("education", ""))
        skills = self._parse_skills(sections.get("skills", ""))
        projects = self._parse_projects(sections.get("projects", ""))
        certifications = self._parse_certifications(sections.get("certifications", ""))
        awards = self._parse_awards(sections.get("awards", ""))

        logger.info(
            f"Resume parsed — experience: {len(experience)}, education: {len(education)}, "
            f"skills: {len(skills)}, projects: {len(projects)}, "
            f"certifications: {len(certifications)}, awards: {len(awards)}"
        )

        return CandidateProfile(
            basic_info=BasicInfo(full_name=candidate_name),
            summary=summary,
            experience=experience,
            education=education,
            skills=skills,
            projects=projects,
            certifications=certifications,
            awards=awards,
            metadata=SchemaMetadata(
                source="Resume",
                raw_data={"resume_path": file_path},
                field_sources={
                    "experience": "Resume",
                    "education": "Resume",
                    "skills": "Resume",
                    "projects": "Resume",
                    "certifications": "Resume",
                    "awards": "Resume",
                },
            ),
        )

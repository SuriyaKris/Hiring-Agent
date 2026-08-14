"""Resume Parser Enrichment Provider implementing BaseProvider."""

from typing import Set
from providers.base_provider import BaseProvider
from schemas.candidate_profile import CandidateProfile
from services.resume_service import ResumeService
from loguru import logger


class ResumeProvider(BaseProvider):
    """Enriches candidate profiles using resume uploads (Experience, Projects, Education, Awards, Certifications).

    Delegates all parsing to ResumeService — the provider itself stays thin.
    It only reads `resume_path` from raw_data and hands off to the pipeline.
    """

    def __init__(self):
        self._service = ResumeService()

    @property
    def provider_name(self) -> str:
        return "Resume"

    @property
    def supported_fields(self) -> Set[str]:
        return {"Experience", "Experience Description", "Projects", "Education", "Awards", "Certifications", "Skills", "Summary"}

    @property
    def priority(self) -> int:
        return 3

    @property
    def cost(self) -> float:
        return 0.02

    @property
    def estimated_time(self) -> float:
        return 5.0

    async def can_enrich(self, profile: CandidateProfile) -> bool:
        """Requires a resume file path stored in raw_data."""
        raw = profile.metadata.raw_data or {}
        return bool(raw.get("resume_path") or raw.get("has_resume"))

    async def enrich(self, profile: CandidateProfile) -> CandidateProfile:
        """Parse resume and merge extracted fields into the canonical profile."""
        raw = profile.metadata.raw_data or {}
        resume_path = raw.get("resume_path")

        if resume_path:
            logger.info(f"ResumeProvider: parsing file at {resume_path}")
            try:
                parsed = self._service.parse(
                    file_path=resume_path,
                    candidate_name=profile.basic_info.full_name,
                )

                # Merge — never overwrite existing good data
                if not profile.experience and parsed.experience:
                    profile.experience = parsed.experience
                    profile.metadata.field_sources["experience"] = self.provider_name

                if not profile.education and parsed.education:
                    profile.education = parsed.education
                    profile.metadata.field_sources["education"] = self.provider_name

                if not profile.skills and parsed.skills:
                    profile.skills = parsed.skills
                    profile.metadata.field_sources["skills"] = self.provider_name

                if not profile.projects and parsed.projects:
                    profile.projects = parsed.projects
                    profile.metadata.field_sources["projects"] = self.provider_name

                if not profile.certifications and parsed.certifications:
                    profile.certifications = parsed.certifications
                    profile.metadata.field_sources["certifications"] = self.provider_name

                if not profile.awards and parsed.awards:
                    profile.awards = parsed.awards
                    profile.metadata.field_sources["awards"] = self.provider_name

                if not profile.summary and parsed.summary:
                    profile.summary = parsed.summary
                    profile.metadata.field_sources["summary"] = self.provider_name

            except Exception as e:
                logger.error(f"ResumeProvider: failed to parse resume — {e}")
        else:
            logger.warning("ResumeProvider: no resume_path in raw_data, skipping file parse.")

        # Track execution
        executed = raw.setdefault("executed_providers", [])
        if self.provider_name not in executed:
            executed.append(self.provider_name)
        profile.metadata.raw_data = raw

        return profile

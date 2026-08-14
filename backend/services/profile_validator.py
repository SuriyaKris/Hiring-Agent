"""Profile Validator for Canonical Candidate Schema."""

from typing import List
from pydantic import BaseModel, Field
from schemas.candidate_profile import CandidateProfile


class ValidationResult(BaseModel):
    """Encapsulates check results detailing missing fields."""
    is_valid: bool = Field(..., description="True if no checks failed/missing fields detected")
    missing_fields: List[str] = Field(default_factory=list, description="Human-readable names of missing/incomplete profile sections")


def validate_profile(profile: CandidateProfile) -> ValidationResult:
    """Validate a CandidateProfile, identifying fields that are missing or incomplete.

    Args:
        profile: The Canonical CandidateProfile object.

    Returns:
        ValidationResult indicating validity status and any missing items.
    """
    missing = []

    # 1. Basic Info
    bi = profile.basic_info
    if not bi.email or not bi.email.strip():
        missing.append("Email")
    if not bi.phone or not bi.phone.strip():
        missing.append("Phone")
    if not bi.location or not bi.location.strip():
        missing.append("Location")
    if not bi.headline or not bi.headline.strip():
        missing.append("Headline")
    if not bi.linkedin_url or not bi.linkedin_url.strip():
        missing.append("LinkedIn URL")

    # 2. Summary
    if not profile.summary or not profile.summary.about or not profile.summary.about.strip():
        missing.append("Summary")

    # 3. Experience
    if not profile.experience:
        missing.append("Experience")
    else:
        # Check if experience description is empty for any item
        has_missing_desc = False
        for exp in profile.experience:
            if not exp.description or not exp.description.strip():
                has_missing_desc = True
                break
        if has_missing_desc:
            missing.append("Experience Description")

    # 4. Skills
    if not profile.skills:
        missing.append("Skills")

    # 5. Education
    if not profile.education:
        missing.append("Education")

    # 6. Certifications
    if not profile.certifications:
        missing.append("Certifications")

    # 7. Languages
    if not profile.languages:
        missing.append("Languages")

    # 8. Projects
    if not profile.projects:
        missing.append("Projects")

    # 9. Awards
    if not profile.awards:
        missing.append("Awards")

    # 10. Company
    if not profile.company or not profile.company.name or not profile.company.name.strip():
        missing.append("Company")

    return ValidationResult(
        is_valid=len(missing) == 0,
        missing_fields=missing
    )

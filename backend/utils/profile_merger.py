"""Profile Merger Utility for combining CandidateProfile instances."""

from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, TypeVar, Callable
from schemas.candidate_profile import (
    CandidateProfile,
    BasicInfo,
    ProfileSummary,
    ExperienceItem,
    SkillItem,
    EducationItem,
    CertificationItem,
    LanguageItem,
    ProjectItem,
    AwardItem,
    CompanyDetails,
    SchemaMetadata,
)

T = TypeVar("T")


def _is_empty(val: Any) -> bool:
    """Helper to check if a value is empty (None, empty string, or empty collection)."""
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, (list, dict)) and len(val) == 0:
        return True
    return False


def _merge_value(val1: Any, val2: Any, path: str, source: str, sources_dict: Dict[str, str]) -> Any:
    """Merge two single/scalar values based on richness rules and updates source tracking."""
    if _is_empty(val1) and not _is_empty(val2):
        sources_dict[path] = source
        return val2
    if not _is_empty(val1) and _is_empty(val2):
        return val1
    if _is_empty(val1) and _is_empty(val2):
        return val1

    # Conflict resolution: if both are strings, choose the longer (richer) one
    if isinstance(val1, str) and isinstance(val2, str):
        if len(val2.strip()) > len(val1.strip()):
            sources_dict[path] = source
            return val2
        return val1

    # Default to val1 if identical or no other rule applies
    return val1


def _merge_list(
    existing_list: List[T],
    new_list: List[T],
    identity_fn: Callable[[T], Any],
    merge_fn: Callable[[T, T, str, str, Dict[str, str]], T],
    path_prefix: str,
    source: str,
    sources_dict: Dict[str, str]
) -> List[T]:
    """Merge two lists of items. Deduplicates items using identity_fn and merges matching items using merge_fn."""
    merged_items: Dict[Any, T] = {}
    
    # Process existing items
    for item in existing_list:
        key = identity_fn(item)
        merged_items[key] = item

    # Process new items
    for new_item in new_list:
        key = identity_fn(new_item)
        if key in merged_items:
            # Merge with existing item
            item_path = f"{path_prefix}[{key}]"
            merged_items[key] = merge_fn(merged_items[key], new_item, item_path, source, sources_dict)
        else:
            merged_items[key] = new_item
            sources_dict[f"{path_prefix}[{key}]"] = source

    return list(merged_items.values())


# Identity & merge helper functions for list items
def _skill_identity(s: SkillItem) -> str:
    return s.name.strip().lower()


def _skill_merge(s1: SkillItem, s2: SkillItem, path: str, source: str, sources_dict: Dict[str, str]) -> SkillItem:
    return SkillItem(
        name=s1.name,
        category=_merge_value(s1.category, s2.category, f"{path}.category", source, sources_dict),
    )


def _experience_identity(e: ExperienceItem) -> str:
    return f"{e.company_name.strip().lower()}:::{e.title.strip().lower()}"


def _experience_merge(e1: ExperienceItem, e2: ExperienceItem, path: str, source: str, sources_dict: Dict[str, str]) -> ExperienceItem:
    return ExperienceItem(
        company_name=e1.company_name,
        title=e1.title,
        start_date=_merge_value(e1.start_date, e2.start_date, f"{path}.start_date", source, sources_dict),
        end_date=_merge_value(e1.end_date, e2.end_date, f"{path}.end_date", source, sources_dict),
        description=_merge_value(e1.description, e2.description, f"{path}.description", source, sources_dict),
        location=_merge_value(e1.location, e2.location, f"{path}.location", source, sources_dict),
        employment_type=_merge_value(e1.employment_type, e2.employment_type, f"{path}.employment_type", source, sources_dict),
        is_current=e1.is_current or e2.is_current,
    )


def _education_identity(e: EducationItem) -> str:
    school = e.school_name.strip().lower()
    degree = (e.degree or "").strip().lower()
    return f"{school}:::{degree}"


def _education_merge(e1: EducationItem, e2: EducationItem, path: str, source: str, sources_dict: Dict[str, str]) -> EducationItem:
    return EducationItem(
        school_name=e1.school_name,
        degree=e1.degree,
        field_of_study=_merge_value(e1.field_of_study, e2.field_of_study, f"{path}.field_of_study", source, sources_dict),
        start_date=_merge_value(e1.start_date, e2.start_date, f"{path}.start_date", source, sources_dict),
        end_date=_merge_value(e1.end_date, e2.end_date, f"{path}.end_date", source, sources_dict),
        description=_merge_value(e1.description, e2.description, f"{path}.description", source, sources_dict),
    )


def _certification_identity(c: CertificationItem) -> str:
    return c.name.strip().lower()


def _certification_merge(c1: CertificationItem, c2: CertificationItem, path: str, source: str, sources_dict: Dict[str, str]) -> CertificationItem:
    return CertificationItem(
        name=c1.name,
        authority=_merge_value(c1.authority, c2.authority, f"{path}.authority", source, sources_dict),
        license_number=_merge_value(c1.license_number, c2.license_number, f"{path}.license_number", source, sources_dict),
        start_date=_merge_value(c1.start_date, c2.start_date, f"{path}.start_date", source, sources_dict),
        end_date=_merge_value(c1.end_date, c2.end_date, f"{path}.end_date", source, sources_dict),
        url=_merge_value(c1.url, c2.url, f"{path}.url", source, sources_dict),
    )


def _language_identity(l: LanguageItem) -> str:
    return l.language.strip().lower()


def _language_merge(l1: LanguageItem, l2: LanguageItem, path: str, source: str, sources_dict: Dict[str, str]) -> LanguageItem:
    return LanguageItem(
        language=l1.language,
        proficiency=_merge_value(l1.proficiency, l2.proficiency, f"{path}.proficiency", source, sources_dict),
    )


def _project_identity(p: ProjectItem) -> str:
    return p.name.strip().lower()


def _project_merge(p1: ProjectItem, p2: ProjectItem, path: str, source: str, sources_dict: Dict[str, str]) -> ProjectItem:
    return ProjectItem(
        name=p1.name,
        description=_merge_value(p1.description, p2.description, f"{path}.description", source, sources_dict),
        url=_merge_value(p1.url, p2.url, f"{path}.url", source, sources_dict),
        start_date=_merge_value(p1.start_date, p2.start_date, f"{path}.start_date", source, sources_dict),
        end_date=_merge_value(p1.end_date, p2.end_date, f"{path}.end_date", source, sources_dict),
    )


def _award_identity(a: AwardItem) -> str:
    return a.title.strip().lower()


def _award_merge(a1: AwardItem, a2: AwardItem, path: str, source: str, sources_dict: Dict[str, str]) -> AwardItem:
    return AwardItem(
        title=a1.title,
        issuer=_merge_value(a1.issuer, a2.issuer, f"{path}.issuer", source, sources_dict),
        issue_date=_merge_value(a1.issue_date, a2.issue_date, f"{path}.issue_date", source, sources_dict),
        description=_merge_value(a1.description, a2.description, f"{path}.description", source, sources_dict),
    )


def merge_profiles(existing: CandidateProfile, new_profile: CandidateProfile) -> CandidateProfile:
    """Merges two CandidateProfile instances.

    Follows rules:
    - Never overwrites good existing data with empty new values.
    - Merges lists (skills, experience, etc.) dynamically and deduplicates them.
    - Chooses richer (longer) strings when there are conflicts.
    - Tracks the source of each field dynamically inside metadata.field_sources.

    Args:
        existing: The current/existing candidate profile.
        new_profile: The new candidate profile data to be merged in.

    Returns:
        A new CandidateProfile representing the combined, validated profile.
    """
    # Create copies to prevent in-place mutation of argument objects
    existing_copy = existing.model_copy(deep=True)
    new_copy = new_profile.model_copy(deep=True)

    sources_dict = existing_copy.metadata.field_sources or {}
    new_source = new_copy.metadata.source or "unknown"

    # Populate missing existing field sources if empty
    if not sources_dict:
        # Default existing fields to the existing profile's source
        existing_source = existing_copy.metadata.source or "unknown"
        for field in [
            "basic_info.first_name", "basic_info.last_name", "basic_info.full_name",
            "basic_info.headline", "basic_info.location", "basic_info.linkedin_url",
            "basic_info.email", "basic_info.personal_email", "basic_info.corporate_email",
            "basic_info.phone", "basic_info.twitter_url",
            "basic_info.github_url", "basic_info.portfolio_url", "summary.about", "summary.tagline"
        ]:
            sources_dict[field] = existing_source

    # --- 1. Merge Basic Info ---
    eb = existing_copy.basic_info
    nb = new_copy.basic_info
    
    merged_basic_info = BasicInfo(
        first_name=_merge_value(eb.first_name, nb.first_name, "basic_info.first_name", new_source, sources_dict),
        last_name=_merge_value(eb.last_name, nb.last_name, "basic_info.last_name", new_source, sources_dict),
        full_name=_merge_value(eb.full_name, nb.full_name, "basic_info.full_name", new_source, sources_dict),
        headline=_merge_value(eb.headline, nb.headline, "basic_info.headline", new_source, sources_dict),
        location=_merge_value(eb.location, nb.location, "basic_info.location", new_source, sources_dict),
        linkedin_url=_merge_value(eb.linkedin_url, nb.linkedin_url, "basic_info.linkedin_url", new_source, sources_dict),
        email=_merge_value(eb.email, nb.email, "basic_info.email", new_source, sources_dict),
        personal_email=_merge_value(getattr(eb, "personal_email", None), getattr(nb, "personal_email", None), "basic_info.personal_email", new_source, sources_dict),
        corporate_email=_merge_value(getattr(eb, "corporate_email", None), getattr(nb, "corporate_email", None), "basic_info.corporate_email", new_source, sources_dict),
        phone=_merge_value(eb.phone, nb.phone, "basic_info.phone", new_source, sources_dict),
        twitter_url=_merge_value(eb.twitter_url, nb.twitter_url, "basic_info.twitter_url", new_source, sources_dict),
        github_url=_merge_value(eb.github_url, nb.github_url, "basic_info.github_url", new_source, sources_dict),
        portfolio_url=_merge_value(eb.portfolio_url, nb.portfolio_url, "basic_info.portfolio_url", new_source, sources_dict),
    )

    # --- 2. Merge Summary ---
    es = existing_copy.summary or ProfileSummary()
    ns = new_copy.summary or ProfileSummary()
    merged_summary = ProfileSummary(
        about=_merge_value(es.about, ns.about, "summary.about", new_source, sources_dict),
        tagline=_merge_value(es.tagline, ns.tagline, "summary.tagline", new_source, sources_dict),
    )

    # --- 3. Merge Lists ---
    merged_skills = _merge_list(
        existing_copy.skills, new_copy.skills, _skill_identity, _skill_merge, "skills", new_source, sources_dict
    )
    merged_experience = _merge_list(
        existing_copy.experience, new_copy.experience, _experience_identity, _experience_merge, "experience", new_source, sources_dict
    )
    merged_education = _merge_list(
        existing_copy.education, new_copy.education, _education_identity, _education_merge, "education", new_source, sources_dict
    )
    merged_certifications = _merge_list(
        existing_copy.certifications, new_copy.certifications, _certification_identity, _certification_merge, "certifications", new_source, sources_dict
    )
    merged_languages = _merge_list(
        existing_copy.languages, new_copy.languages, _language_identity, _language_merge, "languages", new_source, sources_dict
    )
    merged_projects = _merge_list(
        existing_copy.projects, new_copy.projects, _project_identity, _project_merge, "projects", new_source, sources_dict
    )
    merged_awards = _merge_list(
        existing_copy.awards, new_copy.awards, _award_identity, _award_merge, "awards", new_source, sources_dict
    )

    # --- 4. Merge Company Details ---
    ec = existing_copy.company
    nc = new_copy.company
    merged_company = None
    if ec or nc:
        ec = ec or CompanyDetails()
        nc = nc or CompanyDetails()
        merged_company = CompanyDetails(
            name=_merge_value(ec.name, nc.name, "company.name", new_source, sources_dict),
            website=_merge_value(ec.website, nc.website, "company.website", new_source, sources_dict),
            size=_merge_value(ec.size, nc.size, "company.size", new_source, sources_dict),
            industry=_merge_value(ec.industry, nc.industry, "company.industry", new_source, sources_dict),
            domain=_merge_value(ec.domain, nc.domain, "company.domain", new_source, sources_dict),
            linkedin_url=_merge_value(ec.linkedin_url, nc.linkedin_url, "company.linkedin_url", new_source, sources_dict),
        )

    # --- 5. Merge Metadata raw_data ---
    merged_raw_data = deepcopy(existing_copy.metadata.raw_data or {})
    merged_raw_data.update(new_copy.metadata.raw_data or {})

    # Create new combined metadata object
    # Any profile merge operation represents an enrichment step, so enriched is True
    # Average the confidence values of both profiles to get combined confidence
    combined_confidence = round((existing_copy.metadata.confidence + new_copy.metadata.confidence) / 2.0, 2)
    merged_metadata = SchemaMetadata(
        source=existing_copy.metadata.source,  # Keep primary original source as main source
        extracted_at=existing_copy.metadata.extracted_at,
        raw_data=merged_raw_data,
        field_sources=sources_dict,
        enriched=True,
        confidence=combined_confidence,
        last_updated=datetime.utcnow(),
    )

    return CandidateProfile(
        basic_info=merged_basic_info,
        summary=merged_summary,
        experience=merged_experience,
        skills=merged_skills,
        education=merged_education,
        certifications=merged_certifications,
        languages=merged_languages,
        projects=merged_projects,
        awards=merged_awards,
        company=merged_company,
        metadata=merged_metadata,
    )

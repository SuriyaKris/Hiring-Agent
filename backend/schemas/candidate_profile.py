"""Canonical Candidate Schema for AI Hiring Agent.

This schema defines a standardized, provider-agnostic structure for candidate profiles.
All future profile sourcing integrations (e.g. Apollo, Proxycurl, SerpAPI) must map their
raw API payloads to this model.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class BasicInfo(BaseModel):
    """Core contact and identifying details."""
    first_name: Optional[str] = Field(None, description="Candidate's first name")
    last_name: Optional[str] = Field(None, description="Candidate's last name")
    full_name: str = Field(..., description="Candidate's combined full name")
    headline: Optional[str] = Field(None, description="Professional headline/tagline")
    location: Optional[str] = Field(None, description="City, State, Country or region")
    linkedin_url: Optional[str] = Field(None, description="URL to candidate's LinkedIn profile")
    email: Optional[str] = Field(None, description="Candidate's primary contact email (personal email if available, else available work email)")
    personal_email: Optional[str] = Field(None, description="Candidate's personal email address (e.g. Gmail, Yahoo)")
    corporate_email: Optional[str] = Field(None, description="Candidate's work/corporate email address")
    phone: Optional[str] = Field(None, description="Candidate's contact phone number")
    twitter_url: Optional[str] = Field(None, description="URL to Twitter/X profile")
    github_url: Optional[str] = Field(None, description="URL to GitHub profile")
    portfolio_url: Optional[str] = Field(None, description="URL to personal website/portfolio")


class ProfileSummary(BaseModel):
    """Recruiter-facing profile executive summary or candidate's personal statement."""
    about: Optional[str] = Field(None, description="Personal bio or 'About' section from LinkedIn")
    tagline: Optional[str] = Field(None, description="A quick summary sentence/tagline")


class ExperienceItem(BaseModel):
    """A single professional job history entry."""
    company_name: str = Field(..., description="Name of the employing organization")
    title: str = Field(..., description="Job title held by the candidate")
    start_date: Optional[str] = Field(None, description="Start date (format YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="End date (format YYYY-MM, YYYY or 'Present')")
    description: Optional[str] = Field(None, description="Details of responsibilities and achievements")
    location: Optional[str] = Field(None, description="Location of work")
    employment_type: Optional[str] = Field(None, description="Employment type (e.g. Full-time, Contract, Part-time)")
    is_current: bool = Field(False, description="Flag indicating if the candidate currently works here")


class SkillItem(BaseModel):
    """Candidate professional skill or competency."""
    name: str = Field(..., description="Name of the skill")
    category: Optional[str] = Field(None, description="Category grouping for the skill")


class EducationItem(BaseModel):
    """Academic record entry."""
    school_name: str = Field(..., description="Name of the school or university")
    degree: Optional[str] = Field(None, description="Degree earned (e.g. Bachelor of Science)")
    field_of_study: Optional[str] = Field(None, description="Field of study / major")
    start_date: Optional[str] = Field(None, description="Start date (YYYY or YYYY-MM)")
    end_date: Optional[str] = Field(None, description="End date (YYYY or YYYY-MM)")
    description: Optional[str] = Field(None, description="Honors, activities, or academic details")


class CertificationItem(BaseModel):
    """Professional certifications and licenses."""
    name: str = Field(..., description="Name of the certification")
    authority: Optional[str] = Field(None, description="Issuing organization or authority")
    license_number: Optional[str] = Field(None, description="License or credential ID")
    start_date: Optional[str] = Field(None, description="Issue date (YYYY-MM or YYYY)")
    end_date: Optional[str] = Field(None, description="Expiration date (YYYY-MM or YYYY)")
    url: Optional[str] = Field(None, description="Link to verify credential online")


class LanguageItem(BaseModel):
    """Spoken/written languages and candidate proficiency."""
    language: str = Field(..., description="Name of the language")
    proficiency: Optional[str] = Field(None, description="Candidate proficiency level (e.g. Native, Fluent)")


class ProjectItem(BaseModel):
    """Independent or professional projects."""
    name: str = Field(..., description="Name of the project")
    description: Optional[str] = Field(None, description="Overview of the project goals and tools used")
    url: Optional[str] = Field(None, description="Link to project repository or website")
    start_date: Optional[str] = Field(None, description="Project start date")
    end_date: Optional[str] = Field(None, description="Project end date")


class AwardItem(BaseModel):
    """Honor, award, or professional recognition."""
    title: str = Field(..., description="Title of the award")
    issuer: Optional[str] = Field(None, description="Organization that issued the award")
    issue_date: Optional[str] = Field(None, description="Date the award was received")
    description: Optional[str] = Field(None, description="Explanation or reasoning for the award")


class CompanyDetails(BaseModel):
    """Details of the candidate's current or associated employer."""
    name: Optional[str] = Field(None, description="Employer name")
    website: Optional[str] = Field(None, description="Employer website URL")
    size: Optional[str] = Field(None, description="Company range size (e.g. 51-200)")
    industry: Optional[str] = Field(None, description="Primary industry classification")
    domain: Optional[str] = Field(None, description="Company domain name")
    linkedin_url: Optional[str] = Field(None, description="Company LinkedIn profile URL")


class SchemaMetadata(BaseModel):
    """Extra tracking and lifecycle data for internal agent operations."""
    source: str = Field(..., description="Underlying provider source (e.g. apollo, proxycurl)")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="UTC Timestamp of extraction")
    raw_data: Dict = Field(default_factory=dict, description="Raw unmodified response payload from provider")
    field_sources: Dict[str, str] = Field(default_factory=dict, description="Tracks the source provider for each profile field")
    enriched: bool = Field(False, description="Whether the candidate profile has undergone enrichment")
    confidence: float = Field(1.0, description="Overall profile data confidence score (0.0 to 1.0)")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="UTC Timestamp of the last profile modification")
    apollo_person_id: Optional[str] = Field(None, description="Apollo Person ID")
    apollo_organization_id: Optional[str] = Field(None, description="Apollo Organization ID")


class CandidateProfile(BaseModel):
    """Canonical, provider-agnostic representation of a candidate's complete profile."""
    basic_info: BasicInfo = Field(..., description="Core contact and identity information")
    summary: Optional[ProfileSummary] = Field(None, description="Executive bio/summary")
    experience: List[ExperienceItem] = Field(default_factory=list, description="List of professional experience items")
    skills: List[SkillItem] = Field(default_factory=list, description="List of key skills")
    education: List[EducationItem] = Field(default_factory=list, description="List of education history entries")
    certifications: List[CertificationItem] = Field(default_factory=list, description="List of professional certifications")
    languages: List[LanguageItem] = Field(default_factory=list, description="List of languages spoken")
    projects: List[ProjectItem] = Field(default_factory=list, description="List of significant projects")
    awards: List[AwardItem] = Field(default_factory=list, description="List of awards received")
    company: Optional[CompanyDetails] = Field(None, description="Details of current primary employer")
    metadata: SchemaMetadata = Field(..., description="Tracking metadata")

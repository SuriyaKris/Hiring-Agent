"""Rule-Based Enrichment Planner for Candidate Sourcing."""

from abc import ABC, abstractmethod
from typing import List, Optional, Set, Dict
from schemas.candidate_profile import CandidateProfile
from services.profile_validator import ValidationResult
from schemas.enrichment_plan import EnrichmentPlan
from providers.registry import AVAILABLE_PROVIDERS


def get_available_providers(profile: CandidateProfile) -> Set[str]:
    """Helper to determine which enrichment providers are currently eligible/available."""
    available = set()
    raw_data = profile.metadata.raw_data or {}
    
    if profile.basic_info.linkedin_url:
        available.add("Playwright")
    if raw_data.get("has_resume") or raw_data.get("resume_path"):
        available.add("Resume")
    if profile.basic_info.github_url:
        available.add("GitHub")
        
    current_job = profile.experience[0] if profile.experience else None
    if (profile.company and profile.company.name) or (current_job and current_job.company_name):
        available.add("Company")
        
    return available


class BaseEnrichmentRule(ABC):
    """Abstract Base Class for independent enrichment scheduling rules."""

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Return the name of the rule."""
        pass

    @abstractmethod
    async def evaluate(self, profile: CandidateProfile, missing_fields: Set[str], reliability_metrics: Dict[str, Dict[str, float]]) -> Optional[str]:
        """Determine if this rule matches the profile and missing fields.

        Returns:
            The name of the provider to run, or None.
        """
        pass


class PlaywrightRule(BaseEnrichmentRule):
    """Rule 1: Run Playwright scraper if profile details are missing and LinkedIn URL exists."""

    @property
    def rule_name(self) -> str:
        return "PlaywrightScraperRule"

    async def evaluate(self, profile: CandidateProfile, missing_fields: Set[str], reliability_metrics: Dict[str, Dict[str, float]]) -> Optional[str]:
        targets = {"Summary", "Skills", "Experience", "Experience Description", "Education", "Certifications"}
        missing_targets = targets.intersection(missing_fields)
        if not missing_targets or not profile.basic_info.linkedin_url:
            return None

        # Compare confidence levels across all other available providers to optimize routing
        available = get_available_providers(profile)
        playwright_rel = reliability_metrics.get("Playwright", {})

        valid_targets = []
        for field in missing_targets:
            playwright_conf = playwright_rel.get(field, 1.0)
            
            # Check if any other available provider can fulfill this field with higher accuracy
            has_better_alternative = False
            for other in available:
                if other == "Playwright":
                    continue
                other_conf = reliability_metrics.get(other, {}).get(field, 0.0)
                if other_conf > playwright_conf:
                    has_better_alternative = True
                    break
            
            if has_better_alternative:
                continue
            valid_targets.append(field)

        if valid_targets:
            return "Playwright"
        return None


class ResumeRule(BaseEnrichmentRule):
    """Rule 2: Run Resume Parser if projects/experience are missing and a resume is present."""

    @property
    def rule_name(self) -> str:
        return "ResumeParserRule"

    async def evaluate(self, profile: CandidateProfile, missing_fields: Set[str], reliability_metrics: Dict[str, Dict[str, float]]) -> Optional[str]:
        targets = {"Experience", "Experience Description", "Projects", "Education", "Certifications", "Awards", "Skills"}
        raw_data = profile.metadata.raw_data or {}
        has_resume = raw_data.get("has_resume") or raw_data.get("resume_path")
        if not targets.intersection(missing_fields) or not has_resume:
            return None

        # Check alternative providers' confidences
        available = get_available_providers(profile)
        resume_rel = reliability_metrics.get("Resume", {})

        valid_targets = []
        for field in targets.intersection(missing_fields):
            resume_conf = resume_rel.get(field, 1.0)
            has_better_alternative = False
            for other in available:
                if other == "Resume":
                    continue
                other_conf = reliability_metrics.get(other, {}).get(field, 0.0)
                if other_conf > resume_conf:
                    has_better_alternative = True
                    break
            if has_better_alternative:
                continue
            valid_targets.append(field)

        if valid_targets:
            return "Resume"
        return None


class GitHubRule(BaseEnrichmentRule):
    """Rule 3: Run GitHub query if projects/languages are missing and GitHub URL exists."""

    @property
    def rule_name(self) -> str:
        return "GitHubQueryRule"

    async def evaluate(self, profile: CandidateProfile, missing_fields: Set[str], reliability_metrics: Dict[str, Dict[str, float]]) -> Optional[str]:
        targets = {"Projects", "Languages", "Skills"}
        if not targets.intersection(missing_fields) or not profile.basic_info.github_url:
            return None

        available = get_available_providers(profile)
        github_rel = reliability_metrics.get("GitHub", {})

        valid_targets = []
        for field in targets.intersection(missing_fields):
            github_conf = github_rel.get(field, 1.0)
            has_better_alternative = False
            for other in available:
                if other == "GitHub":
                    continue
                other_conf = reliability_metrics.get(other, {}).get(field, 0.0)
                if other_conf > github_conf:
                    has_better_alternative = True
                    break
            if has_better_alternative:
                continue
            valid_targets.append(field)

        if valid_targets:
            return "GitHub"
        return None


class CompanyRule(BaseEnrichmentRule):
    """Rule 4: Run Company firmographics if Company Details are missing."""

    @property
    def rule_name(self) -> str:
        return "CompanyFirmographicsRule"

    async def evaluate(self, profile: CandidateProfile, missing_fields: Set[str], reliability_metrics: Dict[str, Dict[str, float]]) -> Optional[str]:
        if "Company" in missing_fields:
            # Requires at least a company name to enrich it
            current_job = profile.experience[0] if profile.experience else None
            if (profile.company and profile.company.name) or (current_job and current_job.company_name):
                return "Company"
        return None


# Default reliability mapping matching validation accuracies
DEFAULT_RELIABILITY_METRICS = {
    "Playwright": {
        "Summary": 0.95,
        "Experience": 0.91,
        "Skills": 0.45,  # Low reliability (< 50%)
        "Education": 0.88,
        "Certifications": 0.85
    },
    "Resume": {
        "Experience": 0.95,
        "Skills": 0.90,
        "Education": 0.92,
        "Certifications": 0.90,
        "Projects": 0.88,
        "Awards": 0.85
    },
    "GitHub": {
        "Projects": 0.95,
        "Languages": 0.98,
        "Skills": 0.80
    },
    "Company": {
        "Company": 0.95
    }
}


class EnrichmentPlanner:
    """Orchestrates candidate enrichment scheduling via independent execution rules."""

    def __init__(
        self,
        rules: List[BaseEnrichmentRule] = None,
        reliability_metrics: Optional[Dict[str, Dict[str, float]]] = None
    ):
        self.rules = rules or [
            PlaywrightRule(),
            ResumeRule(),
            GitHubRule(),
            CompanyRule(),
        ]
        self.reliability_metrics = reliability_metrics or DEFAULT_RELIABILITY_METRICS
        self.provider_by_name = {p.provider_name: p for p in AVAILABLE_PROVIDERS}

    async def plan(self, profile: CandidateProfile, validation_result: ValidationResult) -> EnrichmentPlan:
        """Evaluate candidate profile validation discrepancies and generate an EnrichmentPlan.

        Args:
            profile: The candidate profile.
            validation_result: The validation result indicating missing areas.

        Returns:
            An EnrichmentPlan listing scheduled providers and estimated metrics.
        """
        missing_fields = set(validation_result.missing_fields)
        
        # Retrieve already executed providers to prevent re-scheduling
        raw_data = profile.metadata.raw_data or {}
        executed_providers = set(raw_data.get("executed_providers", []))

        scheduled_providers = []
        reasons = []

        # Evaluate all rules independently, passing current reliability metrics
        for rule in self.rules:
            provider_name = await rule.evaluate(profile, missing_fields, self.reliability_metrics)
            if provider_name:
                # Ensure the provider is registered, not already run, and not already scheduled
                if (provider_name in self.provider_by_name 
                        and provider_name not in executed_providers 
                        and provider_name not in scheduled_providers):
                    scheduled_providers.append(provider_name)
                    
                    # Log covered fields for reasoning visibility
                    prov = self.provider_by_name[provider_name]
                    covered = prov.supported_fields.intersection(missing_fields)
                    reasons.append(f"Running {provider_name} due to missing: {', '.join(covered)}")

        # Calculate estimated cost and execution time by querying provider parameters
        total_cost = 0.0
        total_time = 0.0
        for name in scheduled_providers:
            prov = self.provider_by_name[name]
            total_cost += prov.cost
            total_time += prov.estimated_time

        # Calculate field confidences
        field_confidences = {}
        for name in scheduled_providers:
            # Note: Playwright maps to "Playwright" provider name
            # Resume maps to "Resume", etc.
            prov = self.provider_by_name[name]
            # Intersect missing fields with supported fields of the provider
            covered = prov.supported_fields.intersection(missing_fields)
            for f in covered:
                field_confidences[f] = self.reliability_metrics.get(name, {}).get(f, 1.0)

        reason_str = " | ".join(reasons) if reasons else "No enrichment needed."

        return EnrichmentPlan(
            providers=scheduled_providers,
            estimated_cost=round(total_cost, 4),
            estimated_time=total_time,
            reason=reason_str,
            field_confidences=field_confidences
        )

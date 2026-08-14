"""Centralized Provider Registry for Candidate Enrichment."""

from providers.apollo_provider import ApolloProvider
from providers.resume_provider import ResumeProvider
from providers.github_provider import GitHubProvider
from providers.company_provider import CompanyProvider

AVAILABLE_PROVIDERS = [
    ApolloProvider(),
    ResumeProvider(),
    GitHubProvider(),
    CompanyProvider(),
]

"""Apollo Discovery Agent — Sourcing candidates via Apollo.io Mixed People search API."""

from typing import List
from loguru import logger
from models.schemas import JDSearchSpec
from services.apollo_service import apollo_search
from schemas.candidate_profile import CandidateProfile, BasicInfo, SchemaMetadata


class ApolloSearchProvider:
    """Orchestrates candidate searches against the Apollo API endpoints."""

    @property
    def provider_name(self) -> str:
        return "ApolloSearch"

    async def search_profiles(self, spec: JDSearchSpec, max_results: int = 25) -> List[CandidateProfile]:
        """Search Apollo and map responses into canonical CandidateProfile schemas."""
        logger.info(f"[Apollo Discovery Agent] Running sourcing search, max_results={max_results}")
        
        try:
            legacy_profiles = await apollo_search(spec, max_results=max_results)
        except Exception as e:
            logger.error(f"[Apollo Discovery Agent] Apollo search failed: {e}")
            return []

        # Import mappers to ensure they register their normalizers in the enrichment registry
        import providers.apollo_mapper
        from services.candidate_enrichment import CandidateEnrichmentService
        enricher_service = CandidateEnrichmentService()

        profiles = []
        for lp in legacy_profiles:
            # Map raw details to the CandidateProfile model
            raw = lp.raw_data or {}
            
            # Extract identifiers
            person_id = raw.get("id")
            org_id = raw.get("organization_id") or (raw.get("organization") or {}).get("id")

            try:
                profile = enricher_service.enrich(raw, "apollo")
                if not profile.basic_info.email and lp.email:
                    profile.basic_info.email = lp.email
                if not profile.basic_info.phone and lp.phone:
                    profile.basic_info.phone = lp.phone
                
                profile.metadata.apollo_person_id = person_id
                profile.metadata.apollo_organization_id = org_id
            except Exception as e:
                logger.error(f"[Apollo Discovery Agent] Sourcing normalization failed: {e}")
                # Fallback to manual mapping
                profile = CandidateProfile(
                    basic_info=BasicInfo(
                        first_name=raw.get("first_name"),
                        last_name=raw.get("last_name"),
                        full_name=lp.full_name,
                        headline=lp.headline,
                        location=lp.location,
                        linkedin_url=lp.linkedin_url,
                        email=lp.email,
                        phone=lp.phone,
                    ),
                    metadata=SchemaMetadata(
                        source="apollo",
                        raw_data=raw,
                        apollo_person_id=person_id,
                        apollo_organization_id=org_id,
                    )
                )
            profiles.append(profile)

        logger.info(f"[Apollo Discovery Agent] Successfully sourced {len(profiles)} profiles.")
        return profiles

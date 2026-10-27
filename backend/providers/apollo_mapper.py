"""Apollo raw JSON mapper for Canonical Candidate Schema."""

from datetime import datetime
from typing import Any, Dict
from services.candidate_enrichment import BaseNormalizer, register_normalizer


class ApolloNormalizer(BaseNormalizer):
    """Normalizes candidate profile payloads returned from Apollo.io API."""

    def normalize(self, person: Dict[str, Any]) -> Dict[str, Any]:
        employment_history = person.get("employment_history", [])
        current_job = employment_history[0] if employment_history else {}

        # 1. Map Basic Info
        last_name = person.get("last_name") or person.get("last_name_obfuscated") or ""
        full_name = person.get("name") or f"{person.get('first_name', '')} {last_name}".strip() or "Unknown"
        title = person.get("title") or person.get("headline") or ""

        basic_info = {
            "first_name": person.get("first_name") or None,
            "last_name": person.get("last_name") or person.get("last_name_obfuscated") or None,
            "full_name": full_name,
            "headline": person.get("headline") or title or None,
            "location": f"{person.get('city', '')}, {person.get('state', '')}, {person.get('country', '')}".strip(", ") or None,
            "linkedin_url": person.get("linkedin_url") or (f"https://linkedin.com/in/{person.get('id', '')}" if person.get("id") else None),
            "email": person.get("email") or None,
            "phone": person.get("phone_numbers", [{}])[0].get("sanitized_number") if person.get("phone_numbers") else None,
            "twitter_url": person.get("twitter_url") or None,
            "github_url": person.get("github_url") or None,
            "portfolio_url": None,
        }

        # 2. Map Profile Summary
        summary = {
            "about": person.get("headline") or title or None,
            "tagline": person.get("headline") or title or None,
        }

        # 3. Map Experience History
        experience_items = []
        for exp in employment_history:
            experience_items.append({
                "company_name": exp.get("organization_name") or "",
                "title": exp.get("title") or "",
                "start_date": exp.get("start_date") or None,
                "end_date": exp.get("end_date") or None,
                "description": exp.get("description") or None,
                "location": f"{exp.get('city', '')}, {exp.get('state', '')}".strip(", ") or None,
                "employment_type": None,
                "is_current": exp.get("is_current") or exp.get("current") or False,
            })

        company_name = person.get("organization_name") or person.get("organization", {}).get("name") or current_job.get("organization_name") or ""
        if not experience_items and (title or company_name):
            experience_items.append({
                "company_name": company_name,
                "title": title,
                "start_date": None,
                "end_date": None,
                "description": None,
                "location": f"{person.get('city', '')}, {person.get('state', '')}".strip(", ") or None,
                "employment_type": None,
                "is_current": True,
            })

        # 4. Map Skills
        raw_skills = person.get("skills", [])
        skills_items = []
        for s in raw_skills:
            if isinstance(s, dict):
                skills_items.append({
                    "name": s.get("name") or "",
                    "category": s.get("category") or None,
                })
            elif isinstance(s, str):
                skills_items.append({
                    "name": s,
                    "category": None,
                })

        # 5. Map Education
        education_history = person.get("education_history", [])
        education_items = []
        for edu in education_history:
            education_items.append({
                "school_name": edu.get("school_name") or edu.get("school") or "",
                "degree": edu.get("degree") or edu.get("degree_name") or None,
                "field_of_study": edu.get("degree_major") or edu.get("major") or None,
                "start_date": edu.get("start_date") or None,
                "end_date": edu.get("end_date") or None,
                "description": edu.get("description") or None,
            })

        # 6. Map Company Details
        company_name = person.get("organization_name") or person.get("organization", {}).get("name") or current_job.get("organization_name")
        company = None
        if company_name:
            emp_count = person.get("organization", {}).get("estimated_num_employees")
            company = {
                "name": company_name,
                "website": person.get("organization", {}).get("website") or None,
                "size": str(emp_count) if emp_count is not None else None,
                "industry": person.get("organization", {}).get("industry") or None,
                "domain": person.get("organization", {}).get("primary_domain") or None,
                "linkedin_url": person.get("organization", {}).get("linkedin_url") or None,
            }

        # 7. Map Metadata
        metadata = {
            "source": "apollo",
            "extracted_at": datetime.utcnow().isoformat(),
            "raw_data": person,
        }

        return {
            "basic_info": basic_info,
            "summary": summary,
            "experience": experience_items,
            "skills": skills_items,
            "education": education_items,
            "certifications": [],
            "languages": [],
            "projects": [],
            "awards": [],
            "company": company,
            "metadata": metadata,
        }


# Register Apollo mapper on load
register_normalizer("apollo", ApolloNormalizer())

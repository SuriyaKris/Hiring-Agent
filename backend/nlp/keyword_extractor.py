"""
Keyword Extractor — Backup heuristic extraction and normalization utilities.
Used to extract target titles, personas, and territories from raw Job Description text if they are missing from the parsed spec.
"""

import re
from nlp.title_taxonomy import REGION_MAP


def clean_text(text: str) -> str:
    """Helper to lowercase and strip non-alphanumeric characters."""
    if not text:
        return ""
    return " ".join(re.sub(r'[^a-z0-9\s]', ' ', text.lower()).split())


def extract_backup_titles(jd_text: str) -> list[str]:
    """
    Search JD text for common job titles across diverse domains as a fallback.
    """
    if not jd_text:
        return []
    
    # Check for explicit Role/Title line in JD
    header_patterns = [
        r'(?:role|title|position|job\s*title|looking\s*for\s*(?:a|an)?)\s*[:\-–]\s*([^\n\r,]+)',
        r'(?:hiring\s*(?:a|an)?)\s+([A-Z][A-Za-z0-9\s/\-–]+?)(?:\s+(?:to|for|at|in)\b|\.|\n)',
    ]
    extracted_from_header = []
    for pattern in header_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            candidate_title = match.group(1).strip()
            if len(candidate_title) > 2 and len(candidate_title) < 60:
                # Clean delimiters
                cleaned = re.split(r'[-–|]', candidate_title)[0].strip()
                if cleaned:
                    extracted_from_header.append(cleaned.title())

    common_titles = [
        # Engineering / Tech
        "software engineer", "frontend engineer", "backend engineer", "full stack engineer",
        "full stack developer", "frontend developer", "backend developer", "devops engineer",
        "site reliability engineer", "cloud architect", "data engineer", "data scientist",
        "machine learning engineer", "ai engineer", "solutions architect", "security engineer",
        "mobile developer", "ios developer", "android developer", "qa engineer",
        "python developer", "java developer", "react developer", "node developer",
        "golang developer", "ruby developer", "c++ developer", "embedded engineer",
        # Product & Design
        "product manager", "product designer", "ui ux designer", "ux designer", "ui designer",
        "technical program manager", "project manager", "scrum master",
        # Sales & Marketing
        "account executive", "inside sales", "sales executive", "sales representative",
        "sales development representative", "business development representative",
        "sdr", "bdr", "growth marketing manager", "marketing manager", "product marketing manager",
        "customer success manager", "account manager", "sales director", "head of sales",
        # Operations & Finance
        "financial analyst", "operations manager", "hr manager", "talent acquisition specialist",
    ]
    
    found = []
    jd_clean = clean_text(jd_text)
    for title in common_titles:
        pattern = r'\b' + re.escape(title) + r'\b'
        if re.search(pattern, jd_clean):
            found.append(title.title())
            
    all_titles = extracted_from_header + [t for t in found if t not in extracted_from_header]
    return list(dict.fromkeys(all_titles))


def extract_backup_persona(jd_text: str) -> str:
    """
    Look for keywords suggesting expected persona level.
    """
    if not jd_text:
        return "Professional"
        
    jd_clean = clean_text(jd_text)
    
    titles = extract_backup_titles(jd_text)
    primary_title = titles[0] if titles else "Candidate"
    
    if any(k in jd_clean for k in ["vp", "vice president", "director", "head of"]):
        return f"Executive / {primary_title}"
    if any(k in jd_clean for k in ["principal", "lead", "staff", "architect"]):
        return f"Lead / {primary_title}"
    if any(k in jd_clean for k in ["senior", "sr", "experienced"]):
        return f"Senior / {primary_title}"
    if any(k in jd_clean for k in ["entry", "junior", "jr", "associate", "intern"]):
        return f"Entry / {primary_title}"
    if any(k in jd_clean for k in ["mid", "intermediate"]):
        return f"Mid-Level / {primary_title}"
        
    return primary_title


def extract_backup_territory(jd_text: str) -> str:
    """
    Find explicit location/city/country in JD text preserving city-level precision.
    Returns specific city/country (e.g., 'Bangalore, India', 'London, UK') or 'Remote', or empty string.
    """
    if not jd_text:
        return ""

    # 1. Check explicit Location header in JD
    location_patterns = [
        r'(?:location|job\s*location|based\s*in|office\s*location|work\s*location)\s*[:\-–]\s*([^\n\r]+)',
    ]
    for pattern in location_patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            loc_val = match.group(1).strip()
            # Clean common parentheticals like "(Hybrid)", "(Onsite)", "(Preferred)"
            loc_val = re.sub(r'\s*\([^)]*\)', '', loc_val).strip()
            if loc_val and len(loc_val) < 80:
                # If remote is explicitly in the location line
                if "remote" in loc_val.lower() or "anywhere" in loc_val.lower() or "wfh" in loc_val.lower():
                    # Check if region-specific remote
                    for region, config in REGION_MAP.items():
                        if any(name in loc_val.lower() for name in config["names"]) or region in loc_val.lower():
                            return f"{region.title()} (Remote)"
                    return "Remote"
                return loc_val

    jd_clean = clean_text(jd_text)

    # 2. Check specific city names first to preserve city precision
    for region, config in REGION_MAP.items():
        for name in config["names"]:
            # If a specific city / sub-region is found (not just the broad country name)
            if name != region and name in jd_clean:
                # e.g., 'bangalore' -> 'Bangalore, India'
                city_name = name.title()
                country_name = region.title()
                if country_name.lower() in ("united states", "united kingdom", "india", "canada", "australia", "germany", "france"):
                    return f"{city_name}, {country_name}"
                return city_name

    # 3. Check country / broad region names
    for region, config in REGION_MAP.items():
        if region in jd_clean:
            return region.title()

    # 4. Check if remote
    if "remote" in jd_clean or "work from home" in jd_clean or "anywhere" in jd_clean:
        return "Remote"

    return ""


def extract_backup_geo_keywords(jd_text: str) -> list[str]:
    """
    Extract a comprehensive list of geographic search keywords (city, alternate names, country).
    """
    if not jd_text:
        return []

    jd_clean = clean_text(jd_text)
    keywords = []

    # Check for known city/country names in taxonomy
    for region, config in REGION_MAP.items():
        matched_region = False
        for name in config["names"]:
            if name in jd_clean:
                keywords.append(name.title())
                matched_region = True
        if matched_region or region in jd_clean:
            if region.title() not in keywords:
                keywords.append(region.title())

    # Add synonyms for major tech hubs
    if any(k.lower() in ("bangalore", "bengaluru") for k in keywords):
        if "Bangalore" not in keywords:
            keywords.insert(0, "Bangalore")
        if "Bengaluru" not in keywords:
            keywords.insert(1, "Bengaluru")
        if "India" not in keywords:
            keywords.append("India")

    if not keywords and ("remote" in jd_clean or "anywhere" in jd_clean):
        keywords = ["Remote"]

    return list(dict.fromkeys(keywords))

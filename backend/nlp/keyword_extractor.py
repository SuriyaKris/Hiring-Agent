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
    Attempt to find explicit region or country names in JD text as a fallback.
    Returns 'Remote' if remote is stated, or the matched country/city, or empty string if none.
    """
    if not jd_text:
        return ""
        
    jd_clean = clean_text(jd_text)
    
    # Check regions in region map
    for region, config in REGION_MAP.items():
        if region in jd_clean or any(name in jd_clean for name in config["names"]):
            return region.title()
            
    # Check if remote
    if "remote" in jd_clean or "work from home" in jd_clean or "anywhere" in jd_clean:
        return "Remote"
        
    return ""

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
    Search JD text for common sales titles as a fallback.
    """
    if not jd_text:
        return []
    
    common_titles = [
        "account executive", "inside sales", "sales executive", "sales representative",
        "sales development representative", "business development representative",
        "sdr", "bdr", "ae", "inside sales representative", "inside sales ae",
        "enterprise account executive", "smb account executive", "mid-market account executive"
    ]
    
    found = []
    jd_clean = clean_text(jd_text)
    for title in common_titles:
        # Use word boundaries
        pattern = r'\b' + re.escape(title) + r'\b'
        if re.search(pattern, jd_clean):
            found.append(title.title())
            
    return list(set(found))

def extract_backup_persona(jd_text: str) -> str:
    """
    Look for keywords suggesting expected persona level.
    """
    if not jd_text:
        return ""
        
    jd_clean = clean_text(jd_text)
    
    if any(k in jd_clean for k in ["enterprise", "strategic", "vp", "director", "head of", "senior ae"]):
        return "Senior / Account Executive - Enterprise"
    if any(k in jd_clean for k in ["entry", "junior", "sdr", "bdr", "smb", "inside sales"]):
        return "Entry / Account Executive - SMB"
    if any(k in jd_clean for k in ["mid market", "midmarket", "commercial"]):
        return "Mid-Market Account Executive"
        
    return "Account Executive"

def extract_backup_territory(jd_text: str) -> str:
    """
    Attempt to find region names in JD text as a fallback.
    """
    if not jd_text:
        return ""
        
    jd_clean = clean_text(jd_text)
    
    # Check regions in region map
    for region, aliases in REGION_MAP.items():
        if region in jd_clean or any(alias in jd_clean for alias in aliases):
            return region.title()
            
    # Default fallback
    if "remote" in jd_clean:
        return "Remote"
        
    return "United States"

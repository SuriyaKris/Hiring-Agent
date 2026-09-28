"""
Title Taxonomy and Regional Matching Constants/Ladders.
Used by title fuzzy matching and territory validation.
"""

# Fuzzy match threshold for token matching (scale 0-100)
FUZZY_MATCH_THRESHOLD = 75.0

# Region alias mapping for geographic expansions (casing insensitive)
# Partitioned into:
# - 'names': full city/region names (safe for substring matching)
# - 'codes': 2-letter state/country codes (require exact word/token matching)
# Ambiguity warning: Standalone 'la' code matches Louisiana state and Los Angeles city abbreviations.
# To prevent false positives in California match, we place 'la' code strictly in the 'south' (Louisiana)
# region rather than leaving it in 'california'.
REGION_MAP = {
    "california": {
        "names": ["california", "los angeles", "san francisco", "san diego", "silicon valley"],
        "codes": ["ca", "sf"]
    },
    "west coast": {
        "names": ["washington", "oregon", "seattle", "portland", "west coast", "pacific northwest", "pnw"],
        "codes": ["wa", "or"]
    },
    "east coast": {
        "names": ["new york", "new jersey", "massachusetts", "boston", "washington dc", "east coast", "atlantic", "mid-atlantic"],
        "codes": ["ny", "nj", "ma", "dc"]
    },
    "texas": {
        "names": ["texas", "austin", "dallas", "houston", "san antonio"],
        "codes": ["tx"]
    },
    "midwest": {
        "names": ["illinois", "chicago", "ohio", "michigan", "detroit", "cleveland", "minneapolis", "minnesota"],
        "codes": ["il", "oh", "mi", "mn"]
    },
    "mountain": {
        "names": ["colorado", "denver", "utah", "salt lake city", "arizona", "phoenix"],
        "codes": ["co", "ut", "az"]
    },
    "south": {
        "names": ["georgia", "atlanta", "north carolina", "charlotte", "florida", "miami", "orlando", "louisiana", "new orleans"],
        "codes": ["ga", "nc", "fl", "la"]
    },
    "united states": {
        "names": ["united states", "united states of america", "america", "remote us", "us remote"],
        "codes": ["us", "usa"]
    },
    "united kingdom": {
        "names": ["united kingdom", "great britain", "england", "scotland", "wales", "london", "manchester", "birmingham"],
        "codes": ["uk", "gb"]
    },
    "europe": {
        "names": ["europe", "european union", "germany", "berlin", "munich", "france", "paris", "netherlands", "amsterdam", "ireland", "dublin", "spain", "madrid", "barcelona"],
        "codes": ["eu", "de", "fr", "nl", "ie", "es"]
    },
    "india": {
        "names": ["india", "bengaluru", "bangalore", "hyderabad", "mumbai", "delhi", "pune", "chennai", "noida", "gurgaon"],
        "codes": ["in"]
    },
    "canada": {
        "names": ["canada", "toronto", "vancouver", "montreal", "ottawa", "calgary"],
        "codes": ["ca"]
    },
    "australia": {
        "names": ["australia", "sydney", "melbourne", "brisbane", "perth"],
        "codes": ["au"]
    }
}


# Semantic similarity calibration thresholds (floors and ceilings)
# about_semantic_sim thresholds: raw cosine similarity runs 0.13 to 0.65
ABOUT_SEMANTIC_SIM_FLOOR = 0.20
ABOUT_SEMANTIC_SIM_CEILING = 0.60

# experience_semantic_sim thresholds: raw cosine similarity runs 0.25 to 0.67
EXP_SEMANTIC_SIM_FLOOR = 0.30
EXP_SEMANTIC_SIM_CEILING = 0.55

# Multiplier for relevant experience years point scaling
RELEVANT_EXP_MULTIPLIER = 5.0


def clean_role_name_for_search(role_name: str | None) -> list[str]:
    """
    Extract the exact and cleaned role names (removing qualifiers like location or regional tags)
    to query Apollo mixed people search effectively.
    """
    if not role_name:
        return []
    role_name_clean = role_name.strip()
    if not role_name_clean:
        return []
        
    parts = [role_name_clean]
    
    # Split by common delimiters: ' - ', ' – ', ' | '
    delimiters = [" - ", " – ", " | ", "-", "–", "|"]
    for d in delimiters:
        if d in role_name_clean:
            subparts = role_name_clean.split(d)
            if subparts:
                first_part = subparts[0].strip()
                if first_part:
                    parts.append(first_part)
            break
            
    # Return unique parts in order
    seen = set()
    unique = []
    for p in parts:
        p_lower = p.lower()
        if p_lower not in seen:
            seen.add(p_lower)
            unique.append(p)
    return unique




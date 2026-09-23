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
    # Normalize unicode quotes and dashes
    normalized = text.replace('’', "'").replace('‘', "'").replace('–', '-').replace('—', '-')
    return " ".join(re.sub(r'[^a-z0-9\s]', ' ', normalized.lower()).split())


def extract_backup_titles(jd_text: str, role_name: str = "") -> list[str]:
    """
    Search JD text for common job titles across diverse domains as a fallback.
    """
    extracted_from_header = []
    
    # If role_name is explicitly provided, place it first
    if role_name and role_name.strip() and role_name.strip().lower() not in ("default", "untitled", "role", "job", "position"):
        extracted_from_header.append(role_name.strip().title())

    if not jd_text:
        return extracted_from_header

    # Normalize unicode characters
    normalized_jd = jd_text.replace('’', "'").replace('‘', "'").replace('–', '-').replace('—', '-')
    
    # Check for explicit Role/Title line or header in JD
    header_patterns = [
        r'(?:we(?:\'re|\s+are)\s+hiring|hiring|role|title|position|job\s*title)\s*[:\-–]\s*([A-Za-z0-9\s/\-–]+?)(?:\s*(?:\||\(|location:|experience:|company:|benefits:|\n|\r|\Z))',
        r'(?:looking\s*for\s*(?:a|an)?)\s+([A-Za-z0-9\s/\-–]+?)(?:\s+(?:who|to|for|at|in|with)\b|\.|\n)',
        r'(?:role|position)\s*overview\s*[:\-–]?\s*(?:we(?:\'re|\s+are)\s+looking\s+for\s+(?:a|an)?\s+)?([A-Za-z0-9\s/\-–]+?)(?:\s+(?:who|to|for|at|in|with)\b|\.|\n)',
    ]
    for pattern in header_patterns:
        match = re.search(pattern, normalized_jd, re.IGNORECASE)
        if match:
            candidate_title = match.group(1).strip()
            # Clean common words like "hands-on", "experienced"
            candidate_title = re.sub(r'^(?:hands-on|experienced|senior|lead)\s+', '', candidate_title, flags=re.IGNORECASE).strip() or candidate_title
            if len(candidate_title) > 2 and len(candidate_title) < 60:
                cleaned = re.split(r'[-–|]', candidate_title)[0].strip()
                if cleaned and cleaned.lower() not in [t.lower() for t in extracted_from_header]:
                    extracted_from_header.append(cleaned.title())

    common_titles = [
        # HR, People Operations & Talent
        "hr lead", "hr manager", "human resources lead", "human resources manager", "head of hr",
        "head of people", "vp of hr", "director of hr", "people operations lead", "people operations manager",
        "talent acquisition lead", "talent acquisition manager", "talent acquisition specialist",
        "hr business partner", "hrbp", "hr operations lead", "hr operations manager", "hr generalist",
        # Engineering / Tech
        "software engineer", "frontend engineer", "backend engineer", "full stack engineer",
        "full stack developer", "frontend developer", "backend developer", "devops engineer",
        "site reliability engineer", "cloud architect", "data engineer", "data scientist",
        "machine learning engineer", "ai engineer", "solutions architect", "security engineer",
        "mobile developer", "ios developer", "android developer", "qa engineer",
        "python developer", "java developer", "react developer", "node developer",
        "golang developer", "ruby developer", "c++ developer", "embedded engineer",
        # Planning, Supply Chain & Operations
        "demand and capacity planner", "demand planner", "capacity planner", "supply chain planner",
        "supply chain analyst", "inventory planner", "operations planner", "production planner",
        "resource planner", "workforce planner", "logistics manager", "supply chain manager",
        "capacity planning specialist", "demand planning specialist",
        # Product & Design
        "product manager", "product designer", "ui ux designer", "ux designer", "ui designer",
        "technical program manager", "project manager", "scrum master",
        # Sales, Marketing & Customer Success
        "account executive", "inside sales", "sales executive", "sales representative",
        "sales development representative", "business development representative",
        "sdr", "bdr", "growth marketing manager", "marketing manager", "product marketing manager",
        "customer success manager", "account manager", "sales director", "head of sales",
        # Operations, Analytics & Finance
        "data analyst", "business analyst", "business intelligence developer", "operations analyst",
        "financial analyst", "operations manager", "fp&a analyst", "fp&a manager", "risk analyst",
        "delivery manager", "program manager",
    ]
    
    found = []
    jd_clean = clean_text(normalized_jd)
    for title in common_titles:
        pattern = r'\b' + re.escape(title) + r'\b'
        if re.search(pattern, jd_clean):
            found.append(title.title())
            
    all_titles = extracted_from_header + [t for t in found if t.lower() not in [x.lower() for x in extracted_from_header]]
    return list(dict.fromkeys(all_titles))


def extract_backup_skills(jd_text: str) -> list[str]:
    """
    Extract technical and domain skills from JD text when LLM output is unavailable.
    Searches known skills taxonomy and parses bullet points in requirements/skills sections.
    """
    if not jd_text:
        return []

    KNOWN_SKILLS = [
        # HR, People & Operations
        "HR Operations", "Payroll Coordination", "Payroll Management", "Statutory Compliance",
        "Labor Law Compliance", "Provident Fund (PF)", "PF", "ESI", "Professional Tax (PT)", "PT",
        "Shops & Establishment Act", "Labor Laws", "Employee Relations", "Onboarding", "Offboarding",
        "Exits", "Full & Final Settlement", "F&F", "HRMS", "Workforce Metrics", "Billability",
        "Utilization", "Bench Management", "Headcount Allocation", "Audit Readiness",
        "Investor Due Diligence", "Performance Management", "Talent Acquisition", "Employee Engagement",
        # Supply Chain & Planning
        "Demand Planning", "Capacity Planning", "Demand Forecasting", "Capacity Forecasting",
        "Resource Planning", "Resource Allocation", "Supply Chain Planning", "Supply Chain Management",
        "S&OP", "Sales and Operations Planning", "Inventory Management", "Production Scheduling",
        "Material Requirements Planning", "MRP", "Workforce Management", "Process Optimization",
        "Operations Research", "Vendor Management", "Logistics",
        # Analytics & Tools
        "Excel", "Advanced Excel", "VBA", "Power BI", "Tableau", "SQL", "Python", "R",
        "SAP", "SAP IBP", "SAP APO", "SAP ERP", "Anaplan", "Oracle SCM", "Oracle ERP",
        "Blue Yonder", "Kinaxis", "Manugistics", "JDA", "ServiceNow", "Salesforce", "Jira",
        # Programming & Frameworks
        "JavaScript", "TypeScript", "React", "Node.js", "Vue", "Angular", "Next.js",
        "Django", "FastAPI", "Flask", "Spring Boot", "Java", "C++", "C#", ".NET",
        "Golang", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "HTML", "CSS",
        # Cloud, DevOps & Databases
        "AWS", "GCP", "Google Cloud", "Azure", "Docker", "Kubernetes", "CI/CD", "Terraform",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Kafka", "RabbitMQ",
        "REST APIs", "GraphQL", "Microservices", "Git", "Linux",
        # Methodologies & General
        "Agile", "Scrum", "Kanban", "Six Sigma", "Lean", "Root Cause Analysis",
        "Data Analysis", "Statistical Modeling", "Predictive Modeling", "Risk Management"
    ]

    found_skills = []
    jd_clean = clean_text(jd_text)

    # 1. Match from taxonomy
    for skill in KNOWN_SKILLS:
        skill_clean = clean_text(skill)
        if re.search(r'\b' + re.escape(skill_clean) + r'\b', jd_clean):
            found_skills.append(skill)

    # 2. Extract bullet points or key responsibility lines
    # Insert newlines before section headers if text is single line
    segmented = re.sub(r'([a-z0-9)])\s+([A-Z][A-Za-z\s&–-]{2,30}:)', r'\1\n\2', jd_text)
    section_pattern = r'(?:key\s+responsibilities|responsibilities|requirements|qualifications|skills|who\s+should\s+apply|what\s+you(?:\'ll|\s+will)\s+do|must\s+have|nice\s+to\s+have)[:\n\r]+((?:[\s\S](?!role:|location:|experience:|company:|benefits:))*?)(?:\n\s*[A-Z][A-Za-z\s&–-]{2,30}:|\Z)'
    section_matches = re.findall(section_pattern, segmented, re.IGNORECASE)
    
    for section_text in section_matches:
        lines = [l.strip() for l in re.split(r'[\n\r•*]+|(?<=[a-z0-9])\s*[-–]\s*(?=[A-Z])', section_text) if l.strip()]
        for line_clean in lines:
            words = line_clean.split()
            if 1 <= len(words) <= 6 and not any(p in line_clean.lower() for p in ["years of", "experience in", "bachelor", "master", "degree", "looking for", "salary", "benefits"]):
                cleaned_phrase = re.sub(r'[,;.:]+$', '', line_clean).title()
                if cleaned_phrase and cleaned_phrase not in found_skills and len(cleaned_phrase) < 45:
                    found_skills.append(cleaned_phrase)

    return list(dict.fromkeys(found_skills))[:15]


def extract_backup_technologies(jd_text: str) -> list[str]:
    """Extract technology/tool identifiers mentioned in the JD."""
    if not jd_text:
        return []
    
    TECH_LIST = [
        "python", "java", "javascript", "typescript", "react", "node", "fastapi", "django",
        "flask", "docker", "kubernetes", "aws", "gcp", "azure", "postgresql", "mysql",
        "mongodb", "redis", "elasticsearch", "kafka", "sap", "anaplan", "oracle", "excel",
        "tableau", "power bi", "sql", "jira", "salesforce", "servicenow", "kinaxis", "jda"
    ]
    
    jd_clean = clean_text(jd_text)
    matched = []
    for tech in TECH_LIST:
        if re.search(r'\b' + re.escape(tech) + r'\b', jd_clean):
            matched.append(tech)
    return list(dict.fromkeys(matched))


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

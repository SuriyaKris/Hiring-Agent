# Implementation Plan — Phase 1 Feature Engineering

This plan details the implementation of a 6-feature vector engineering pipeline for candidate profile matching against job descriptions (JDs). The target features are:
1. `title_keyword_match` (Fuzzy token match via `rapidfuzz`)
2. `persona_match` (Discrete persona match with normalization)
3. `title_semantic_sim` (Cosine similarity of title embeddings via `sentence-transformers`)
4. `total_experience_years` (Passthrough with fallback/validation)
5. `relevant_experience_years` (Experience summation of relevant roles matching target titles)
6. `territory_match` (Fuzzy and region-lookup territory matching)

---

## User Review Required

> [!IMPORTANT]
> - **Dependency Installation**: We need to install `rapidfuzz` and `sentence-transformers`. `sentence-transformers` will download `PyTorch` (~100-200MB CPU version) and download the `all-MiniLM-L6-v2` model (~80MB) upon first initialization.
> - **LLM Prompt Updates**: We are updating the `jd_parser.txt` prompt to instruct the LLM to output the three new fields (`target_titles`, `target_persona`, `target_territory`).

## Open Questions

None at this time. All requirements are clear.

---

## Proposed Changes

### Dependencies

#### [MODIFY] [requirements.txt](file:///e:/hiring-agent-v2/backend/requirements.txt)
- Add `rapidfuzz==3.9.6`
- Add `sentence-transformers==3.0.1`

---

### NLP Modules

#### [NEW] [title_taxonomy.py](file:///e:/hiring-agent-v2/backend/nlp/title_taxonomy.py)
- Define standard title synonyms, seniority ladders, and matching thresholds (e.g. `FUZZY_MATCH_THRESHOLD = 75.0`).
- Define the region/territory mapping structure for geographic expansion.

#### [NEW] [keyword_extractor.py](file:///e:/hiring-agent-v2/backend/nlp/keyword_extractor.py)
- Implement backup heuristic parsing to extract target titles, personas, and territories from raw JD text if they are somehow missing from the LLM parsed spec.

#### [NEW] [embedding_model.py](file:///e:/hiring-agent-v2/backend/nlp/embedding_model.py)
- Implement `SentenceTransformer` loader for model `all-MiniLM-L6-v2`.
- Implement `TitleEmbedder` with a caching mechanism to avoid re-embedding target titles repeatedly during the pipeline run.

---

### Data Models & Prompting

#### [MODIFY] [schemas.py](file:///e:/hiring-agent-v2/backend/models/schemas.py)
- Add the `CandidateFeatures` Pydantic model containing the 6 target features (normalized to `0.0` - `1.0` or float years).
- Update `JDSearchSpec` to include:
  - `target_titles: list[str]`
  - `target_persona: str`
  - `target_territory: str`
- Update `ScoredCandidate` to include `features: Optional[CandidateFeatures] = None`.

#### [MODIFY] [jd_parser.txt](file:///e:/hiring-agent-v2/backend/prompts/jd_parser.txt)
- Update JSON output specification to mandate `target_titles`, `target_persona`, and `target_territory`.
- Add description/rules on how the LLM should parse/format these fields.

---

### Feature Engineering Service

#### [NEW] [feature_engineering_service.py](file:///e:/hiring-agent-v2/backend/services/feature_engineering_service.py)
- Implement calculations for all 6 target features.
- Implement the "fail loud" validation checks: if any of the target JD fields (`target_titles`, `target_persona`, `target_territory`) are missing or empty, log a warning and return `None` for the affected features.
- Perform calculations:
  - `title_keyword_match`: Fuzzy token matching of current title against target titles.
  - `persona_match`: Normalization and matching of persona string.
  - `title_semantic_sim`: Cosine similarity using the cached title embedder.
  - `total_experience_years`: Pass-through with fallback validation (summing history if missing).
  - `relevant_experience_years`: Sum duration of roles that clear the fuzzy title match threshold.
  - `territory_match`: Substring, word intersection, or region-lookup match.

---

## Verification Plan

### Automated Tests
- Test installation and initialization of the `SentenceTransformer` model.
- Run a pipeline script to verify `jd_service.py` outputs the new target fields correctly.
- Implement unit tests to score and extract features from seeded candidates (`Sarah Johnson`, `Priya Sharma`, `Patrick Munroe`) and print their 6-wide feature vector.

### Manual Verification
- Spot-check 3-5 candidates from the database to verify their generated feature vectors against their profile attributes (headline, title, location, experience history).

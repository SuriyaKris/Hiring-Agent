# Hardcoded Values — What They Are and How to Replace Them

## Everything hardcoded in Phase 1 and where to change it

---

### 1. Company name: "4CECloud Labs"

**Where it appears:**
- `frontend/src/pages/Pipeline.jsx` line: `company_name: '4CECloud Labs'`
- `frontend/src/pages/Outreach.jsx` line: `company_name: '4CECloud Labs'`
- `backend/models/schemas.py`: `company_name: str = "4CECloud Labs"`

**How to replace for Phase 2:**
Add to `.env`:
```
COMPANY_NAME=YourCompanyName
```
Then read it in `config.py` and pass it through the pipeline. The frontend reads it from `/api/status`.

---

### 2. Recruiter name: "Meghana"

**Where it appears:**
- `frontend/src/pages/Pipeline.jsx`: `recruiter_name: 'Meghana'`
- `frontend/src/pages/Outreach.jsx`: `recruiter_name: 'Meghana'`
- `backend/models/schemas.py`: `recruiter_name: str = "Meghana"`

**How to replace:**
Phase 1: Edit the two JSX lines directly.
Phase 2: Add a login/user system — recruiter name comes from the logged-in user profile.

---

### 3. Role names: "Inside Sales – US Region" and "US Sales Executive"

**Where they appear:**
- `frontend/src/pages/Pipeline.jsx`: default value in the role name input field
- `frontend/src/pages/Outreach.jsx`: state variable `roleName`
- `scripts/seed_mock.py`: `role_name` field in mock candidates

**How to replace:**
These are just default values in input fields — the recruiter can type any role name in the UI. No code change needed for different roles.

---

### 4. Sample job description text

**Where it appears:**
- `frontend/src/pages/Pipeline.jsx`: the `SAMPLE_JD` constant at the top

**How to replace:**
The recruiter pastes or uploads their own JD. The sample is just a placeholder. Remove or replace the `SAMPLE_JD` constant with an empty string when going live.

---

### 5. LLM models

**Where they appear:**
- `config.py`: `groq_fast_model`, `groq_smart_model`, `openai_fast_model`, `openai_smart_model`
- These are already driven by `.env` — not hardcoded in logic

**How to replace:**
Change in `.env`:
```
GROQ_FAST_MODEL=llama-3.1-70b-versatile   # upgrade from 8b to 70b
OPENAI_FAST_MODEL=gpt-4o-mini
OPENAI_SMART_MODEL=gpt-4o
```

---

### 6. Scoring weights (title, skills, geography, etc.)

**Where they appear:**
- `backend/prompts/scorer.txt`: the scoring rubric numbers (title_match 0-30, skills_match 0-25, etc.)

**How to replace:**
Edit `backend/prompts/scorer.txt` directly — no code changes. You can tune these weights based on what Meghana says matters most. For example, if CRM background matters more than geography, raise `crm_background` from 0-20 to 0-25.

---

### 7. Target companies for CRM ecosystem

**Where they appear:**
- `backend/prompts/jd_parser.txt`: the list of CRM ecosystem companies
- `backend/services/apollo_service.py`: used in mock data

**How to replace:**
Edit `backend/prompts/jd_parser.txt` — add or remove company names from the list. No code changes.

---

### 8. Mock candidates

**Where they appear:**
- `backend/services/apollo_service.py`: `MOCK_US_SALES_CANDIDATES` list
- `scripts/seed_mock.py`: `MOCK_CANDIDATES` list

**How to replace for production:**
Set `APOLLO_API_KEY` in `.env` — the mock data is completely bypassed and Apollo API is used instead. The `get_candidates()` function in `apollo_service.py` checks for the key automatically.

---

### 9. Database location

**Where it appears:**
- `config.py`: `database_url: str = "sqlite+aiosqlite:///./hiring_agent.db"`
- `.env.example`: `DATABASE_URL=sqlite+aiosqlite:///./hiring_agent.db`

**How to replace for production:**
```
DATABASE_URL=postgresql+asyncpg://username:password@host:5432/hiring_agent
```
Railway provides this URL automatically when you add a Postgres database to your project.

---

### 10. CORS allowed origins

**Where it appears:**
- `backend/main.py`: `allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"]`

**How to replace:**
Add your Vercel frontend URL to `.env`:
```
FRONTEND_URL=https://your-app.vercel.app
```
`main.py` reads this from settings already.

---

## Summary table

| What's hardcoded | File | Phase to replace | How |
|---|---|---|---|
| Company name "4CECloud Labs" | Pipeline.jsx, Outreach.jsx, schemas.py | Phase 2 | Add `COMPANY_NAME` to `.env` |
| Recruiter name "Meghana" | Pipeline.jsx, Outreach.jsx | Phase 2 | Add user auth / login |
| Sample JD text | Pipeline.jsx | Phase 1 | Recruiter overwrites it in UI |
| Role defaults | Pipeline.jsx | Phase 1 | Recruiter types their own |
| Scoring weights | prompts/scorer.txt | Any time | Edit the text file |
| CRM company list | prompts/jd_parser.txt | Any time | Edit the text file |
| Mock candidates | apollo_service.py | Phase 1→2 | Set `APOLLO_API_KEY` in `.env` |
| SQLite DB | config.py / .env | Phase 2 | Set `DATABASE_URL` to Postgres |
| LLM models | .env | Any time | Change model name in `.env` |
| localhost CORS | main.py | Phase 2 | Set `FRONTEND_URL` in `.env` |

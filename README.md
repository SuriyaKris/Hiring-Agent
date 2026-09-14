# 4CECloud Labs — AI Hiring Agent v2
## Apollo + OpenAI | LangGraph | Phase 1 MVP

---

## Step-by-step setup (Windows PowerShell)

### 1. Go into the project folder
```powershell
cd hiring-agent-v2
```

### 2. Copy the env file
```powershell
Copy-Item .env.example .env
```

### 3. Switch to POC mode and set your free Groq key
```powershell
# Get a FREE key at https://console.groq.com  (30 seconds, no credit card)
python scripts/switch_provider.py poc
python scripts/switch_provider.py set-groq  gsk_YOUR_KEY_HERE
```

### 4. Set up and start the backend
```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cd ..
python scripts/seed_mock.py
cd backend
uvicorn main:app --reload --port 8000
```
API is live at http://localhost:8000/docs

### 5. Start the frontend (open a new PowerShell window)
```powershell
cd hiring-agent-v2\frontend
npm install
npm run dev
```
UI is live at http://localhost:5173

### 6. Check status
```powershell
python scripts/switch_provider.py status
```

---

## Step-by-step setup (Mac / Linux)

```bash
cd hiring-agent-v2
cp .env.example .env
python scripts/switch_provider.py poc
python scripts/switch_provider.py set-groq gsk_YOUR_KEY_HERE

cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd ..
python scripts/seed_mock.py
cd backend
uvicorn main:app --reload --port 8000
```
New terminal:
```bash
cd hiring-agent-v2/frontend
npm install && npm run dev
```

---

## Test all pipeline steps
```powershell
# Windows (from hiring-agent-v2 folder, venv active)
python scripts/test_pipeline.py

# Mac/Linux
python scripts/test_pipeline.py
```

---

## Switch from POC to production

| Step | What to do | Command |
|---|---|---|
| 1 | Better LLM (OpenAI) | `python scripts/switch_provider.py set-openai sk-YOUR_KEY` then change `LLM_PROVIDER=openai` in `.env` |
| 2 | Real candidates (Apollo) | `python scripts/switch_provider.py set-apollo YOUR_APOLLO_KEY` |
| 3 | Deploy backend | Railway: `railway up` from backend folder |
| 4 | Deploy frontend | Vercel: `vercel deploy` from frontend folder |

---

## What each script does

| Script | Run from | What it does |
|---|---|---|
| `scripts/switch_provider.py poc` | `hiring-agent-v2/` | Sets LLM_PROVIDER=groq in .env |
| `scripts/switch_provider.py set-groq KEY` | `hiring-agent-v2/` | Saves Groq key to .env |
| `scripts/switch_provider.py status` | `hiring-agent-v2/` | Shows current config |
| `scripts/seed_mock.py` | `hiring-agent-v2/` | Loads 10 mock US candidates into DB |
| `scripts/test_pipeline.py` | `hiring-agent-v2/` | Tests all 5 pipeline steps |

---

## POC vs Production

| Component | POC (free) | Production | Change needed |
|---|---|---|---|
| LLM | Groq free (Llama 3.1) | OpenAI gpt-4o-mini + gpt-4o | `LLM_PROVIDER=openai` in .env |
| Candidates | Mock JSON (10 profiles) | Apollo.io API (real people) | `APOLLO_API_KEY=...` in .env |
| Database | SQLite local file | Postgres on Railway | `DATABASE_URL=postgresql://...` in .env |
| Hosting | localhost | Railway + Vercel | Deploy commands above |
| Monthly cost | $0 | ~$64/mo | |

---

## Project structure

```
hiring-agent-v2/
├── .env.example              Copy to .env, fill in keys
├── docker-compose.yml        One-command start (optional)
├── README.md
├── backend/
│   ├── main.py               FastAPI app entry point
│   ├── config.py             Reads .env, handles provider switching
│   ├── db.py                 SQLAlchemy: SQLite (POC) / Postgres (prod)
│   ├── agents/
│   │   └── hiring_graph.py   LangGraph pipeline: parse -> search -> score
│   ├── services/
│   │   ├── llm_service.py    Groq/OpenAI abstraction (one-line switch)
│   │   ├── apollo_service.py Apollo API + 10 mock US sales candidates
│   │   ├── jd_service.py     JD parser + Boolean string builder
│   │   ├── scoring_service.py AI scorer + rule-based fallback
│   │   └── outreach_service.py Personalised message generator
│   ├── routers/              jd_parser, search, outreach, pipeline
│   ├── prompts/              jd_parser.txt, scorer.txt, outreach.txt
│   └── requirements.txt
├── frontend/
│   └── src/pages/
│       ├── Pipeline.jsx      Tab 1: one-click full pipeline run
│       ├── Candidates.jsx    Tab 2: ranked list + verdict controls
│       └── Outreach.jsx      Tab 3: copy-ready messages + tracker
├── scripts/
│   ├── switch_provider.py    Switch POC <-> production, set keys
│   ├── seed_mock.py          Load 10 mock candidates (no API needed)
│   └── test_pipeline.py      End-to-end test all 5 steps
└── docs/
    ├── tech-stack.md         Full tools table with costs
    └── poc-to-production.md  Detailed upgrade guide
```

---

## Deploying to Netlify (Frontend) + Render (Backend)

### 1. Render (FastAPI Backend)
1. **Root Directory**: `backend` (or build command from repo root: `pip install -r backend/requirements.txt`)
2. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables**:
   - `DATABASE_URL`: Your PostgreSQL connection string (e.g. Render Postgres)
   - `FRONTEND_URL`: `https://<your-netlify-site>.netlify.app`
   - `LLM_PROVIDER`: `gemini` (or `groq` / `openai`)
   - `GEMINI_API_KEY`: Your Google AI Studio key
   - `GEMINI_FAST_MODEL`: `gemini-3.6-flash`
   - `GEMINI_SMART_MODEL`: `gemini-3.6-flash`
   - `APOLLO_API_KEY`: Your Apollo.io API key (or blank for mock data)

### 2. Netlify (React Frontend)
1. **Base directory**: `frontend`
2. **Build command**: `npm run build`
3. **Publish directory**: `dist` (or `frontend/dist` if deploying from repo root)
4. **Environment Variables**:
   - `VITE_API_URL`: `https://<your-render-backend-url>.onrender.com` (no trailing slash)
5. **SPA Redirects**: Included automatically in `frontend/public/_redirects` and `netlify.toml`.


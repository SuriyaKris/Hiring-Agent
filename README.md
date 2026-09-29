# 4CECloud Labs — AI Hiring Agent v2
## Apollo + Gemini / Groq / OpenAI | LangGraph | Phase 1 MVP

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

### 3. Set Gemini as primary LLM & set keys
```powershell
# Set Gemini as primary LLM (free key at https://aistudio.google.com)
python scripts/switch_provider.py gemini
python scripts/switch_provider.py set-gemini YOUR_GEMINI_KEY

# Set your Apollo API key for live candidate search
python scripts/switch_provider.py set-apollo YOUR_APOLLO_KEY
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
python scripts/switch_provider.py gemini
python scripts/switch_provider.py set-gemini YOUR_GEMINI_KEY
python scripts/switch_provider.py set-apollo YOUR_APOLLO_KEY

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
# Run from hiring-agent-v2 folder
python scripts/test_pipeline.py
```

---

## Provider Options & Switching

| Provider | Purpose | Switch Command | Required Key |
|---|---|---|---|
| **Gemini** (Primary) | High accuracy, generous rate limit, free tier | `python scripts/switch_provider.py gemini` | `GEMINI_API_KEY` (Google AI Studio) |
| **Groq** (Fallback) | Fast free tier fallback | `python scripts/switch_provider.py poc` | `GROQ_API_KEY` (Groq Console) |
| **OpenAI** (Paid) | Optional paid production | `python scripts/switch_provider.py production` | `OPENAI_API_KEY` (OpenAI Platform) |

---

## What each script does

| Script | Run from | What it does |
|---|---|---|
| `scripts/switch_provider.py gemini` | `hiring-agent-v2/` | Sets `LLM_PROVIDER=gemini` in `.env` |
| `scripts/switch_provider.py set-gemini KEY` | `hiring-agent-v2/` | Saves Gemini API key to `.env` |
| `scripts/switch_provider.py set-apollo KEY` | `hiring-agent-v2/` | Saves Apollo API key to `.env` |
| `scripts/switch_provider.py poc` | `hiring-agent-v2/` | Sets `LLM_PROVIDER=groq` in `.env` |
| `scripts/switch_provider.py set-groq KEY` | `hiring-agent-v2/` | Saves Groq key to `.env` |
| `scripts/switch_provider.py status` | `hiring-agent-v2/` | Shows current LLM, Apollo, and DB config |
| `scripts/seed_mock.py` | `hiring-agent-v2/` | Loads 10 mock US candidates into DB |
| `scripts/test_pipeline.py` | `hiring-agent-v2/` | Tests all 5 pipeline steps end-to-end |

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
   - `GEMINI_FAST_MODEL`: `gemini-3.5-flash-lite`
   - `GEMINI_SMART_MODEL`: `gemini-3.5-flash-lite`
   - `APOLLO_API_KEY`: Your Apollo.io API key (or blank for mock data)

### 2. Netlify (React Frontend)
1. **Base directory**: `frontend`
2. **Build command**: `npm run build`
3. **Publish directory**: `dist` (or `frontend/dist` if deploying from repo root)
4. **Environment Variables**:
   - `VITE_API_URL`: `https://<your-render-backend-url>.onrender.com` (no trailing slash)

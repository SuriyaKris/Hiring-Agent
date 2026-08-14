# POC → Production Switch Guide
## Step-by-step instructions for each upgrade

---

## Stage 0 — POC (free, today)

**What's free:**
- Groq API: free tier at console.groq.com — llama-3.1-8b-instant for fast tasks, mixtral-8x7b for scoring
- Mock candidate data: 10 realistic US sales profiles built into the code
- SQLite: zero-config local database
- Chroma: local vector store

**Setup commands:**
```bash
# 1. Get a free Groq key (30 seconds)
#    → https://console.groq.com → Sign up → API Keys → Create key

# 2. Configure
cp .env.example .env
python scripts/switch_provider.py poc
python scripts/switch_provider.py set-groq gsk_YOUR_KEY_HERE

# 3. Start backend
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python ../scripts/seed_mock.py          # load mock candidates
uvicorn main:app --reload --port 8000

# 4. Start frontend (new terminal)
cd frontend
npm install && npm run dev

# 5. Verify
curl http://localhost:8000/health
# → {"status":"ok","llm_provider":"groq","data_source":"mock"}
```

**What you can test in POC:**
✅ Full pipeline UI (upload JD → see ranked candidates → generate outreach)
✅ LLM JD parsing (real AI, real Groq API)
✅ Candidate scoring with AI (real scoring logic, mock profiles)
✅ Outreach message generation (real personalised drafts)
✅ Outreach tracking (mark as sent, record status)
✅ API docs at http://localhost:8000/docs

**What POC cannot test:**
❌ Real LinkedIn candidate discovery (needs Apollo)
❌ Verified email data (needs Apollo)
❌ Large-scale pipeline runs

---

## Stage 1 — Add real LLM (OpenAI, ~$15/mo)

**When to do this:** When you want better scoring quality than Groq provides.
Groq's Mixtral is good but gpt-4o scores more accurately for nuanced role matching.

```bash
# 1. Get OpenAI key
#    → https://platform.openai.com → API Keys → Create new secret key
#    Add $20 credit to start (lasts 1-2 months at MVP volume)

# 2. Switch provider
python scripts/switch_provider.py set-openai sk-YOUR_KEY_HERE
python scripts/switch_provider.py production   # changes LLM_PROVIDER=openai in .env

# 3. Restart backend
# Ctrl+C then:
uvicorn main:app --reload --port 8000

# 4. Verify
curl http://localhost:8000/api/status
# → {"llm_provider":"openai","fast_model":"gpt-4o-mini","smart_model":"gpt-4o",...}
```

No code changes needed — the `llm_service.py` abstraction handles the switch.

---

## Stage 2 — Add real candidate data (Apollo, $49/mo)

**When to do this:** When you're ready to source real US candidates.

```bash
# 1. Sign up at https://app.apollo.io
#    → Settings → Integrations → API → Copy API key
#    Note: API access requires a paid plan or custom agreement

# 2. Set the key
python scripts/switch_provider.py set-apollo YOUR_APOLLO_KEY

# 3. Restart backend — Apollo auto-activates when key is present
uvicorn main:app --reload --port 8000

# 4. Verify
curl http://localhost:8000/api/status
# → {"data_source":"Apollo.io (production)","using_mock_data":false,...}

# 5. Run a real pipeline
# Go to http://localhost:5173 → Run Pipeline
# Agent will now call Apollo API for real US sales candidates
```

**Apollo query the agent sends:**
```json
{
  "person_titles": ["Inside Sales Representative", "SDR", "BDR", "Account Executive"],
  "person_locations": ["United States", "USA", "Remote US"],
  "q_keywords": "Salesforce HubSpot CRM",
  "person_seniorities": ["senior", "mid"],
  "per_page": 25
}
```

---

## Stage 3 — Deploy to production hosting

**Backend → Railway:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
cd backend
railway init          # creates a new Railway project
railway up            # deploys backend

# Set environment variables in Railway dashboard:
# LLM_PROVIDER, OPENAI_API_KEY, APOLLO_API_KEY, etc.

# Add Postgres (Railway UI: + New → Database → PostgreSQL)
# Railway provides DATABASE_URL automatically

# Update .env with Railway's public URL for FRONTEND_URL
```

**Frontend → Vercel:**
```bash
# Install Vercel CLI
npm install -g vercel

cd frontend

# Update vite.config.js proxy target to your Railway backend URL
# Or set VITE_API_URL environment variable in Vercel dashboard

vercel deploy --prod
# → Your app is live at https://your-app.vercel.app
```

---

## Stage 4 — Phase 2 additions (months 4–6)

### Add SerpAPI for overflow LinkedIn search
```bash
# Get free key at https://serpapi.com (100 free searches/month)
# Set in .env:
SERPAPI_KEY=your_key

# SerpAPI service (backend/services/serpapi_service.py) activates automatically
# Used only when Apollo returns < 20 results for a query
```

### Add Hunter.io for email fallback
```bash
# Get free key at https://hunter.io (25 free/month)
# Set in .env:
HUNTER_API_KEY=your_key

# Email enrichment runs automatically on candidates missing Apollo email
```

### Add LangSmith tracing (free)
```bash
# Sign up at https://smith.langchain.com
# Set in .env:
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_key
LANGCHAIN_PROJECT=hiring-agent-v2

# Now every LangGraph pipeline run is visible in LangSmith dashboard
# See exactly what each node did, how long it took, what the LLM returned
```

---

## Quick reference: what each key unlocks

| Key | Where to get it | What it unlocks | Free tier |
|---|---|---|---|
| `GROQ_API_KEY` | console.groq.com | Real LLM (Llama 3.1 / Mixtral) | 14,400 req/day |
| `OPENAI_API_KEY` | platform.openai.com | GPT-4o-mini + GPT-4o | $5 free credit |
| `APOLLO_API_KEY` | app.apollo.io | Real US candidate search + emails | 50 contacts/mo |
| `SERPAPI_KEY` | serpapi.com | Google X-Ray LinkedIn search | 100 searches/mo |
| `PROXYCURL_API_KEY` | nubela.co/proxycurl | LinkedIn profile enrichment | 10 free credits |
| `LANGCHAIN_API_KEY` | smith.langchain.com | Pipeline tracing + debugging | Free tier |

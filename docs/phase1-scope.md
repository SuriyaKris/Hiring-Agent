# Phase 1 — What We Are Building and Why

## The problem we are solving

Meghana (the recruiter) spends 8–10 hours per week manually:
1. Searching LinkedIn for Inside Sales and US Sales Executive candidates
2. Reading each profile to judge if they're relevant
3. Writing individual outreach messages for each person
4. Tracking who she contacted and who replied

These two roles have been open for 3–4 months with no hire. The bottleneck is the sourcing and screening volume — not a lack of candidates in the market.

---

## What Phase 1 does (and only this)

Phase 1 automates exactly the three steps that consume most of Meghana's time:

### Step 1 — JD Parser
**What it does:** Meghana uploads or pastes the job description. The AI reads it and produces a structured search specification — an expanded list of job titles (not just "Inside Sales" but also SDR, BDR, Account Executive, etc.), required skills, target companies in the Salesforce ecosystem, and geography filters.

**Why this matters:** Without this, Meghana has to manually think of all the title variations that might match. She typically misses 30–40% of relevant candidates because she searches only the exact title she knows.

**What Meghana does instead:** Upload JD → review the parsed spec → confirm it looks right → move to step 2.

---

### Step 2 — Candidate search + AI scoring
**What it does:** The agent queries Apollo.io (or uses mock data in POC) with the parsed spec. It gets back up to 25–50 US candidates matching the titles, geography, and keywords. Each candidate is then scored 0–100 by the AI based on title match, skills overlap, CRM background, job stability, and geography. The list is sorted with the best matches at the top.

**Why this matters:** Meghana currently reads every profile manually and judges fit herself. That takes 3–5 minutes per profile. The AI does it in 2–3 seconds per profile and applies consistent criteria every time.

**What Meghana does instead:** Review the top 10–15 ranked candidates, click shortlist/maybe/skip on each one. This takes 15–20 minutes instead of 3+ hours.

---

### Step 3 — Outreach message generator
**What it does:** For each shortlisted candidate, the agent generates a personalised message pack: a LinkedIn connection note (under 300 characters), an InMail subject + body, an email subject + body, and two follow-up messages. Each message references something specific about that candidate — their current company, a matching skill, whether they're open to work.

**Why this matters:** Meghana currently writes each message from scratch or uses a template that candidates can see is generic. Generic messages get 3–5% reply rates. Personalised messages referencing specific profile details get 15–25% reply rates.

**What Meghana does instead:** Review the draft, make any tweaks, copy and send. This takes 2–3 minutes per candidate instead of 10–15 minutes.

---

## What Phase 1 does NOT do

These are deliberately left out to keep Phase 1 focused and shippable:

| What's excluded | Why | When it gets added |
|---|---|---|
| Automatic sending of messages | LinkedIn blocks automated sending — Meghana must click send herself | Never automated (ToS risk) |
| Real-time LinkedIn scraping | Requires LinkedIn Sales Navigator API or violates ToS | Phase 2 alternative approach |
| Follow-up scheduling / reminders | Would need a scheduler / cron job | Phase 2 |
| Candidate reply tracking | Would need email/LinkedIn inbox integration | Phase 2 |
| Multiple recruiters / team features | Needs auth system | Phase 3 |
| Learning from past hires | Needs enough historical data (6+ months) | Phase 3 |
| Other role types (engineering, etc.) | Prompts are tuned for US sales right now | Phase 2 with prompt updates |

---

## Time saving — before vs after

| Task | Before Phase 1 | After Phase 1 | Time saved |
|---|---|---|---|
| Search LinkedIn for candidates | 3–4 hours/week | 0 (Apollo does it) | 3–4 hours |
| Read and filter profiles | 2–3 hours/week | 20 min (review AI scores) | 2+ hours |
| Write outreach messages | 2–3 hours/week | 20 min (review AI drafts) | 2+ hours |
| **Total** | **8–10 hours/week** | **~1 hour/week** | **~8 hours/week** |

---

## Phase 1 deliverables checklist

- [x] FastAPI backend with 4 routers (JD parser, search, outreach, pipeline)
- [x] LangGraph orchestrated pipeline (parse → search → score)
- [x] LLM abstraction layer (Groq free / OpenAI paid — switch via .env)
- [x] Apollo.io integration with mock data fallback for POC
- [x] AI candidate scorer with 5-dimension rubric + rule-based fallback
- [x] Personalised outreach generator (InMail + email + 2 follow-ups)
- [x] React dashboard with 3 tabs (Pipeline, Candidates, Outreach)
- [x] SQLite database for candidates + outreach history
- [x] Windows setup scripts (batch files, no venv activation issues)
- [x] POC mode: fully testable with $0 spend using Groq + mock data

---

## Phase 1 monthly cost

| Item | Cost |
|---|---|
| Groq API (POC) | $0 |
| OpenAI API (production) | ~$15/mo |
| Apollo.io Basic (production) | $49/mo |
| Railway hosting | $5/mo |
| Vercel frontend | $0 |
| **Total production** | **~$69/mo** |

Compared to LinkedIn Sales Navigator at $99–150/mo with no automation.

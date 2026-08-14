# Tech Stack Reference — 4CECloud AI Hiring Agent

## Core development stack

| Layer | Tool / Library | Why we use it | How effective | POC cost | Prod cost |
|---|---|---|---|---|---|
| LLM — fast tasks | `gpt-4o-mini` (prod) / `llama-3.1-8b-instant` (POC) | JD parsing, outreach drafts — structured JSON output | Very high for parsing and generation tasks | $0 (Groq free tier) | ~$2–5/mo |
| LLM — scoring | `gpt-4o` (prod) / `mixtral-8x7b-32768` (POC) | Candidate scoring — needs stronger reasoning | High; scoring quality improves conversion rates | $0 (Groq free tier) | ~$8–12/mo |
| Candidate discovery | Apollo.io People API | Automated people search by title + geo + skills — returns LinkedIn URL + verified email in one call | High for US SaaS/sales roles; 90%+ coverage | $0 (50 credits free) | $49/mo (1,000 exports) |
| Agent orchestration | LangGraph | Stateful pipeline: parse → search → score → outreach. Handles retries, conditional edges, future human-in-the-loop | Very high for multi-step agent workflows | $0 (open source) | $0 |
| Backend API | FastAPI | High-performance Python async API. Auto-generates OpenAPI docs at /docs | Very high — fastest Python framework for APIs | $0 | $0 |
| Data validation | Pydantic v2 | Types all request/response payloads. Catches malformed LLM output before it breaks the pipeline | High — prevents runtime errors from bad JSON | $0 | $0 |
| Database / ORM | SQLAlchemy + SQLite (POC) → Postgres (prod) | Stores candidates, outreach history, pipeline runs. Async-native. Railway supports zero-config Postgres | High — full auditability and tracking | $0 (SQLite) | $0–5/mo (Railway) |
| Vector store | Chroma (local) | Profile embeddings for semantic deduplication — prevents rescoring the same person twice | High for small–mid scale (up to 50k profiles) | $0 | $0 |
| Frontend | React 18 + Vite | Component-based UI, fast HMR, minimal config. Vite proxy routes /api calls to FastAPI | Very high — 3-tab dashboard ships fast | $0 | $0 |
| Styling | TailwindCSS | Utility-first CSS — build clean recruiter UI without writing custom CSS | High — consistent design with minimal effort | $0 | $0 |
| Frontend hosting | Vercel | `vercel deploy` — done. Free Hobby tier handles MVP traffic | Very high for fast deployment | $0 (Hobby) | $0–20/mo |
| Backend hosting | Railway | Drag-and-drop Python deploy + Postgres provisioning. SSH, logs, env vars all in UI | High for quick MVP deployment | $0–5/mo | $5–20/mo |
| Document parsing | pypdf + python-docx | Extract text from JD uploads in PDF or DOCX format | High — handles most JD file formats | $0 | $0 |
| Retry logic | tenacity | Wraps all LLM and API calls with exponential backoff. Critical for Groq free tier rate limits | Essential for reliability | $0 | $0 |
| Logging | loguru | Structured logging across all services. Single `logger.info()` call, no config needed | High — easy debug without setup overhead | $0 | $0 |
| HTTP client | httpx | Async HTTP for Apollo, SerpAPI, Proxycurl calls. Drop-in replacement for requests | High for async API calls | $0 | $0 |
| Env config | pydantic-settings | Reads `.env` into typed Settings object. Provider switching (Groq ↔ OpenAI) with one env var | High — clean config, no scattered os.getenv() | $0 | $0 |

---

## Phase 2 additions (months 4–6)

| Tool | Purpose | Why add it | Cost |
|---|---|---|---|
| SerpAPI | Google X-Ray search — `site:linkedin.com/in/ "inside sales" "United States"` — finds profiles not in Apollo | Overflow sourcing for niche roles Apollo misses | $0 free (100/mo), $50/mo (5,000) |
| Proxycurl | Fetch full LinkedIn profile JSON from a URL — use with SerpAPI results | Enriches SerpAPI URLs into structured profiles | $0.01/profile |
| Hunter.io | Email enrichment by name + company — fallback when Apollo email is missing | Increases email coverage from 60% → 80%+ | $0 free (25/mo), $49/mo |
| LangSmith | LangChain tracing — visualise every agent step, debug prompt failures | Speeds up prompt tuning and debugging | $0 free tier |
| Alembic | Database migrations — manage schema changes without dropping tables | Required once you move to Postgres in production | $0 |

---

## Phase 3 / optional tools (months 7+)

| Tool | Purpose | Cost | Note |
|---|---|---|---|
| Mistral Small 3.1 | Self-hosted open-source LLM — Apache 2.0 license. Strong instruction following and function calling | Compute only (no license fee) | Replace Groq/OpenAI for zero ongoing LLM cost |
| Qwen2.5-7B-Instruct | Strong at structured JSON extraction and long-context tasks. Apache 2.0 (most variants) | Compute only | Good alternative for JD parsing |
| BGE-M3 | Multilingual embedding model — 100+ languages, multi-function retrieval | $0 | Replaces OpenAI embeddings for semantic search |
| Playwright | Browser automation — for controlled UI actions if needed in future | $0 license (higher maintenance) | Only if scraping becomes necessary |
| Bright Data | Enterprise-grade web scraping infrastructure | Quote-based ($500+/mo) | Only if Apollo/SerpAPI coverage becomes insufficient |
| Apollo Custom Plan | Higher API credits + deeper query filters | Quote-based | When monthly volume exceeds 2,000 contacts |
| Pinecone | Managed vector DB — replaces local Chroma at scale (100k+ profiles) | $70/mo (Standard) | Phase 3 only |
| Redis | Job queue for async pipeline runs — prevents timeout on large batches | $0 (self-hosted) | When running 50+ candidates per pipeline run |

---

## Monthly cost summary

| Phase | What's running | Monthly cost |
|---|---|---|
| POC | Groq (free) + mock data + SQLite + localhost | $0 |
| Phase 1 MVP | OpenAI (~$15) + Apollo Basic ($49) + Railway ($5) + Vercel ($0) | ~$69/mo |
| Phase 2 | + SerpAPI ($50) + Hunter.io ($49) + LangSmith ($0) | ~$168/mo |
| Phase 3 | Self-hosted Mistral (replaces OpenAI) + Apollo Custom | ~$100–150/mo |

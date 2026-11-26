import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

load_dotenv(override=False)

from config import get_settings
from db import init_db
from routers import jd_parser, outreach, pipeline, auth, jobs, apollo, candidates, user_auth

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting AI Hiring Agent v2")
    logger.info(f"LLM provider: {settings.llm_provider} | model: {settings.fast_model}")
    logger.info(f"Data source: Apollo.io")
    db_type = "PostgreSQL" if settings.database_url.startswith("postgresql") else "SQLite"
    logger.info(f"Database engine: {db_type}")
    await init_db()
    logger.info("Database ready.")

    def _warmup_embeddings():
        try:
            from nlp.embedding_model import get_embedding_model
            get_embedding_model()
            logger.info("SentenceTransformer model pre-warmed successfully.")
        except Exception as e:
            logger.warning(f"Embedding model warmup skipped: {e}")

    asyncio.create_task(asyncio.to_thread(_warmup_embeddings))

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="4CECloud AI Hiring Agent v2",
    description="Apollo + LangGraph + OpenAI/Groq · Phase 1 MVP",
    version="2.0.0",
    lifespan=lifespan,
)

# Parse allowed origins from settings and defaults
raw_origins = [o.strip() for o in settings.frontend_url.split(",") if o.strip()]
default_origins = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:4173", "http://127.0.0.1:4173"
]
for default_origin in default_origins:
    if default_origin not in raw_origins:
        raw_origins.append(default_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=raw_origins,
    allow_origin_regex=r"^https?://([a-zA-Z0-9_-]+\.)*(netlify\.app|onrender\.com|localhost)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(jd_parser.router, prefix="/api", tags=["JD Parser"])
app.include_router(outreach.router, prefix="/api", tags=["Outreach"])
app.include_router(pipeline.router, prefix="/api", tags=["Pipeline"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(user_auth.router, prefix="/api", tags=["Recruiter Auth"])
app.include_router(jobs.router, prefix="/api", tags=["Jobs"])
app.include_router(apollo.router, prefix="/api", tags=["Apollo"])
app.include_router(candidates.router, prefix="/api", tags=["Candidates"])


@app.get("/")
@app.head("/")
async def root():
    return {
        "name": "4CECloud AI Hiring Agent API",
        "status": "online",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "llm_provider": settings.llm_provider,
        "data_source": "apollo",
    }


@app.get("/api/status")
async def get_status():
    return {
        "apollo_active": bool(settings.apollo_api_key),
        "using_mock_data": False,
        "llm_provider": settings.llm_provider,
        "fast_model": settings.fast_model,
    }

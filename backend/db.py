"""
Async SQLAlchemy database setup.
SQLite for POC (zero config), Postgres for production (change DATABASE_URL).
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Boolean, Text, DateTime, Integer, ForeignKey, Uuid
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime, timezone
from typing import Optional
from config import get_settings

settings = get_settings()

connect_args = {}
kwargs = {}
if settings.database_url.startswith("postgresql"):
    kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(
    settings.database_url,
    echo=False,
    **kwargs
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class CandidateRecord(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), default=None, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    headline: Mapped[str] = mapped_column(String(500), default="")
    current_company: Mapped[str] = mapped_column(String(200), default="")
    current_title: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    fitment_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    score_reasoning: Mapped[str] = mapped_column(Text, default="")
    recommended_action: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    is_open_to_work: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(50), default="apollo")
    raw_json: Mapped[str] = mapped_column(Text, default="{}")
    recruiter_verdict: Mapped[str] = mapped_column(String(50), default="pending")
    role_name: Mapped[str] = mapped_column(String(200), default="")
    
    # Candidate Intelligence Additions
    apollo_person_id: Mapped[Optional[str]] = mapped_column(String(100), default=None, index=True)
    apollo_organization_id: Mapped[Optional[str]] = mapped_column(String(100), default=None)
    indeed_url: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    candidate_origin: Mapped[str] = mapped_column(String(50), default="apollo")
    source_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    search_session_id: Mapped[Optional[str]] = mapped_column(String(100), default=None, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class OutreachRecord(Base):
    __tablename__ = "outreach"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_linkedin_url: Mapped[str] = mapped_column(String(500), index=True)
    candidate_name: Mapped[str] = mapped_column(String(200))
    role_name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(50))
    message_sent: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    recruiter_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SearchSessionRecord(Base):
    __tablename__ = "search_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    role_name: Mapped[str] = mapped_column(String(200))
    jd_text: Mapped[str] = mapped_column(Text)
    parsed_spec_json: Mapped[str] = mapped_column(Text, default="{}")
    apollo_filters_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(50), default="running")
    audit_trail_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    role_track_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    spec_fingerprint_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True, index=True)
    spec_embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(384), nullable=True)


async def init_db():
    try:
        async with engine.begin() as conn:
            if settings.database_url.startswith("postgresql"):
                try:
                    from sqlalchemy import text
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                except Exception as e:
                    from loguru import logger
                    logger.warning(f"Could not enable pgvector extension: {e}")
            await conn.run_sync(Base.metadata.create_all)

        # Seed default demo recruiter user if not present
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            import bcrypt
            stmt = select(UserRecord).where(UserRecord.email == "recruiter@4cecloud.com")
            res = await session.execute(stmt)
            if not res.scalars().first():
                demo_pw = bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode("utf-8")
                session.add(UserRecord(
                    email="recruiter@4cecloud.com",
                    hashed_password=demo_pw,
                    full_name="Meghana (Recruiter)"
                ))
                from loguru import logger
                logger.info("Created default demo user: recruiter@4cecloud.com")

            # Clean legacy 0 matched skills reasoning from database
            from sqlalchemy import update
            await session.execute(
                update(CandidateRecord)
                .where(CandidateRecord.score_reasoning.like("%0 matched skills%"))
                .values(score_reasoning="")
            )
            await session.commit()

        from loguru import logger
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        from loguru import logger
        logger.warning(f"Database auto-initialization skipped or failed: {e}")


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

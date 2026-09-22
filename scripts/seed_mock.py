"""
cleanup_db.py — Cleans mock/fallback candidate records from the database.
"""

import asyncio
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.chdir(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from db import init_db, AsyncSessionLocal, CandidateRecord
from sqlalchemy import delete


async def cleanup():
    await init_db()
    async with AsyncSessionLocal() as db:
        # Delete any records with source='mock' or placeholder fake records
        res = await db.execute(delete(CandidateRecord).where(CandidateRecord.source == "mock"))
        await db.commit()
        print(f"Purged fake/mock candidates from database.")

if __name__ == "__main__":
    asyncio.run(cleanup())

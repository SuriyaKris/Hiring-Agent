import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from db import get_db, UserRecord

router = APIRouter()

# Authentication configuration
JWT_SECRET = "4cecloud_hiring_agent_v2_jwt_auth_secret_key_prod_development"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Pydantic schemas for request / response validation
class UserSignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = ""

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponseSchema(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str
    user: UserResponseSchema


# Authentication helper functions
def hash_password(password: str) -> str:
    pw_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pw_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(pw_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    expires = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "exp": expires
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# Dependency to fetch the active logged-in user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserRecord:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    stmt = select(UserRecord).where(UserRecord.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


# Signup Route
@router.post("/auth/signup", response_model=TokenResponseSchema)
async def signup(
    req: UserSignupRequest,
    db: AsyncSession = Depends(get_db)
):
    # Check if email is already taken
    stmt = select(UserRecord).where(UserRecord.email == req.email.lower())
    result = await db.execute(stmt)
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash the password and create the new user
    new_user = UserRecord(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name or ""
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Generate token
    token = create_access_token(new_user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user
    }


# Login Route
@router.post("/auth/login", response_model=TokenResponseSchema)
async def login(
    req: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(UserRecord).where(UserRecord.email == req.email.lower())
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate token
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }


# Profile Info Route
@router.get("/auth/me", response_model=UserResponseSchema)
async def get_me(current_user: UserRecord = Depends(get_current_user)):
    return current_user


# GET /me/roles
@router.get("/me/roles")
async def get_my_roles(
    current_user: UserRecord = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all unique role tracks for the logged-in user.
    Groups searches by role_track_id and returns aggregation info.
    """
    from sqlalchemy import select
    from db import SearchSessionRecord, CandidateRecord
    
    # 1. Load all sessions for current user
    stmt = select(SearchSessionRecord).where(
        SearchSessionRecord.user_id == current_user.id
    ).order_by(SearchSessionRecord.created_at.desc())
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    # 2. Group them by role_track_id
    tracks = {}
    for s in sessions:
        if not s.role_track_id:
            continue
        t_id = str(s.role_track_id)
        if t_id not in tracks:
            tracks[t_id] = {
                "role_track_id": t_id,
                "role_name": s.role_name,
                "search_count": 0,
                "last_search_at": s.created_at.isoformat() if s.created_at else None,
                "session_ids": []
            }
        tracks[t_id]["search_count"] += 1
        tracks[t_id]["session_ids"].append(s.session_id)
        # Update representative name/timestamp with the most recent search
        if s.created_at:
            t_info = tracks[t_id]
            # Convert str last_search_at back to datetime for comparison
            last_dt = datetime.fromisoformat(t_info["last_search_at"]) if t_info["last_search_at"] else None
            if not last_dt or s.created_at > last_dt:
                t_info["last_search_at"] = s.created_at.isoformat()
                t_info["role_name"] = s.role_name

    # 3. For each track, count unique candidates matching those session IDs
    result_list = []
    for t_id, t_info in tracks.items():
        if not t_info["session_ids"]:
            t_info["candidate_count"] = 0
            result_list.append(t_info)
            continue
            
        cand_stmt = select(CandidateRecord.linkedin_url, CandidateRecord.email, CandidateRecord.apollo_person_id)\
            .where(CandidateRecord.search_session_id.in_(t_info["session_ids"]))
        c_res = await db.execute(cand_stmt)
        candidates = c_res.all()
        
        # Deduplicate unique candidates in this track
        from identity.matching_engine import normalize_val
        unique_ids = set()
        unique_cands_count = 0
        for url, email, ap_id in candidates:
            norm_url = normalize_val(url)
            norm_email = normalize_val(email)
            norm_ap = normalize_val(ap_id)
            
            matched = False
            for key in [norm_url, norm_email, norm_ap]:
                if key and key in unique_ids:
                    matched = True
                    break
            if not matched:
                unique_cands_count += 1
                for key in [norm_url, norm_email, norm_ap]:
                    if key:
                        unique_ids.add(key)
                        
        t_info["candidate_count"] = unique_cands_count
        del t_info["session_ids"]
        result_list.append(t_info)

    # Sort result list by last_search_at desc
    result_list.sort(key=lambda x: x["last_search_at"] or "", reverse=True)
    return result_list


# GET /me/roles/{role_track_id}/sessions
@router.get("/me/roles/{role_track_id}/sessions")
async def get_role_track_sessions(
    role_track_id: uuid.UUID,
    current_user: UserRecord = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List every search session in this role track."""
    from sqlalchemy import select, func
    from db import SearchSessionRecord, CandidateRecord
    
    stmt = select(SearchSessionRecord).where(
        SearchSessionRecord.user_id == current_user.id
    ).where(
        SearchSessionRecord.role_track_id == role_track_id
    ).order_by(SearchSessionRecord.created_at.desc())
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    result = []
    for s in sessions:
        c_stmt = select(func.count(CandidateRecord.id)).where(CandidateRecord.search_session_id == s.session_id)
        c_count_res = await db.execute(c_stmt)
        c_count = c_count_res.scalar() or 0
        
        result.append({
            "session_id": s.session_id,
            "role_name": s.role_name,
            "jd_snippet": s.jd_text[:150] + "..." if len(s.jd_text) > 150 else s.jd_text,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "candidate_count": c_count
        })
    return result


# GET /me/sessions/{session_id}/candidates
@router.get("/me/sessions/{session_id}/candidates")
async def get_session_candidates(
    session_id: str,
    current_user: UserRecord = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve candidates for a specific search session."""
    from sqlalchemy import select
    from db import CandidateRecord, SearchSessionRecord
    import json
    from routers.candidates import _normalize_raw_json
    
    # Verify session belongs to user
    sess_stmt = select(SearchSessionRecord).where(
        SearchSessionRecord.session_id == session_id
    ).where(
        SearchSessionRecord.user_id == current_user.id
    )
    sess_res = await db.execute(sess_stmt)
    sess = sess_res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Search session not found or access denied")

    result = await db.execute(
        select(CandidateRecord)
        .where(CandidateRecord.search_session_id == session_id)
        .order_by(CandidateRecord.fitment_score.desc())
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "linkedin_url": r.linkedin_url,
            "full_name": r.full_name,
            "headline": r.headline,
            "current_company": r.current_company,
            "current_title": r.current_title,
            "location": r.location,
            "fitment_score": r.fitment_score,
            "score_breakdown": json.loads(r.score_breakdown_json or "{}"),
            "score_reasoning": r.score_reasoning,
            "recommended_action": r.recommended_action,
            "email": r.email,
            "phone": r.phone,
            "is_open_to_work": r.is_open_to_work,
            "source": r.source,
            "recruiter_verdict": r.recruiter_verdict,
            "role_name": r.role_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "profile_details": _normalize_raw_json(r.raw_json, r.source),
        }
        for r in rows
    ]

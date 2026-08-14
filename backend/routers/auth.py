from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
import httpx
import json
import os
from config import get_settings
from loguru import logger

router = APIRouter()
settings = get_settings()

TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".apollo_token.json")

@router.get("/auth/apollo/url")
async def get_apollo_oauth_url():
    """Generate the Apollo.io OAuth authorization URL."""
    if not settings.apollo_client_id:
        raise HTTPException(status_code=400, detail="APOLLO_CLIENT_ID is not configured in .env")
        
    client_id = settings.apollo_client_id
    redirect_uri = settings.apollo_redirect_uri
    
    if not redirect_uri:
         raise HTTPException(status_code=400, detail="APOLLO_REDIRECT_URI is not configured in .env")
         
    url = (
        f"https://app.apollo.io/#/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&state=csrf_security_state"
    )
    return {"url": url}


@router.get("/auth/apollo/login")
async def apollo_login_redirect():
    """Redirect browser directly to the Apollo OAuth authorization page."""
    if not settings.apollo_client_id or not settings.apollo_redirect_uri:
        raise HTTPException(status_code=400, detail="APOLLO_CLIENT_ID or APOLLO_REDIRECT_URI not configured in .env")
    url = (
        f"https://app.apollo.io/#/oauth/authorize"
        f"?client_id={settings.apollo_client_id}"
        f"&redirect_uri={settings.apollo_redirect_uri}"
        f"&response_type=code"
        f"&state=csrf_security_state"
    )
    return RedirectResponse(url=url)


@router.get("/auth/apollo/callback")
async def apollo_oauth_callback(
    code: str = Query(...),
    state: str = Query(None)
):
    """Receive the callback auth code, exchange it for access token, and save it."""
    if not settings.apollo_client_id or not settings.apollo_client_secret:
        raise HTTPException(status_code=400, detail="OAuth credentials not fully configured in .env")

    exchange_url = "https://app.apollo.io/api/v1/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.apollo_client_id,
        "client_secret": settings.apollo_client_secret,
        "code": code,
        "redirect_uri": settings.apollo_redirect_uri
    }
    
    logger.info(f"Exchanging OAuth code for token at {exchange_url}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(exchange_url, json=payload)
            if resp.status_code != 200:
                logger.error(f"OAuth token exchange failed: {resp.status_code} - {resp.text}")
                raise HTTPException(status_code=400, detail=f"Token exchange failed: {resp.text}")
                
            token_data = resp.json()
            
            with open(TOKEN_FILE, "w") as f:
                json.dump(token_data, f, indent=2)
                
            logger.info("Successfully received and saved Apollo OAuth token.")
            
            frontend_url = settings.frontend_url or "http://localhost:5173"
            return RedirectResponse(url=f"{frontend_url}/?oauth_success=true")
            
        except Exception as e:
            logger.exception("Exception during token exchange")
            raise HTTPException(status_code=500, detail=str(e))

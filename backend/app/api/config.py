from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import httpx

from backend.app.database import get_db
from backend.app import models, security
from backend.app.api.auth import get_current_user
from backend.core.onelap_client import OnelapClient
from backend.core.strava_cookie_client import StravaCookieClient

router = APIRouter(prefix="/api/config", tags=["Config"])

class ConfigUpdateSchema(BaseModel):
    onelap_username: Optional[str] = None
    onelap_password: Optional[str] = None
    strava_mode: Optional[str] = "cookie"
    strava_cookie: Optional[str] = None
    strava_client_id: Optional[str] = None
    strava_client_secret: Optional[str] = None
    strava_refresh_token: Optional[str] = None
    auto_sync_enabled: Optional[bool] = True
    sync_interval_hours: Optional[int] = 6

class ConfigResponseSchema(BaseModel):
    onelap_username: Optional[str] = None
    has_onelap_password: bool = False
    strava_mode: str = "cookie"
    has_strava_cookie: bool = False
    strava_client_id: Optional[str] = None
    has_strava_client_secret: bool = False
    has_strava_refresh_token: bool = False
    strava_athlete_name: Optional[str] = None
    cookie_status: str = "untested"
    auto_sync_enabled: bool = True
    sync_interval_hours: int = 6
    last_sync_at: Optional[str] = None

class TokenExchangeRequest(BaseModel):
    client_id: str
    client_secret: str
    code: str

@router.get("", response_model=ConfigResponseSchema)
def get_config(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == current_user.id).first()
    if not cfg:
        cfg = models.AccountConfig(user_id=current_user.id)
        db.add(cfg)
        db.commit()

    client_id = security.decrypt_sensitive_data(cfg.strava_client_id_enc) if cfg.strava_client_id_enc else None

    return ConfigResponseSchema(
        onelap_username=cfg.onelap_username,
        has_onelap_password=bool(cfg.onelap_password_enc),
        strava_mode=cfg.strava_mode or "cookie",
        has_strava_cookie=bool(cfg.strava_cookie_enc),
        strava_client_id=client_id,
        has_strava_client_secret=bool(cfg.strava_client_secret_enc),
        has_strava_refresh_token=bool(cfg.strava_refresh_token_enc),
        strava_athlete_name=cfg.strava_athlete_name,
        cookie_status=cfg.cookie_status or "untested",
        auto_sync_enabled=cfg.auto_sync_enabled if cfg.auto_sync_enabled is not None else True,
        sync_interval_hours=cfg.sync_interval_hours or 6,
        last_sync_at=cfg.last_sync_at.isoformat() if cfg.last_sync_at else None
    )

@router.put("", response_model=ConfigResponseSchema)
def update_config(data: ConfigUpdateSchema, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == current_user.id).first()
    if not cfg:
        cfg = models.AccountConfig(user_id=current_user.id)
        db.add(cfg)

    if data.onelap_username is not None:
        cfg.onelap_username = data.onelap_username
    
    if data.onelap_password:
        cfg.onelap_password_enc = security.encrypt_sensitive_data(data.onelap_password)

    if data.strava_mode:
        cfg.strava_mode = data.strava_mode

    if data.strava_cookie:
        cfg.strava_cookie_enc = security.encrypt_sensitive_data(data.strava_cookie)
        cfg.cookie_status = "untested"

    if data.strava_client_id:
        cfg.strava_client_id_enc = security.encrypt_sensitive_data(data.strava_client_id)

    if data.strava_client_secret:
        cfg.strava_client_secret_enc = security.encrypt_sensitive_data(data.strava_client_secret)

    if data.strava_refresh_token:
        cfg.strava_refresh_token_enc = security.encrypt_sensitive_data(data.strava_refresh_token)

    if data.auto_sync_enabled is not None:
        cfg.auto_sync_enabled = data.auto_sync_enabled

    if data.sync_interval_hours:
        cfg.sync_interval_hours = data.sync_interval_hours

    db.commit()
    return get_config(current_user=current_user, db=db)

@router.post("/exchange-strava-token")
async def exchange_strava_token(data: TokenExchangeRequest, current_user: models.User = Depends(get_current_user)):
    payload = {
        "client_id": data.client_id,
        "client_secret": data.client_secret,
        "code": data.code,
        "grant_type": "authorization_code"
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post("https://www.strava.com/oauth/token", data=payload)
        if res.status_code == 200:
            res_json = res.json()
            refresh_token = res_json.get("refresh_token")
            athlete = res_json.get("athlete", {})
            athlete_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
            return {
                "success": True,
                "refresh_token": refresh_token,
                "athlete_name": athlete_name or "Strava User",
                "message": "成功换取 Refresh Token！已自动为您填入表格，点击“保存设置”即可生效。"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Strava Token 换取失败 (HTTP {res.status_code}): {res.text}")

@router.post("/test-onelap")
async def test_onelap(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == current_user.id).first()
    if not cfg or not cfg.onelap_username or not cfg.onelap_password_enc:
        raise HTTPException(status_code=400, detail="Onelap username or password not configured.")

    pwd = security.decrypt_sensitive_data(cfg.onelap_password_enc)
    async with OnelapClient(username=cfg.onelap_username, password=pwd) as client:
        try:
            await client.login()
            activities = await client.get_activities(limit=5)
            return {
                "success": True, 
                "message": f"Onelap authentication successful! Found {len(activities)} recent rides."
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Onelap login failed: {str(e)}")

@router.post("/test-strava")
async def test_strava(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == current_user.id).first()
    if not cfg or not cfg.strava_cookie_enc:
        raise HTTPException(status_code=400, detail="Strava cookie session not configured.")

    cookie = security.decrypt_sensitive_data(cfg.strava_cookie_enc)
    client = StravaCookieClient(cookie)
    result = await client.validate_session()
    
    if result.get("valid"):
        cfg.cookie_status = "valid"
        cfg.strava_athlete_name = result.get("athlete_name")
        db.commit()
        return {
            "success": True,
            "message": f"Strava session cookie is valid! Logged in as: {result.get('athlete_name')}"
        }
    else:
        cfg.cookie_status = "expired"
        db.commit()
        raise HTTPException(status_code=400, detail=f"Strava session invalid: {result.get('reason')}")

class PlatformExchangeRequest(BaseModel):
    code: str

@router.post("/exchange-platform-token")
def exchange_platform_token(req: PlatformExchangeRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    from backend.app.config import settings
    import requests
    
    if not settings.PLATFORM_STRAVA_CLIENT_ID or not settings.PLATFORM_STRAVA_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Platform API is not configured on the server")
        
    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": settings.PLATFORM_STRAVA_CLIENT_ID,
        "client_secret": settings.PLATFORM_STRAVA_CLIENT_SECRET,
        "code": req.code,
        "grant_type": "authorization_code"
    }
    
    resp = requests.post(url, data=payload)
    if resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Strava Exchange Failed: {resp.text}")
        
    data = resp.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Strava response missing refresh_token")
        
    user_config = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == current_user.id).first()
    if not user_config:
        user_config = models.AccountConfig(user_id=current_user.id)
        db.add(user_config)
        
    user_config.strava_mode = "api"
    # Clear the custom keys so it defaults to Platform key
    user_config.strava_client_id = None
    user_config.strava_client_secret = None
    
    from backend.core.security import encrypt_token
    user_config.strava_refresh_token_encrypted = encrypt_token(refresh_token)
    
    db.commit()
    return {"status": "success", "message": "Platform API authorized successfully!"}

@router.get("/oauth-url")
def get_oauth_url(request: Request):
    from backend.app.config import settings
    if not settings.PLATFORM_STRAVA_CLIENT_ID:
        return {"url": None}
    
    # We construct the oauth url and set the redirect_uri to the origin of the request
    # If there's a proxy, request.base_url might be tricky, but we can try to guess or just use origin headers
    origin = request.headers.get("origin") or request.headers.get("referer") or str(request.base_url)
    if origin.endswith("/"):
        origin = origin[:-1]
    
    # ensure it's http/https
    if not origin.startswith("http"):
        origin = str(request.base_url).strip("/")
        
    url = f"https://www.strava.com/oauth/authorize?client_id={settings.PLATFORM_STRAVA_CLIENT_ID}&response_type=code&redirect_uri={origin}&approval_prompt=force&scope=read,activity:write,activity:read_all"
    return {"url": url}

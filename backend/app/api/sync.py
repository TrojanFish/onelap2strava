import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.app.database import get_db
from backend.app import models
from backend.app.api.auth import get_current_user
from backend.app.scheduler import run_sync_for_user

router = APIRouter(prefix="/api/sync", tags=["Sync"])

class SyncSummaryResponse(BaseModel):
    total_synced: int
    total_failed: int
    total_activities: int
    last_sync_at: Optional[str] = None
    cookie_status: str
    auto_sync_enabled: bool = True
    sync_interval_hours: int = 6

@router.post("/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cfg = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == current_user.id).first()
    if not cfg or not cfg.onelap_username or not cfg.onelap_password_enc:
        raise HTTPException(status_code=400, detail="Please configure Onelap credentials first.")

    if cfg.strava_mode == "cookie" and not cfg.strava_cookie_enc:
        raise HTTPException(status_code=400, detail="Please configure Strava session cookie first.")

    background_tasks.add_task(run_sync_for_user, current_user.id)
    return {"message": "Sync task initiated! Background process is running."}

@router.get("/summary", response_model=SyncSummaryResponse)
def get_sync_summary(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    cfg = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == current_user.id).first()
    
    total_synced = db.query(models.SyncedActivity).filter(
        models.SyncedActivity.user_id == current_user.id,
        models.SyncedActivity.sync_status == "SUCCESS"
    ).count()

    total_failed = db.query(models.SyncedActivity).filter(
        models.SyncedActivity.user_id == current_user.id,
        models.SyncedActivity.sync_status == "FAILED"
    ).count()

    total_activities = db.query(models.SyncedActivity).filter(
        models.SyncedActivity.user_id == current_user.id
    ).count()

    auto_sync = cfg.auto_sync_enabled if (cfg and cfg.auto_sync_enabled is not None) else True
    interval = cfg.sync_interval_hours if (cfg and cfg.sync_interval_hours) else 6

    return SyncSummaryResponse(
        total_synced=total_synced,
        total_failed=total_failed,
        total_activities=total_activities,
        last_sync_at=cfg.last_sync_at.isoformat() if (cfg and cfg.last_sync_at) else None,
        cookie_status=cfg.cookie_status if cfg else "untested",
        auto_sync_enabled=auto_sync,
        sync_interval_hours=interval
    )

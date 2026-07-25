from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from backend.app.database import get_db
from backend.app import models
from backend.app.api.auth import get_current_user

router = APIRouter(prefix="/api/logs", tags=["Logs"])

class SyncedActivitySchema(BaseModel):
    id: int
    onelap_activity_id: str
    strava_activity_id: Optional[str] = None
    title: Optional[str] = None
    sync_status: str
    error_message: Optional[str] = None
    synced_at: str

class SyncLogSchema(BaseModel):
    id: int
    level: str
    message: str
    timestamp: str

@router.get("/activities", response_model=List[SyncedActivitySchema])
def get_activity_logs(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.SyncedActivity).filter(models.SyncedActivity.user_id == current_user.id)
    if status:
        query = query.filter(models.SyncedActivity.sync_status == status)
    
    records = query.order_by(models.SyncedActivity.synced_at.desc()).limit(limit).all()
    
    return [
        SyncedActivitySchema(
            id=r.id,
            onelap_activity_id=r.onelap_activity_id,
            strava_activity_id=r.strava_activity_id,
            title=r.title or "Cycling Activity",
            sync_status=r.sync_status,
            error_message=r.error_message,
            synced_at=r.synced_at.isoformat() if r.synced_at else ""
        ) for r in records
    ]

@router.get("/messages", response_model=List[SyncLogSchema])
def get_log_messages(
    limit: int = Query(50, le=200),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = db.query(models.SyncLog).filter(
        models.SyncLog.user_id == current_user.id
    ).order_by(models.SyncLog.timestamp.desc()).limit(limit).all()

    return [
        SyncLogSchema(
            id=r.id,
            level=r.level,
            message=r.message,
            timestamp=r.timestamp.isoformat() if r.timestamp else ""
        ) for r in records
    ]

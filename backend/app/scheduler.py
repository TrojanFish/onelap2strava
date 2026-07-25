import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app import models, security
from backend.core.sync_engine import SyncEngine

logger = logging.getLogger(__name__)

_scheduler_task = None

async def run_sync_for_user(user_id: int):
    """
    Background job function to execute sync for a specific user.
    """
    db: Session = SessionLocal()
    try:
        config = db.query(models.AccountConfig).filter(models.AccountConfig.user_id == user_id).first()
        if not config or not config.onelap_username or not config.onelap_password_enc:
            logger.warning(f"User {user_id} sync skipped: Credentials incomplete.")
            return

        onelap_pwd = security.decrypt_sensitive_data(config.onelap_password_enc)
        strava_cookie = security.decrypt_sensitive_data(config.strava_cookie_enc)
        strava_client_id = security.decrypt_sensitive_data(config.strava_client_id_enc)
        strava_client_secret = security.decrypt_sensitive_data(config.strava_client_secret_enc)
        strava_refresh_token = security.decrypt_sensitive_data(config.strava_refresh_token_enc)

        existing_records = db.query(models.SyncedActivity).filter(
            models.SyncedActivity.user_id == user_id,
            models.SyncedActivity.sync_status == "SUCCESS"
        ).all()
        synced_ids = {r.onelap_activity_id for r in existing_records}

        engine = SyncEngine(
            user_id=user_id,
            onelap_username=config.onelap_username,
            onelap_password=onelap_pwd,
            strava_mode=config.strava_mode or "cookie",
            strava_cookie=strava_cookie,
            strava_client_id=strava_client_id,
            strava_client_secret=strava_client_secret,
            strava_refresh_token=strava_refresh_token,
            synced_activity_ids=synced_ids
        )

        results = await engine.execute_sync(limit=15)

        for item in results.get("activities", []):
            act_id = item["id"]
            existing = db.query(models.SyncedActivity).filter(
                models.SyncedActivity.user_id == user_id,
                models.SyncedActivity.onelap_activity_id == act_id
            ).first()

            if not existing:
                record = models.SyncedActivity(
                    user_id=user_id,
                    onelap_activity_id=act_id,
                    strava_activity_id=item.get("strava_id"),
                    title=item.get("title"),
                    sync_status=item.get("status"),
                    error_message=item.get("error"),
                    synced_at=datetime.utcnow()
                )
                db.add(record)
            else:
                existing.sync_status = item.get("status")
                existing.strava_activity_id = item.get("strava_id") or existing.strava_activity_id
                existing.error_message = item.get("error")

        for log_item in results.get("logs", []):
            db_log = models.SyncLog(
                user_id=user_id,
                level=log_item.get("level", "INFO"),
                message=log_item.get("message"),
                timestamp=datetime.utcnow()
            )
            db.add(db_log)

        config.last_sync_at = datetime.utcnow()
        db.commit()

        logger.info(f"Background sync job completed for user {user_id}")
    except Exception as e:
        logger.exception(f"Error in background sync for user {user_id}: {e}")
        db.rollback()
    finally:
        db.close()

async def scheduled_all_users_loop():
    """
    Periodically check all users and trigger sync if interval has elapsed.
    """
    while True:
        try:
            db: Session = SessionLocal()
            try:
                configs = db.query(models.AccountConfig).filter(models.AccountConfig.auto_sync_enabled == True).all()
                now = datetime.utcnow()
                for cfg in configs:
                    interval = timedelta(hours=cfg.sync_interval_hours or 6)
                    if not cfg.last_sync_at or (now - cfg.last_sync_at) >= interval:
                        asyncio.create_task(run_sync_for_user(cfg.user_id))
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error checking scheduled syncs: {e}")
        
        await asyncio.sleep(900)  # Check every 15 minutes

def start_scheduler():
    global _scheduler_task
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()
        scheduler.add_job(scheduled_all_users_loop, "interval", minutes=15, id="all_users_sync_check", replace_existing=True)
        scheduler.start()
        logger.info("APScheduler started.")
    except ImportError:
        logger.info("APScheduler not found, starting native asyncio background loop.")
        _scheduler_task = asyncio.create_task(scheduled_all_users_loop())

def stop_scheduler():
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()

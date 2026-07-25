import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.core.onelap_client import OnelapClient
from backend.core.strava_cookie_client import StravaCookieClient
from backend.core.strava_api_client import StravaApiClient

logger = logging.getLogger(__name__)

class SyncEngine:
    def __init__(
        self,
        user_id: int,
        onelap_username: str,
        onelap_password: str,
        strava_mode: str = "cookie",
        strava_cookie: Optional[str] = None,
        strava_client_id: Optional[str] = None,
        strava_client_secret: Optional[str] = None,
        strava_refresh_token: Optional[str] = None,
        synced_activity_ids: Optional[set] = None
    ):
        self.user_id = user_id
        self.onelap_username = onelap_username
        self.onelap_password = onelap_password
        self.strava_mode = strava_mode
        self.strava_cookie = strava_cookie
        self.strava_client_id = strava_client_id
        self.strava_client_secret = strava_client_secret
        self.strava_refresh_token = strava_refresh_token
        self.synced_activity_ids = synced_activity_ids or set()

    async def execute_sync(self, limit: int = 15) -> Dict[str, Any]:
        results = {
            "user_id": self.user_id,
            "total_found": 0,
            "synced_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "activities": [],
            "logs": []
        }

        def log_msg(level: str, msg: str):
            logger.info(f"[User {self.user_id}] {msg}")
            results["logs"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": msg
            })

        log_msg("INFO", f"Starting sync job (Mode: {self.strava_mode})...")

        async with OnelapClient(username=self.onelap_username, password=self.onelap_password) as onelap:
            try:
                await onelap.login()
                activities = await onelap.get_activities(limit=limit)
                results["total_found"] = len(activities)
                log_msg("INFO", f"Fetched {len(activities)} activities from Onelap.")
            except Exception as e:
                err_msg = f"Failed to login or fetch activities from Onelap: {e}"
                log_msg("ERROR", err_msg)
                results["error"] = err_msg
                return results

            for act in activities:
                act_id = act["id"]
                title = act.get("title", "Onelap Ride")
                
                if act_id in self.synced_activity_ids:
                    results["skipped_count"] += 1
                    log_msg("INFO", f"Skipping activity '{title}' ({act_id}) - already synced.")
                    results["activities"].append({
                        "id": act_id,
                        "title": title,
                        "status": "SKIPPED",
                        "reason": "Already synced"
                    })
                    continue

                log_msg("INFO", f"Downloading FIT file for '{title}' (ID: {act_id})...")
                try:
                    fit_bytes = await onelap.download_fit_file(act_id, fit_url=act.get("fit_url"))
                except Exception as e:
                    results["failed_count"] += 1
                    log_msg("ERROR", f"Failed downloading FIT file for '{title}': {e}")
                    results["activities"].append({
                        "id": act_id,
                        "title": title,
                        "status": "FAILED",
                        "error": str(e)
                    })
                    continue

                upload_res = None
                if self.strava_mode == "cookie":
                    if not self.strava_cookie:
                        log_msg("ERROR", "Strava cookie string is missing or not set!")
                        results["failed_count"] += 1
                        results["activities"].append({
                            "id": act_id,
                            "title": title,
                            "status": "FAILED",
                            "error": "Strava cookie missing"
                        })
                        continue

                    cookie_client = StravaCookieClient(self.strava_cookie)
                    filename = f"onelap_{act_id}.fit"
                    upload_res = await cookie_client.upload_fit(fit_bytes, filename=filename, activity_name=title)

                elif self.strava_mode == "api":
                    if not all([self.strava_client_id, self.strava_client_secret, self.strava_refresh_token]):
                        log_msg("ERROR", "Strava API credentials incomplete!")
                        results["failed_count"] += 1
                        results["activities"].append({
                            "id": act_id,
                            "title": title,
                            "status": "FAILED",
                            "error": "Strava API credentials incomplete"
                        })
                        continue

                    api_client = StravaApiClient(
                        client_id=self.strava_client_id,
                        client_secret=self.strava_client_secret,
                        refresh_token=self.strava_refresh_token
                    )
                    filename = f"onelap_{act_id}.fit"
                    upload_res = await api_client.upload_fit(fit_bytes, filename=filename, activity_name=title)

                if upload_res and upload_res.get("success"):
                    results["synced_count"] += 1
                    strava_act_id = upload_res.get("strava_activity_id")
                    log_msg("INFO", f"Successfully synced '{title}' to Strava! (Strava ID: {strava_act_id or 'N/A'})")
                    results["activities"].append({
                        "id": act_id,
                        "title": title,
                        "status": "SUCCESS",
                        "strava_id": strava_act_id
                    })
                    self.synced_activity_ids.add(act_id)
                else:
                    results["failed_count"] += 1
                    err_text = upload_res.get("error") if upload_res else "Unknown upload error"
                    log_msg("ERROR", f"Failed uploading '{title}' to Strava: {err_text}")
                    results["activities"].append({
                        "id": act_id,
                        "title": title,
                        "status": "FAILED",
                        "error": err_text
                    })

                await asyncio.sleep(3.0)

        log_msg("INFO", f"Sync completed! Synced: {results['synced_count']}, Skipped: {results['skipped_count']}, Failed: {results['failed_count']}")
        return results

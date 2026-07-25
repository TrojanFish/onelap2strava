import re
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class StravaCookieClient:
    BASE_URL = "https://www.strava.com"

    def __init__(self, cookie_str: str):
        clean_cookie = cookie_str.strip()
        if "_strava4_session=" not in clean_cookie and not clean_cookie.startswith("Cookie:"):
            clean_cookie = f"_strava4_session={clean_cookie}"
        self.cookie_header = clean_cookie.replace("Cookie:", "").strip()

    def _get_headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Cookie": self.cookie_header,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if extra:
            headers.update(extra)
        return headers

    async def validate_session(self) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/dashboard"
        async with httpx.AsyncClient(follow_redirects=False, timeout=15.0) as client:
            try:
                response = await client.get(url, headers=self._get_headers())
                if response.status_code == 200:
                    html = response.text
                    athlete_match = re.search(r'class="athlete-name"[^>]*>([^<]+)<', html)
                    athlete_name = athlete_match.group(1).strip() if athlete_match else "Strava User"
                    return {"valid": True, "athlete_name": athlete_name}
                elif response.status_code in (301, 302) and "login" in response.headers.get("location", "").lower():
                    return {"valid": False, "reason": "Session cookie expired or invalid"}
                else:
                    return {"valid": False, "reason": f"Strava returned HTTP status {response.status_code}"}
            except Exception as e:
                logger.error(f"Error validating Strava cookie: {e}")
                return {"valid": False, "reason": str(e)}

    async def upload_fit(
        self, 
        fit_content: bytes, 
        filename: str = "activity.fit", 
        activity_name: Optional[str] = None
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            try:
                select_url = f"{self.BASE_URL}/upload/select"
                res_page = await client.get(select_url, headers=self._get_headers())
                
                if res_page.status_code != 200 or "login" in str(res_page.url).lower():
                    return {"success": False, "error": "Strava session expired. Please update your session cookie."}

                html = res_page.text
                csrf_token = ""
                meta_match = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
                if meta_match:
                    csrf_token = meta_match.group(1)

                upload_url = f"{self.BASE_URL}/upload/files"
                upload_headers = self._get_headers({
                    "X-CSRF-Token": csrf_token,
                    "X-Requested-With": "XMLHttpRequest",
                    "Accept": "application/json, text/javascript, */*; q=0.01"
                })

                files = {"files[]": (filename, fit_content, "application/octet-stream")}
                data = {"authenticity_token": csrf_token, "data_type": "fit", "activity_type": "Ride"}
                if activity_name:
                    data["name"] = activity_name

                upload_res = await client.post(upload_url, headers=upload_headers, data=data, files=files)
                
                if upload_res.status_code in (200, 201, 202):
                    res_json = upload_res.json()
                    upload_id = res_json.get("id") or res_json.get("upload_id") or res_json.get("workflow_id")
                    if upload_id:
                        return await self._poll_upload_status(client, str(upload_id))
                    else:
                        return {"success": True, "message": "File uploaded to Strava successfully", "strava_activity_id": None}
                else:
                    return {"success": False, "error": f"Strava upload HTTP {upload_res.status_code}: {upload_res.text[:200]}"}
            except Exception as e:
                logger.exception(f"Exception during Strava cookie upload: {e}")
                return {"success": False, "error": str(e)}

    async def _poll_upload_status(self, client: httpx.AsyncClient, upload_id: str, max_retries: int = 15) -> Dict[str, Any]:
        status_url = f"{self.BASE_URL}/upload/status/{upload_id}"
        poll_headers = self._get_headers({"X-Requested-With": "XMLHttpRequest"})

        for attempt in range(max_retries):
            await asyncio.sleep(2.0)
            try:
                res = await client.get(status_url, headers=poll_headers)
                if res.status_code == 200:
                    data = res.json()
                    status = data.get("status")
                    if status == "Your activity is ready.":
                        activity_id = data.get("activity_id")
                        return {"success": True, "strava_activity_id": str(activity_id) if activity_id else None, "message": "Activity synced to Strava!"}
                    elif "error" in data or status == "There was an error processing your activity.":
                        err_msg = data.get("error") or data.get("message") or "Strava processing error"
                        return {"success": False, "error": err_msg}
            except Exception as e:
                logger.warning(f"Poll upload status exception (attempt {attempt+1}): {e}")

        return {"success": True, "strava_activity_id": None, "message": "Upload initiated, processing in background."}

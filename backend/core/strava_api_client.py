import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class StravaApiClient:
    API_BASE = "https://www.strava.com/api/v3"
    OAUTH_URL = "https://www.strava.com/oauth/token"

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token: Optional[str] = None

    async def get_access_token(self) -> str:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(self.OAUTH_URL, data=payload)
            if res.status_code == 200:
                data = res.json()
                self.access_token = data.get("access_token")
                return self.access_token
            else:
                raise Exception(f"Failed to refresh Strava access token: HTTP {res.status_code}")

    async def upload_fit(self, fit_content: bytes, filename: str = "activity.fit", activity_name: Optional[str] = None) -> Dict[str, Any]:
        if not self.access_token:
            await self.get_access_token()

        url = f"{self.API_BASE}/uploads"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        files = {"file": (filename, fit_content, "application/octet-stream")}
        data = {"data_type": "fit", "activity_type": "ride"}
        if activity_name:
            data["name"] = activity_name

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=headers, data=data, files=files)
            if res.status_code in (200, 201):
                data = res.json()
                return {"success": True, "strava_activity_id": str(data.get("id")), "message": "Upload successful"}
            else:
                return {"success": False, "error": f"Strava API error HTTP {res.status_code}: {res.text}"}

import logging
import hashlib
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class OnelapClient:
    BASE_URL = "https://u.onelap.cn"
    API_URL = "https://www.onelap.cn/api"

    def __init__(self, username: str = "", password: str = "", token: Optional[str] = None):
        self.username = username
        self.password = password
        self.token = token
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _hash_password(self, pwd: str) -> str:
        return hashlib.md5(pwd.encode('utf-8')).hexdigest()

    async def login(self) -> bool:
        if self.token:
            return True

        if not self.username or not self.password:
            raise ValueError("Username and password are required for Onelap login")

        url = f"{self.BASE_URL}/api/login"
        payload = {
            "account": self.username,
            "password": self._hash_password(self.password),
            "source": "web"
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = await self.client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 200 or data.get("status") == 0:
                    token_data = data.get("data", {})
                    self.token = token_data.get("token") or token_data.get("accessToken")
                    logger.info(f"Onelap login successful for user: {self.username}")
                    return True
                else:
                    msg = data.get("msg") or data.get("message") or "Unknown error"
                    logger.error(f"Onelap login failed: {msg}")
                    raise Exception(f"Onelap login failed: {msg}")
            else:
                logger.error(f"Onelap login HTTP {response.status_code}")
                raise Exception(f"Onelap server returned status {response.status_code}")
        except Exception as e:
            logger.exception(f"Error logging into Onelap: {e}")
            raise

    async def get_activities(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.token:
            await self.login()

        url = f"{self.BASE_URL}/api/v1/workout/list"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "token": self.token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        params = {"page": 1, "limit": limit}

        try:
            response = await self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                records = data.get("data", {}).get("list", []) or data.get("data", [])
                formatted = []
                for item in records:
                    formatted.append({
                        "id": str(item.get("id") or item.get("workoutId") or item.get("logId")),
                        "title": item.get("title") or item.get("name") or "Onelap Indoor Cycling",
                        "start_time": item.get("startTime") or item.get("created_at"),
                        "distance_km": round((item.get("distance", 0) or 0) / 1000.0, 2),
                        "duration_sec": item.get("duration", 0) or item.get("elapsedTime", 0),
                        "fit_url": item.get("fitUrl") or item.get("downloadUrl") or item.get("fit_file"),
                    })
                return formatted
            else:
                logger.error(f"Failed to fetch Onelap activities: HTTP {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Exception fetching Onelap activities: {e}")
            raise

    async def download_fit_file(self, activity_id: str, fit_url: Optional[str] = None) -> bytes:
        if not self.token:
            await self.login()

        download_target = fit_url or f"{self.BASE_URL}/api/v1/workout/download?id={activity_id}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "token": self.token,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = await self.client.get(download_target, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Failed to download FIT file for activity {activity_id}: HTTP {response.status_code}")

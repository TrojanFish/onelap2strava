import os
import secrets
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "Onelap2Strava Sync WebApp"
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "u234567890123456789012345678901234567890123=")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./onelap2strava.db")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

settings = Settings()

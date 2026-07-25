from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    config = relationship("AccountConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    activities = relationship("SyncedActivity", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("SyncLog", back_populates="user", cascade="all, delete-orphan")

class AccountConfig(Base):
    __tablename__ = "account_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Onelap Credentials
    onelap_username = Column(String(100), nullable=True)
    onelap_password_enc = Column(Text, nullable=True)
    
    # Strava Configuration
    strava_mode = Column(String(20), default="cookie")  # 'cookie' or 'api'
    strava_cookie_enc = Column(Text, nullable=True)
    strava_athlete_name = Column(String(100), nullable=True)
    cookie_status = Column(String(20), default="untested")  # 'valid', 'expired', 'untested'
    
    # Strava API Credentials (Optional fallback)
    strava_client_id_enc = Column(Text, nullable=True)
    strava_client_secret_enc = Column(Text, nullable=True)
    strava_refresh_token_enc = Column(Text, nullable=True)
    
    # Sync Settings
    auto_sync_enabled = Column(Boolean, default=True)
    sync_interval_hours = Column(Integer, default=6)
    last_sync_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="config")

class SyncedActivity(Base):
    __tablename__ = "synced_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    onelap_activity_id = Column(String(100), nullable=False, index=True)
    strava_activity_id = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)
    start_time = Column(String(50), nullable=True)
    distance_km = Column(String(20), nullable=True)
    duration_sec = Column(Integer, nullable=True)
    sync_status = Column(String(20), default="PENDING")
    error_message = Column(Text, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="activities")

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")

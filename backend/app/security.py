import base64
from datetime import datetime, timedelta
from typing import Optional, Any
from passlib.context import CryptContext
from jose import jwt, JWTError
from cryptography.fernet import Fernet
import hashlib

from backend.app.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
ALGORITHM = "HS256"

def _get_fernet_key() -> bytes:
    key_material = settings.ENCRYPTION_KEY or settings.SECRET_KEY
    key_bytes = hashlib.sha256(key_material.encode()).digest()
    return base64.urlsafe_b64encode(key_bytes)

fernet = Fernet(_get_fernet_key())

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password[:72])

def encrypt_sensitive_data(plain_text: Optional[str]) -> Optional[str]:
    """Encrypt password or cookie string for database storage."""
    if not plain_text:
        return None
    encrypted_bytes = fernet.encrypt(plain_text.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_sensitive_data(cipher_text: Optional[str]) -> Optional[str]:
    """Decrypt password or cookie string from database storage."""
    if not cipher_text:
        return None
    try:
        decrypted_bytes = fernet.decrypt(cipher_text.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception:
        return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

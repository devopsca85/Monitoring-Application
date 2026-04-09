import base64
import os
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jose import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def _get_fernet() -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"monitoring-salt-v1",
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(
        kdf.derive(settings.CREDENTIAL_ENCRYPTION_KEY.encode())
    )
    return Fernet(key)


def encrypt_credential(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_credential(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

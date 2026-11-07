import hashlib
import secrets
from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from . import models
from .db import get_db

TOKEN_TTL_SECONDS = 3600

password_hasher = PasswordHasher()  # Argon2id
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def new_secret() -> str:
    """Random token or API key, 43 characters."""
    return secrets.token_urlsafe(32)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def unauthorized(detail: str):
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})


def current_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: DbSession = Depends(get_db),
) -> models.Session:
    if credentials is None:
        raise unauthorized("Missing bearer token")
    session = db.scalar(select(models.Session).where(models.Session.token_hash == sha256(credentials.credentials)))
    if session is None or session.expires_at <= datetime.now(timezone.utc):
        raise unauthorized("Invalid or expired token")
    return session


def current_sensor(
    api_key: str | None = Depends(api_key_scheme),
    db: DbSession = Depends(get_db),
) -> models.Sensor:
    if not api_key:
        raise HTTPException(401, "Missing X-API-Key header")
    sensor = db.scalar(select(models.Sensor).where(models.Sensor.api_key_hash == sha256(api_key)))
    if sensor is None:
        raise HTTPException(401, "Invalid sensor API key")
    return sensor

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings
from .errors import ApiError


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "TOKEN_EXPIRED", "Session expired. Please sign in again.")
    except jwt.PyJWTError:
        raise ApiError(401, "TOKEN_INVALID", "Invalid token.")
    if payload.get("type") != "access":
        raise ApiError(401, "TOKEN_INVALID", "Invalid token.")
    return payload


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def generate_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_otp(code: str, phone: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()

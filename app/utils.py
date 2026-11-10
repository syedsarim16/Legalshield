import re
import uuid
from datetime import datetime, timezone

from .errors import ApiError


def utcnow() -> datetime:
    """Return an aware UTC timestamp compatible with Firestore."""
    return datetime.now(timezone.utc)


def normalize_utc(value: datetime) -> datetime:
    """Normalize aware or legacy-naive datetimes to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return normalize_utc(dt).replace(tzinfo=None, microsecond=0).isoformat() + "Z"


CNIC_RE = re.compile(r"^\d{5}-\d{7}-\d$")


def validate_cnic(value: str) -> str:
    value = value.strip()
    if not CNIC_RE.match(value):
        raise ApiError(422, "INVALID_CNIC", "CNIC must look like 12345-1234567-1.")
    return value


def mask_cnic(value: str | None) -> str | None:
    return None if not value else "*****-*******-" + value[-1]


def normalize_phone(raw: str) -> str:
    """Pakistani mobile numbers only. Returns +923XXXXXXXXX."""
    p = re.sub(r"[\s\-()]", "", raw or "")
    if p.startswith("+92"):
        rest = p[3:]
    elif p.startswith("0092"):
        rest = p[4:]
    elif p.startswith("92") and len(p) == 12:
        rest = p[2:]
    elif p.startswith("0"):
        rest = p[1:]
    else:
        rest = p
    if not re.fullmatch(r"3\d{9}", rest):
        raise ApiError(422, "INVALID_PHONE", "Enter a valid Pakistani mobile number, e.g. 0300 1234567.")
    return "+92" + rest


def validate_password(pw: str) -> str:
    if len(pw) < 8 or len(pw.encode()) > 72:
        raise ApiError(422, "WEAK_PASSWORD", "Password must be 8 to 72 characters.")
    return pw

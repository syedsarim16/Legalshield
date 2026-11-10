from datetime import timedelta

from ..config import settings
from ..firebase import create_custom_token
from ..models import RefreshToken, User
from ..security import create_access_token, new_refresh_token
from ..utils import utcnow


def issue_token_pair(db, user: User, include_firebase_custom_token: bool = True) -> dict:
    raw, hashed = new_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=hashed, expires_at=utcnow() + timedelta(days=settings.refresh_token_days)))
    db.commit()
    result = {
        "access_token": create_access_token(user.id, user.role),
        "refresh_token": raw,
        "token_type": "bearer",
        "expires_in": settings.access_token_minutes * 60,
    }
    if include_firebase_custom_token:
        result["firebase_custom_token"] = create_custom_token(user.id)
    return result

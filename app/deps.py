from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import get_db
from .errors import ApiError
from .firebase import verify_id_token
from .models import FirebaseIdentity, User

_bearer = HTTPBearer(auto_error=False)


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer), db=Depends(get_db)
) -> User | None:
    if creds is None:
        return None
    claims = verify_id_token(creds.credentials)
    uid = str(claims.get("uid") or claims.get("sub") or "")
    if not uid:
        raise ApiError(401, "FIREBASE_TOKEN_INVALID", "Firebase sign-in could not be verified.")
    user = db.get(User, uid)
    if user is None:
        identity = db.get(FirebaseIdentity, uid)
        if identity:
            user = db.get(User, identity.user_id)
    if user is None:
        raise ApiError(401, "TOKEN_INVALID", "Account no longer exists.")
    return user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "Sign in required.")
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "Your account type cannot use this feature.")
        return user

    return dep

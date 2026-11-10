"""Firebase Admin integration.

The checked-in google-services file is a public Android client configuration.
Server-side Firebase Admin operations require a service-account credential,
provided through FIREBASE_SERVICE_ACCOUNT_JSON or
GOOGLE_APPLICATION_CREDENTIALS.
"""
import base64
import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from .config import settings
from .errors import ApiError

log = logging.getLogger("legalshield.firebase")
ROOT = Path(__file__).resolve().parent.parent
ID_TOKEN_CLOCK_SKEW_SECONDS = 5

try:  # Optional locally so the existing offline test environment still boots.
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials, firestore, messaging, storage
except ImportError:  # pragma: no cover - exercised only without the optional dependency
    firebase_admin = None
    firebase_auth = credentials = firestore = messaging = storage = None


def _google_services_path() -> Path:
    configured = Path(settings.firebase_google_services_file)
    return configured if configured.is_absolute() else ROOT / configured


@lru_cache(maxsize=1)
def public_config() -> dict:
    """Build a browser-safe Firebase config from google-services.json."""
    path = _google_services_path()
    if not path.exists():
        return {"enabled": False}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        project = raw.get("project_info", {})
        client = (raw.get("client") or [{}])[0]
        info = client.get("client_info", {})
        api_keys = client.get("api_key") or []
        api_key = (api_keys[0] if api_keys else {}).get("current_key", "")
        project_id = project.get("project_id", "")
        project_number = project.get("project_number", "")
        app_id = info.get("mobilesdk_app_id", "")
        bucket = project.get("storage_bucket", "")
        if not all((api_key, project_id, project_number, app_id)):
            return {"enabled": False}
        return {
            "enabled": True,
            "apiKey": api_key,
            "authDomain": f"{project_id}.firebaseapp.com",
            "projectId": project_id,
            "storageBucket": bucket,
            "messagingSenderId": project_number,
            "appId": app_id,
            "vapidKey": settings.firebase_web_vapid_key,
        }
    except (OSError, ValueError, TypeError, KeyError) as exc:
        log.warning("Could not read Firebase client configuration: %s", exc)
        return {"enabled": False}


def _service_account_options() -> dict:
    raw = settings.firebase_service_account_json.strip()
    if raw:
        try:
            if raw.startswith("{"):
                return json.loads(raw)
            return json.loads(base64.b64decode(raw).decode("utf-8"))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeError("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON or base64 JSON") from exc
    path = (settings.google_application_credentials or os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")).strip()
    if path:
        if not Path(path).is_file():
            raise FileNotFoundError("GOOGLE_APPLICATION_CREDENTIALS does not point to an existing file.")
        return {"path": path}
    return {}


@lru_cache(maxsize=1)
def admin_ready() -> bool:
    if firebase_admin is None:
        return False
    try:
        if firebase_admin._apps:
            return True
        options = {}
        if public_config().get("projectId"):
            options["projectId"] = public_config()["projectId"]
        if settings.firebase_storage_bucket:
            options["storageBucket"] = settings.firebase_storage_bucket
        account = _service_account_options()
        if account.get("path"):
            cred = credentials.Certificate(account["path"])
        elif account:
            cred = credentials.Certificate(account)
        else:
            # Do not silently probe local metadata servers. Explicit server
            # credentials keep local development safe and predictable.
            return False
        if not options.get("storageBucket") and public_config().get("storageBucket"):
            options["storageBucket"] = public_config()["storageBucket"]
        firebase_admin.initialize_app(cred, options=options)
        return True
    except FileNotFoundError as exc:
        log.error("%s Configure GOOGLE_APPLICATION_CREDENTIALS with the path to your Firebase service-account JSON.", exc)
        return False
    except Exception as exc:
        log.error("Firebase Admin initialization failed (%s); check the service-account JSON and project configuration.", type(exc).__name__)
        return False


def verify_id_token(id_token: str) -> dict:
    if not admin_ready():
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase server credentials are not configured.")
    try:
        return firebase_auth.verify_id_token(
            id_token,
            check_revoked=True,
            clock_skew_seconds=ID_TOKEN_CLOCK_SKEW_SECONDS,
        )
    except Exception as exc:
        if firebase_auth is not None and isinstance(exc, firebase_auth.InvalidIdTokenError):
            log.warning("Firebase ID token verification failed (%s): %s", type(exc).__name__, exc)
        else:
            log.warning("Firebase ID token verification failed (%s).", type(exc).__name__)
        if isinstance(exc, firebase_auth.ExpiredIdTokenError):
            raise ApiError(401, "FIREBASE_TOKEN_EXPIRED", "Your Firebase session has expired. Please sign in again.") from exc
        if isinstance(exc, firebase_auth.RevokedIdTokenError):
            raise ApiError(401, "FIREBASE_TOKEN_REVOKED", "Your Firebase session was revoked. Please sign in again.") from exc
        raise ApiError(401, "FIREBASE_TOKEN_INVALID", "Firebase sign-in could not be verified.") from exc


def create_custom_token(uid: str) -> str:
    if not admin_ready() or firebase_auth is None:
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase server credentials are not configured.")
    try:
        try:
            firebase_auth.get_user(uid)
        except firebase_auth.UserNotFoundError:
            try:
                firebase_auth.create_user(uid=uid)
            except firebase_auth.UidAlreadyExistsError:
                pass
        token = firebase_auth.create_custom_token(uid)
        return token.decode("utf-8") if isinstance(token, bytes) else token
    except Exception as exc:
        log.error("Firebase custom token creation failed (%s).", type(exc).__name__)
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase authentication is temporarily unavailable.") from exc


def revoke_firebase_user(uid: str) -> None:
    if not admin_ready() or firebase_auth is None:
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase server credentials are not configured.")
    try:
        firebase_auth.revoke_refresh_tokens(uid)
    except Exception as exc:
        log.error("Firebase refresh-token revocation failed.")
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase sign-out could not be completed.") from exc


def firestore_client():
    if not admin_ready() or firestore is None:
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase server credentials are not configured.")
    try:
        return firestore.client()
    except Exception as exc:
        log.error("Firestore client initialization failed.")
        raise ApiError(503, "FIRESTORE_UNAVAILABLE", "Firestore is temporarily unavailable.") from exc


def upload_document(key: str, data: bytes, content_type: str | None = None) -> bool:
    if not admin_ready() or storage is None:
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase Storage is not configured.")
    try:
        blob = storage.bucket().blob(key)
        blob.upload_from_string(data, content_type=content_type or "application/octet-stream")
        return True
    except Exception as exc:
        log.error("Firebase Storage upload failed.")
        raise ApiError(503, "FIREBASE_STORAGE_UNAVAILABLE", "The verification document could not be stored.") from exc


def delete_document(key: str) -> None:
    if not key:
        return
    if not admin_ready() or storage is None:
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase Storage is not configured.")
    try:
        storage.bucket().blob(key).delete()
    except Exception as exc:
        log.error("Firebase Storage delete failed.")
        raise ApiError(503, "FIREBASE_STORAGE_UNAVAILABLE", "The verification document could not be deleted.") from exc


def delete_user_preferences(user_id: str) -> None:
    client = firestore_client()
    try:
        client.collection("user_preferences").document(user_id).delete()
    except Exception as exc:
        log.error("Firestore user preference deletion failed.")
        raise ApiError(503, "FIRESTORE_UNAVAILABLE", "Account preferences could not be deleted.") from exc


def delete_auth_user(firebase_uid: str) -> None:
    if not firebase_uid:
        return
    if not admin_ready() or firebase_auth is None:
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase server credentials are not configured.")
    try:
        firebase_auth.delete_user(firebase_uid)
    except firebase_auth.UserNotFoundError:
        return
    except Exception as exc:
        log.error("Firebase Auth user deletion failed.")
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "The Firebase account could not be deleted.") from exc


def send_push(tokens: list[str], title: str, body: str, data: dict | None = None) -> int:
    if not tokens or not admin_ready() or messaging is None:
        return 0
    try:
        result = messaging.send_each_for_multicast(
            messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(title=title, body=body),
                data={str(k): str(v) for k, v in (data or {}).items()},
            )
        )
        return result.success_count
    except Exception as exc:
        log.warning("Firebase Cloud Messaging failed: %s", exc)
        return 0

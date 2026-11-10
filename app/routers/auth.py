"""Module 1: registration, OTP, login, refresh, logout (E-01 .. E-06)."""
import secrets
from datetime import timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel, Field

from ..config import settings
from ..db import get_db, select, update
from ..deps import get_optional_user
from ..errors import ApiError
from ..firebase import delete_document, revoke_firebase_user, verify_id_token, upload_document
from ..models import FirebaseIdentity, LawyerProfile, NgoProfile, PasswordResetGrant, RefreshToken, User
from ..ratelimit import RateLimiter
from ..security import hash_password, hash_token, verify_password
from ..services.accounts import purge_user
from ..services.otp import issue_otp, verify_otp
from ..services.tokens import issue_token_pair
from ..utils import new_id, normalize_phone, utcnow, validate_cnic, validate_password

router = APIRouter(prefix="/auth", tags=["M1 Auth"])

login_limiter = RateLimiter(10, 600, "LOGIN_RATE_LIMITED", "Too many sign-in attempts. Try again in a few minutes.")
SELF_REGISTER_ROLES = {"citizen", "lawyer", "ngo_monitor"}


def _sniff_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"%PDF"):
        return "pdf"
    return None


def _save_document(upload: UploadFile) -> str:
    limit = settings.max_upload_mb * 1024 * 1024
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise ApiError(413, "FILE_TOO_LARGE", f"File must be {settings.max_upload_mb} MB or smaller.")
    ext = _sniff_extension(data)
    if ext is None:
        raise ApiError(422, "UNSUPPORTED_FILE_TYPE", "Upload a JPG, PNG or PDF.")
    key = f"verification/{new_id()}.{ext}"
    upload_document(key, data, upload.content_type)
    return key


def _split(values: list[str]) -> list[str]:
    out = []
    for v in values:
        out.extend(p.strip() for p in v.split(",") if p.strip())
    return out


@router.post("/register", status_code=201)  # E-01
def register(
    role: str = Form(...),
    full_name: str = Form(..., min_length=2, max_length=120),
    phone: str = Form(...),
    password: str = Form(...),
    cnic: Optional[str] = Form(None),
    bar_council_no: Optional[str] = Form(None),
    organisation_name: Optional[str] = Form(None),
    districts: list[str] = Form(default=[]),
    verification_document: Optional[UploadFile] = File(None),
    db=Depends(get_db),
):
    if role == "admin":
        raise ApiError(403, "ADMIN_REGISTRATION_FORBIDDEN", "Admin accounts cannot be created from the app.")
    if role not in SELF_REGISTER_ROLES:
        raise ApiError(422, "INVALID_ROLE", "Role must be citizen, lawyer or ngo_monitor.")
    phone_n = normalize_phone(phone)
    validate_password(password)
    cnic_n = validate_cnic(cnic) if cnic else None
    if role == "lawyer" and not (bar_council_no and bar_council_no.strip()):
        raise ApiError(422, "BAR_COUNCIL_REQUIRED", "Bar Council number is required for lawyers.")
    if role == "ngo_monitor" and not (organisation_name and organisation_name.strip() and _split(districts)):
        raise ApiError(422, "NGO_DETAILS_REQUIRED", "Organisation name and at least one district are required.")
    if role in ("lawyer", "ngo_monitor") and (verification_document is None or not verification_document.filename):
        raise ApiError(422, "DOCUMENT_REQUIRED", "Upload your licence or proof document.")

    existing = db.scalar(select(User).where(User.phone == phone_n))
    if existing is not None:
        if existing.phone_verified:
            raise ApiError(409, "PHONE_IN_USE", "This phone number is already registered.")
        purge_user(db, existing)  # abandoned, never-verified signup: let the owner start over

    doc_key = _save_document(verification_document) if role != "citizen" and verification_document else None
    try:
        user = User(
            role=role,
            full_name=full_name.strip(),
            phone=phone_n,
            cnic=cnic_n,
            password_hash=hash_password(password),
            verification_status="pending" if role in ("lawyer", "ngo_monitor") else "not_required",
            verification_document_key=doc_key,
        )
        db.add(user)
        db.flush()
        if role == "lawyer":
            db.add(LawyerProfile(user_id=user.id, bar_council_no=bar_council_no.strip(), contact_phone=phone_n))
        elif role == "ngo_monitor":
            db.add(NgoProfile(user_id=user.id, organisation_name=organisation_name.strip(), districts=_split(districts)))
        db.commit()
        code = issue_otp(db, phone_n, "register", user.id)
    except Exception:
        db.rollback()
        if doc_key:
            delete_document(doc_key)
        raise
    body = {"user_id": user.id, "role": user.role, "verification_status": user.verification_status, "otp_sent": True}
    if settings.debug_return_otp:
        body["dev_otp"] = code
    return body


def _firebase_identity(claims: dict) -> tuple[str, str]:
    uid = str(claims.get("uid") or "").strip()
    raw_phone = str(claims.get("phone_number") or "").strip()
    if not uid or not raw_phone:
        raise ApiError(422, "FIREBASE_PHONE_REQUIRED", "Firebase must provide a verified phone number.")
    phone = normalize_phone(raw_phone)
    return uid, phone


def _validate_firebase_registration(
    role: str,
    cnic: Optional[str],
    bar_council_no: Optional[str],
    organisation_name: Optional[str],
    districts: list[str],
    verification_document: Optional[UploadFile],
) -> tuple[Optional[str], list[str]]:
    if role == "admin":
        raise ApiError(403, "ADMIN_REGISTRATION_FORBIDDEN", "Admin accounts cannot be created from the app.")
    if role not in SELF_REGISTER_ROLES:
        raise ApiError(422, "INVALID_ROLE", "Role must be citizen, lawyer or ngo_monitor.")
    cnic_n = validate_cnic(cnic) if cnic else None
    districts_n = _split(districts)
    if role == "lawyer" and not (bar_council_no and bar_council_no.strip()):
        raise ApiError(422, "BAR_COUNCIL_REQUIRED", "Bar Council number is required for lawyers.")
    if role == "ngo_monitor" and not (organisation_name and organisation_name.strip() and districts_n):
        raise ApiError(422, "NGO_DETAILS_REQUIRED", "Organisation name and at least one district are required.")
    if role in ("lawyer", "ngo_monitor") and (verification_document is None or not verification_document.filename):
        raise ApiError(422, "DOCUMENT_REQUIRED", "Upload your licence or proof document.")
    return cnic_n, districts_n


class FirebaseExchange(BaseModel):
    id_token: str = Field(min_length=20)


@router.post("/firebase/exchange")
def firebase_exchange(body: FirebaseExchange, db=Depends(get_db)):
    """Exchange a verified Firebase Auth phone session for a LegalShield session."""
    uid, phone = _firebase_identity(verify_id_token(body.id_token))
    identity = db.get(FirebaseIdentity, uid)
    user = db.get(User, identity.user_id) if identity else db.scalar(select(User).where(User.phone == phone))
    if user is None:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "Create a LegalShield account first.")
    if user.phone != phone:
        raise ApiError(409, "PHONE_MISMATCH", "This Firebase phone does not match the LegalShield account.")
    if identity is None:
        db.add(FirebaseIdentity(firebase_uid=uid, user_id=user.id, provider="phone"))
    user.phone_verified = True
    db.commit()
    return {**issue_token_pair(db, user), "role": user.role, "verification_status": user.verification_status}


@router.post("/firebase/register", status_code=201)
def firebase_register(
    id_token: str = Form(...),
    role: str = Form(...),
    full_name: str = Form(..., min_length=2, max_length=120),
    password: str = Form(..., min_length=8, max_length=72),
    cnic: Optional[str] = Form(None),
    bar_council_no: Optional[str] = Form(None),
    organisation_name: Optional[str] = Form(None),
    districts: list[str] = Form(default=[]),
    verification_document: Optional[UploadFile] = File(None),
    db=Depends(get_db),
):
    """Create a LegalShield account after Firebase has verified the phone OTP."""
    uid, phone = _firebase_identity(verify_id_token(id_token))
    validate_password(password)
    cnic_n, districts_n = _validate_firebase_registration(
        role, cnic, bar_council_no, organisation_name, districts, verification_document
    )
    if db.get(FirebaseIdentity, uid) is not None:
        raise ApiError(409, "FIREBASE_ACCOUNT_EXISTS", "This Firebase account is already linked to LegalShield.")
    existing = db.scalar(select(User).where(User.phone == phone))
    if existing is not None:
        if existing.phone_verified:
            raise ApiError(409, "PHONE_IN_USE", "This phone number is already registered.")
        purge_user(db, existing)
    doc_key = _save_document(verification_document) if role != "citizen" and verification_document else None
    try:
        user = User(
            id=uid,
            role=role,
            full_name=full_name.strip(),
            phone=phone,
            cnic=cnic_n,
            # Firebase owns the phone factor, while the chosen password keeps
            # the existing password-login fallback available.
            password_hash=hash_password(password),
            phone_verified=True,
            verification_status="pending" if role in ("lawyer", "ngo_monitor") else "not_required",
            verification_document_key=doc_key,
        )
        db.add(user)
        db.flush()
        if role == "lawyer":
            db.add(LawyerProfile(user_id=user.id, bar_council_no=bar_council_no.strip(), contact_phone=phone))
        elif role == "ngo_monitor":
            db.add(NgoProfile(user_id=user.id, organisation_name=organisation_name.strip(), districts=districts_n))
        db.add(FirebaseIdentity(firebase_uid=uid, user_id=user.id, provider="phone"))
        db.commit()
    except Exception:
        db.rollback()
        if doc_key:
            delete_document(doc_key)
        raise
    return {**issue_token_pair(db, user), "user_id": user.id, "role": user.role, "verification_status": user.verification_status}


class OtpRequest(BaseModel):
    purpose: Literal["register", "reset", "change_phone"]
    phone: Optional[str] = None
    new_phone: Optional[str] = None
    current_password: Optional[str] = None


@router.post("/otp/request")  # E-02
def otp_request(body: OtpRequest, db=Depends(get_db), me: User | None = Depends(get_optional_user)):
    code = None
    if body.purpose == "change_phone":
        if me is None:
            raise ApiError(401, "UNAUTHENTICATED", "Sign in required.")
        if not body.new_phone or not body.current_password:
            raise ApiError(422, "VALIDATION_ERROR", "new_phone and current_password are required.")
        if not verify_password(body.current_password, me.password_hash):
            raise ApiError(401, "INVALID_CREDENTIALS", "Current password is incorrect.")
        new_phone = normalize_phone(body.new_phone)
        if db.scalar(select(User).where(User.phone == new_phone)):
            raise ApiError(409, "PHONE_IN_USE", "This phone number is already registered.")
        code = issue_otp(db, new_phone, "change_phone", me.id)
    else:
        if not body.phone:
            raise ApiError(422, "VALIDATION_ERROR", "phone is required.")
        phone = normalize_phone(body.phone)
        user = db.scalar(select(User).where(User.phone == phone))
        if body.purpose == "reset" and (user is None or not user.phone_verified):
            raise ApiError(404, "RESET_PHONE_NOT_FOUND", "No verified account is registered with that phone number.")
        if user is not None and (
            (body.purpose == "register" and not user.phone_verified) or (body.purpose == "reset" and user.phone_verified)
        ):
            code = issue_otp(db, phone, body.purpose, user.id)
    out = {"sent": True}
    if settings.debug_return_otp and code:
        out["dev_otp"] = code
    return out


class OtpVerify(BaseModel):
    purpose: Literal["register", "reset", "change_phone"]
    phone: str  # for change_phone this is the NEW phone number
    code: str = Field(min_length=6, max_length=6)
    new_password: Optional[str] = None


@router.post("/otp/verify")  # E-03
def otp_verify(body: OtpVerify, db=Depends(get_db)):
    phone = normalize_phone(body.phone)
    if body.purpose == "reset" and body.new_password is not None:
        validate_password(body.new_password)
    row = verify_otp(db, phone, body.purpose, body.code)

    if body.purpose == "register":
        user = db.get(User, row.user_id)
        if user is None:
            raise ApiError(400, "OTP_INVALID", "Code is invalid or has expired.")
        user.phone_verified = True
    elif body.purpose == "reset":
        user = db.get(User, row.user_id)
        if user is None or user.phone != phone:
            raise ApiError(400, "OTP_INVALID", "Code is invalid or has expired.")
        if body.new_password is not None:
            user.password_hash = hash_password(body.new_password)
            db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
            db.commit()
            identity = db.scalar(select(FirebaseIdentity).where(FirebaseIdentity.user_id == user.id))
            revoke_firebase_user(identity.firebase_uid if identity else user.id)
            return {"verified": True}
        else:
            reset_token = secrets.token_urlsafe(32)
            db.add(
                PasswordResetGrant(
                    user_id=user.id,
                    token_hash=hash_token(reset_token),
                    expires_at=utcnow() + timedelta(minutes=settings.otp_minutes),
                )
            )
            db.commit()
            return {"verified": True, "reset_token": reset_token}
    else:  # change_phone
        user = db.get(User, row.user_id)
        if user is None or db.scalar(select(User).where(User.phone == phone)):
            raise ApiError(409, "PHONE_IN_USE", "This phone number is already registered.")
        user.phone = phone
        user.phone_verified = True
        db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
        db.commit()
        identity = db.scalar(select(FirebaseIdentity).where(FirebaseIdentity.user_id == user.id))
        revoke_firebase_user(identity.firebase_uid if identity else user.id)
        return {"verified": True}
    db.commit()
    return {"verified": True}


class PasswordResetBody(BaseModel):
    reset_token: str = Field(min_length=32, max_length=128)
    new_password: str


@router.post("/password/reset")
def reset_password(body: PasswordResetBody, db=Depends(get_db)):
    validate_password(body.new_password)
    now = utcnow()
    token_hash = hash_token(body.reset_token)
    grant = db.scalar(select(PasswordResetGrant).where(PasswordResetGrant.token_hash == token_hash))
    if grant is None or grant.consumed or grant.expires_at <= now:
        raise ApiError(400, "RESET_TOKEN_INVALID", "Password reset verification is invalid or has expired.")
    user = db.get(User, grant.user_id)
    if user is None:
        raise ApiError(400, "RESET_TOKEN_INVALID", "Password reset verification is invalid or has expired.")
    consumed = db.execute(
        update(PasswordResetGrant)
        .where(
            PasswordResetGrant.id == grant.id,
            PasswordResetGrant.consumed == False,  # noqa: E712
            PasswordResetGrant.expires_at > now,
        )
        .values(consumed=True)
    )
    if consumed.rowcount != 1:
        raise ApiError(400, "RESET_TOKEN_INVALID", "Password reset verification is invalid or has expired.")
    user.password_hash = hash_password(body.new_password)
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
    identity = db.scalar(select(FirebaseIdentity).where(FirebaseIdentity.user_id == user.id))
    revoke_firebase_user(identity.firebase_uid if identity else user.id)
    return {"reset": True}


class LoginBody(BaseModel):
    phone: str
    password: str


@router.post("/login")  # E-04
def login(body: LoginBody, db=Depends(get_db)):
    phone = normalize_phone(body.phone)
    login_limiter.check(phone)
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "Phone number or password is incorrect.")
    if not user.phone_verified:
        raise ApiError(403, "PHONE_NOT_VERIFIED", "Verify your phone number first.")
    return {**issue_token_pair(db, user), "role": user.role, "verification_status": user.verification_status}


class RefreshBody(BaseModel):
    refresh_token: str


class LogoutBody(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/refresh")  # E-05 (rotation + reuse detection)
def refresh(body: RefreshBody, db=Depends(get_db)):
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(body.refresh_token)))
    if row is None or row.expires_at < utcnow():
        raise ApiError(401, "TOKEN_INVALID", "Invalid or expired session. Please sign in again.")
    if row.revoked:
        # an already-used token came back: assume theft, end every session of this user
        db.execute(update(RefreshToken).where(RefreshToken.user_id == row.user_id).values(revoked=True))
        db.commit()
        raise ApiError(401, "TOKEN_INVALID", "Invalid or expired session. Please sign in again.")
    burned = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == row.id,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > utcnow(),
        )
        .values(revoked=True)
    )
    if burned.rowcount != 1:
        raise ApiError(401, "TOKEN_INVALID", "Invalid or expired session. Please sign in again.")
    user = db.get(User, row.user_id)
    if user is None:
        raise ApiError(401, "TOKEN_INVALID", "Invalid or expired session. Please sign in again.")
    return issue_token_pair(db, user)


@router.post("/logout", status_code=204)  # E-06
def logout(
    body: LogoutBody | None = None,
    db=Depends(get_db),
):
    token = (
        db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(body.refresh_token)))
        if body and body.refresh_token
        else None
    )
    if token is None:
        return Response(status_code=204)
    rows = db.scalars(select(RefreshToken).where(RefreshToken.user_id == token.user_id))
    for row in rows:
        row.revoked = True
    db.commit()
    uid = db.scalar(select(FirebaseIdentity).where(FirebaseIdentity.user_id == token.user_id))
    if uid:
        revoke_firebase_user(uid.firebase_uid)
    return Response(status_code=204)

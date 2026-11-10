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
from ..firebase import (
    create_email_user,
    delete_auth_user,
    delete_document,
    revoke_firebase_user,
    set_email_verified,
    set_email_password,
    verify_id_token,
    upload_document,
)
from ..models import FirebaseIdentity, LawyerProfile, NgoProfile, OtpCode, PasswordResetGrant, RefreshToken, User
from ..ratelimit import RateLimiter
from ..security import hash_password, hash_token, verify_password
from ..services.accounts import purge_user
from ..services.otp import issue_otp, verify_otp
from ..services.tokens import issue_token_pair
from ..utils import new_id, normalize_email, normalize_phone, utcnow, validate_cnic, validate_password

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
    email: str = Form(...),
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
    email_n = normalize_email(email)
    validate_password(password)
    cnic_n = validate_cnic(cnic) if cnic else None
    if role == "lawyer" and not (bar_council_no and bar_council_no.strip()):
        raise ApiError(422, "BAR_COUNCIL_REQUIRED", "Bar Council number is required for lawyers.")
    if role == "ngo_monitor" and not (organisation_name and organisation_name.strip() and _split(districts)):
        raise ApiError(422, "NGO_DETAILS_REQUIRED", "Organisation name and at least one district are required.")
    if role in ("lawyer", "ngo_monitor") and (verification_document is None or not verification_document.filename):
        raise ApiError(422, "DOCUMENT_REQUIRED", "Upload your licence or proof document.")

    existing_phone = db.scalar(select(User).where(User.phone == phone_n))
    existing_email = db.scalar(select(User).where(User.email == email_n))
    if existing_email is not None and (
        existing_email.email_verified or existing_email.id != getattr(existing_phone, "id", None)
    ):
        raise ApiError(409, "EMAIL_IN_USE", "This email address is already registered.")
    if existing_phone is not None:
        if existing_phone.phone_verified or existing_phone.email_verified:
            raise ApiError(409, "PHONE_IN_USE", "This phone number is already registered.")
        purge_user(db, existing_phone)

    doc_key = _save_document(verification_document) if role != "citizen" and verification_document else None
    firebase_user_created = False
    try:
        user = User(
            role=role,
            full_name=full_name.strip(),
            phone=phone_n,
            email=email_n,
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
        create_email_user(user.id, email_n, password, user.full_name)
        firebase_user_created = True
        db.add(FirebaseIdentity(firebase_uid=user.id, user_id=user.id, provider="password"))
        db.commit()
    except Exception:
        db.rollback()
        if firebase_user_created:
            delete_auth_user(user.id)
        if doc_key:
            delete_document(doc_key)
        raise
    issue_otp(db, email_n, "register", user.id)
    return {
        "user_id": user.id,
        "role": user.role,
        "verification_status": user.verification_status,
        "email": email_n,
        "verification_required": True,
    }


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


class FirebaseEmailExchange(FirebaseExchange):
    password: Optional[str] = Field(None, min_length=8, max_length=72)


@router.post("/firebase/email/exchange")
def firebase_email_exchange(body: FirebaseEmailExchange, db=Depends(get_db)):
    claims = verify_id_token(body.id_token)
    if not claims.get("email_verified") or not claims.get("email"):
        raise ApiError(403, "EMAIL_NOT_VERIFIED", "Verify your email address with the code we sent before signing in.")
    email = normalize_email(str(claims["email"]))
    uid = str(claims.get("uid") or claims.get("sub") or "").strip()
    if not uid:
        raise ApiError(401, "FIREBASE_TOKEN_INVALID", "Firebase sign-in could not be verified.")
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "Create a LegalShield account first.")
    if not user.email_verified:
        raise ApiError(403, "EMAIL_NOT_VERIFIED", "Verify your email address with the code we sent before signing in.")
    identity = db.get(FirebaseIdentity, uid)
    if identity is not None and identity.user_id != user.id:
        raise ApiError(409, "FIREBASE_ACCOUNT_EXISTS", "This Firebase account is linked to another LegalShield account.")
    if uid != user.id and identity is None:
        db.add(
            FirebaseIdentity(
                firebase_uid=uid,
                user_id=user.id,
                provider=str(claims.get("firebase", {}).get("sign_in_provider", "password")),
            )
        )
    if body.password and not verify_password(body.password, user.password_hash):
        user.password_hash = hash_password(body.password)
        db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
    session = issue_token_pair(db, user, include_firebase_custom_token=False)
    return {**session, "role": user.role, "verification_status": user.verification_status}


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
    if user.email and not user.email_verified:
        raise ApiError(403, "EMAIL_NOT_VERIFIED", "Verify your email address first.")
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
    email: str = Form(...),
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
    email_n = normalize_email(email)
    validate_password(password)
    cnic_n, districts_n = _validate_firebase_registration(
        role, cnic, bar_council_no, organisation_name, districts, verification_document
    )
    if db.get(FirebaseIdentity, uid) is not None:
        raise ApiError(409, "FIREBASE_ACCOUNT_EXISTS", "This Firebase account is already linked to LegalShield.")
    if db.scalar(select(User).where(User.email == email_n)):
        raise ApiError(409, "EMAIL_IN_USE", "This email address is already registered.")
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
            email=email_n,
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
        create_email_user(user.id, email_n, password, user.full_name)
        db.add(FirebaseIdentity(firebase_uid=uid, user_id=user.id, provider="phone"))
        db.commit()
    except Exception:
        db.rollback()
        if doc_key:
            delete_document(doc_key)
        raise
    issue_otp(db, email_n, "register", user.id)
    return {
        "user_id": user.id,
        "role": user.role,
        "verification_status": user.verification_status,
        "email": email_n,
        "verification_required": True,
    }


class OtpRequest(BaseModel):
    purpose: Literal["register", "reset", "change_phone"]
    email: Optional[str] = None
    new_phone: Optional[str] = None
    current_password: Optional[str] = None


@router.post("/otp/request")  # E-02
def otp_request(body: OtpRequest, db=Depends(get_db), me: User | None = Depends(get_optional_user)):
    if body.purpose == "change_phone":
        if me is None:
            raise ApiError(401, "UNAUTHENTICATED", "Sign in required.")
        if not body.new_phone or not body.current_password:
            raise ApiError(422, "VALIDATION_ERROR", "new_phone and current_password are required.")
        if not me.email:
            raise ApiError(409, "EMAIL_REQUIRED", "Add an email address before changing your phone number.")
        if not verify_password(body.current_password, me.password_hash):
            raise ApiError(401, "INVALID_CREDENTIALS", "Current password is incorrect.")
        new_phone = normalize_phone(body.new_phone)
        if db.scalar(select(User).where(User.phone == new_phone)):
            raise ApiError(409, "PHONE_IN_USE", "This phone number is already registered.")
        email = normalize_email(me.email)
        issue_otp(db, email, "change_phone", me.id, phone=new_phone)
        return {"sent": True}

    if not body.email:
        raise ApiError(422, "VALIDATION_ERROR", "email is required.")
    email = normalize_email(body.email)
    user = db.scalar(select(User).where(User.email == email))
    if body.purpose == "register":
        if user is None:
            raise ApiError(404, "ACCOUNT_NOT_FOUND", "No account is registered with that email address.")
        if user.email_verified:
            raise ApiError(409, "EMAIL_ALREADY_VERIFIED", "This email address is already verified.")
        latest = db.scalar(
            select(OtpCode)
            .where(OtpCode.email == email, OtpCode.purpose == "register")
            .order_by(OtpCode.created_at.desc(), OtpCode.id.desc())
        )
        if latest is not None and latest.created_at > utcnow() - timedelta(seconds=60):
            raise ApiError(429, "OTP_COOLDOWN", "Please wait one minute before requesting another code.")
        issue_otp(db, email, body.purpose, user.id)
        return {"sent": True}
    if user is None:
        raise ApiError(404, "ACCOUNT_NOT_FOUND", "No account is registered with that email address.")
    if not user.email_verified:
        raise ApiError(403, "EMAIL_NOT_VERIFIED", "Verify your email address before resetting its password.")
    if body.purpose == "reset":
        db.execute(
            update(PasswordResetGrant)
            .where(PasswordResetGrant.user_id == user.id, PasswordResetGrant.consumed == False)  # noqa: E712
            .values(consumed=True)
        )
    issue_otp(db, email, body.purpose, user.id)
    return {"sent": True}


class OtpVerify(BaseModel):
    purpose: Literal["register", "reset", "change_phone"]
    email: Optional[str] = None
    phone: Optional[str] = None  # for change_phone this is the NEW phone number
    code: str = Field(pattern=r"^\d{6}$")


@router.post("/otp/verify")  # E-03
def otp_verify(body: OtpVerify, db=Depends(get_db)):
    if not body.email:
        raise ApiError(422, "VALIDATION_ERROR", "email is required.")
    email = normalize_email(body.email)
    row = verify_otp(db, email, body.purpose, body.code)

    user = db.get(User, row.user_id)
    if user is None or user.email != email:
        raise ApiError(400, "OTP_INVALID", "Code is invalid or has expired.")
    if body.purpose == "register":
        if row.user_id != user.id or user.email_verified:
            raise ApiError(400, "OTP_INVALID", "Code is invalid or has expired.")
        set_email_verified(user.id)
        user.email_verified = True
        db.commit()
        return {"verified": True}
    if body.purpose == "reset":
        if not user.email_verified or row.user_id != user.id:
            raise ApiError(400, "OTP_INVALID", "Code is invalid or has expired.")
        reset_token = secrets.token_urlsafe(32)
        db.add(
            PasswordResetGrant(
                user_id=user.id,
                token_hash=hash_token(reset_token),
                expires_at=utcnow() + timedelta(minutes=10),
            )
        )
        db.commit()
        return {"verified": True, "reset_token": reset_token}

    if not body.phone:
        raise ApiError(422, "VALIDATION_ERROR", "phone is required.")
    phone = normalize_phone(body.phone)
    if row.phone != phone:
        raise ApiError(400, "OTP_INVALID", "Code is invalid or has expired.")
    if db.scalar(select(User).where(User.phone == phone)):
        raise ApiError(409, "PHONE_IN_USE", "This phone number is already registered.")
    user.phone = phone
    user.phone_verified = True
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
    identity = db.scalar(select(FirebaseIdentity).where(FirebaseIdentity.user_id == user.id))
    revoke_firebase_user(identity.firebase_uid if identity else user.id)
    return {"verified": True}


class PasswordResetBody(BaseModel):
    reset_token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)


@router.post("/password/reset")
def reset_password(body: PasswordResetBody, db=Depends(get_db)):
    validate_password(body.new_password)
    now = utcnow()
    grant = db.scalar(select(PasswordResetGrant).where(PasswordResetGrant.token_hash == hash_token(body.reset_token)))
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
    db.commit()
    identity = db.scalar(select(FirebaseIdentity).where(FirebaseIdentity.user_id == user.id))
    firebase_uid = identity.firebase_uid if identity else user.id
    set_email_password(firebase_uid, body.new_password)
    user.password_hash = hash_password(body.new_password)
    db.execute(update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True))
    db.commit()
    revoke_firebase_user(firebase_uid)
    return {"reset": True}


class LoginBody(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    password: str


@router.post("/login")  # E-04
def login(body: LoginBody, db=Depends(get_db)):
    if body.email:
        if "@" in body.email:
            email = normalize_email(body.email)
            login_limiter.check(email)
            user = db.scalar(select(User).where(User.email == email))
            verified = user.email_verified if user else False
            email_login = True
        else:
            phone = normalize_phone(body.email)
            login_limiter.check(phone)
            user = db.scalar(select(User).where(User.phone == phone))
            verified = user.phone_verified if user else False
            email_login = False
    elif body.phone:
        phone = normalize_phone(body.phone)
        login_limiter.check(phone)
        user = db.scalar(select(User).where(User.phone == phone))
        verified = user.phone_verified if user else False
        email_login = False
    else:
        raise ApiError(422, "VALIDATION_ERROR", "email is required.")
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(
            401,
            "INVALID_CREDENTIALS",
            "Email address or password is incorrect." if email_login else "Phone number or password is incorrect.",
        )
    if not verified:
        raise ApiError(
            403,
            "EMAIL_NOT_VERIFIED" if email_login else "PHONE_NOT_VERIFIED",
            "Verify your email address first." if email_login else "Verify your phone number first.",
        )
    if user.email:
        raise ApiError(400, "FIREBASE_AUTH_REQUIRED", "Sign in with Firebase using your email address and password.")
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

"""Module 1: profile, emergency contacts, devices, account deletion (E-07 .. E-12, E-49)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from ..firebase import firestore_client
from ..db import get_db, select
from ..deps import get_current_user, require_roles
from ..errors import ApiError
from ..models import Device, EmergencyContact, LawyerProfile, NgoProfile, User
from ..security import verify_password
from ..services.accounts import purge_user
from ..utils import iso, mask_cnic, normalize_phone, validate_cnic

router = APIRouter(prefix="/users", tags=["M1 Users"])


def _profile(db, user: User) -> dict:
    out = {
        "id": user.id,
        "role": user.role,
        "full_name": user.full_name,
        "phone": user.phone,
        "cnic_masked": mask_cnic(user.cnic),
        "phone_verified": user.phone_verified,
        "verification_status": user.verification_status,
        "verification_note": user.verification_note,
        "created_at": iso(user.created_at),
    }
    if user.role == "lawyer":
        p = db.get(LawyerProfile, user.id)
        if p:
            out["lawyer"] = {"bar_council_no": p.bar_council_no, "cities": p.cities, "specializations": p.specializations,
                             "pro_bono": p.pro_bono, "sos_opt_in": p.sos_opt_in}
    if user.role == "ngo_monitor":
        p = db.get(NgoProfile, user.id)
        if p:
            out["ngo"] = {"organisation_name": p.organisation_name, "districts": p.districts}
    return out


@router.get("/me")  # E-07
def me(user: User = Depends(get_current_user), db=Depends(get_db)):
    return _profile(db, user)


class ProfilePatch(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    cnic: Optional[str] = None


@router.patch("/me")  # E-08
def update_me(body: ProfilePatch, user: User = Depends(get_current_user), db=Depends(get_db)):
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.cnic is not None:
        user.cnic = validate_cnic(body.cnic)
    db.commit()
    return _profile(db, user)


class PreferencesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lang: Literal["en", "rn", "ur"]
    theme: Literal["light", "dark"]
    discreet: bool


@router.get("/me/preferences")
def get_preferences(user: User = Depends(get_current_user)):
    snapshot = firestore_client().collection("user_preferences").document(user.id).get()
    return snapshot.to_dict() or {}


@router.put("/me/preferences")
def save_preferences(body: PreferencesBody, user: User = Depends(get_current_user)):
    firestore_client().collection("user_preferences").document(user.id).set(body.model_dump(), merge=True)
    return body.model_dump()


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str


def _contact(c: EmergencyContact) -> dict:
    return {"id": c.id, "name": c.name, "phone": c.phone}


@router.get("/me/contacts")  # E-09
def list_contacts(user: User = Depends(require_roles("citizen")), db=Depends(get_db)):
    rows = db.scalars(select(EmergencyContact).where(EmergencyContact.user_id == user.id))
    return {"contacts": [_contact(c) for c in rows]}


@router.post("/me/contacts", status_code=201)  # E-10
def add_contact(body: ContactIn, user: User = Depends(require_roles("citizen")), db=Depends(get_db)):
    c = EmergencyContact(user_id=user.id, name=body.name.strip(), phone=normalize_phone(body.phone))
    db.add(c)
    db.commit()
    return _contact(c)


@router.delete("/me/contacts/{contact_id}", status_code=204)  # E-11
def delete_contact(contact_id: str, user: User = Depends(require_roles("citizen")), db=Depends(get_db)):
    c = db.get(EmergencyContact, contact_id)
    if c is None or c.user_id != user.id:
        raise ApiError(404, "NOT_FOUND", "Contact not found.")
    db.delete(c)
    db.commit()
    return Response(status_code=204)


class DeviceIn(BaseModel):
    fcm_token: str = Field(min_length=10, max_length=300)


@router.post("/me/devices")  # E-12
def register_device(body: DeviceIn, user: User = Depends(get_current_user), db=Depends(get_db)):
    exists = db.scalar(select(Device).where(Device.user_id == user.id, Device.fcm_token == body.fcm_token))
    if exists is None:
        db.add(Device(user_id=user.id, fcm_token=body.fcm_token))
        db.commit()
    return {"registered": True}


class DeleteBody(BaseModel):
    password: str


@router.delete("/me", status_code=204)  # E-49
def delete_me(body: DeleteBody, user: User = Depends(get_current_user), db=Depends(get_db)):
    if user.role == "admin":
        raise ApiError(403, "ADMIN_DELETE_FORBIDDEN", "Admin accounts cannot be deleted from the app.")
    if not verify_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "Password is incorrect.")
    purge_user(db, user)
    return Response(status_code=204)

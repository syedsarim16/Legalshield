"""Firestore record definitions."""
from datetime import datetime

from .crypto import decrypt_value, encrypt_value
from .db import Field
from .utils import new_id, normalize_utc, utcnow


class Record:
    __collection__ = ""
    __key__ = "id"
    __fields__: tuple[str, ...] = ()
    __defaults__: dict = {}

    def __init__(self, **values):
        unknown = set(values) - set(self.__fields__)
        if unknown:
            raise TypeError(f"Unknown {type(self).__name__} fields: {', '.join(sorted(unknown))}")
        for name in self.__fields__:
            value = values.get(name, self.__defaults__.get(name))
            if callable(value):
                value = value()
            setattr(self, name, value)

    def to_dict(self) -> dict:
        return {name: getattr(self, name) for name in self.__fields__}

    @classmethod
    def from_dict(cls, values: dict):
        values = {name: values[name] for name in cls.__fields__ if name in values}
        return cls(**{
            name: normalize_utc(value) if isinstance(value, datetime) else value
            for name, value in values.items()
        })

    @classmethod
    def _fields(cls):
        for name in cls.__fields__:
            setattr(cls, name, Field(name))


class User(Record):
    __collection__ = "users"
    __fields__ = ("id", "role", "full_name", "phone", "cnic", "password_hash", "phone_verified",
                  "verification_status", "verification_note", "verification_document_key", "created_at")
    __defaults__ = {"id": new_id, "cnic": None, "phone_verified": False, "verification_status": "not_required",
                    "verification_note": None, "verification_document_key": None, "created_at": utcnow}

    def to_dict(self):
        values = super().to_dict()
        values["cnic"] = encrypt_value(self.cnic) if self.cnic is not None else None
        return values

    @classmethod
    def from_dict(cls, values):
        values = dict(values)
        if values.get("cnic") is not None:
            values["cnic"] = decrypt_value(values["cnic"])
        return super().from_dict(values)


class FirebaseIdentity(Record):
    __collection__ = "firebase_identities"
    __key__ = "firebase_uid"
    __fields__ = ("firebase_uid", "user_id", "provider", "created_at")
    __defaults__ = {"provider": "phone", "created_at": utcnow}


class LawyerProfile(Record):
    __collection__ = "lawyer_profiles"
    __key__ = "user_id"
    __fields__ = ("user_id", "bar_council_no", "cities", "specializations", "pro_bono", "sos_opt_in", "bio", "contact_phone")
    __defaults__ = {"cities": list, "specializations": list, "pro_bono": False, "sos_opt_in": False, "bio": "", "contact_phone": None}


class NgoProfile(Record):
    __collection__ = "ngo_profiles"
    __key__ = "user_id"
    __fields__ = ("user_id", "organisation_name", "districts")
    __defaults__ = {"districts": list}


class OtpCode(Record):
    __collection__ = "otp_codes"
    __fields__ = ("id", "phone", "purpose", "user_id", "code_hash", "attempts", "consumed", "created_at", "expires_at")
    __defaults__ = {"id": new_id, "user_id": None, "attempts": 0, "consumed": False, "created_at": utcnow}


class PasswordResetGrant(Record):
    __collection__ = "password_reset_grants"
    __fields__ = ("id", "user_id", "token_hash", "consumed", "created_at", "expires_at")
    __defaults__ = {"id": new_id, "consumed": False, "created_at": utcnow}


class RefreshToken(Record):
    __collection__ = "refresh_tokens"
    __fields__ = ("id", "user_id", "token_hash", "revoked", "created_at", "expires_at")
    __defaults__ = {"id": new_id, "revoked": False, "created_at": utcnow}


class Device(Record):
    __collection__ = "devices"
    __fields__ = ("id", "user_id", "fcm_token", "created_at")
    __defaults__ = {"id": new_id, "created_at": utcnow}


class EmergencyContact(Record):
    __collection__ = "emergency_contacts"
    __fields__ = ("id", "user_id", "name", "phone")
    __defaults__ = {"id": new_id}


class StatuteSection(Record):
    __collection__ = "statute_sections"
    __fields__ = ("id", "law", "section_number", "title", "chapter", "text_en", "kind", "bailable", "cognizable",
                  "compoundable", "punishment", "triable_by", "source_ref", "version", "reviewed_by_advisor")
    __defaults__ = {"id": new_id, "chapter": None, "bailable": None, "cognizable": None, "compoundable": None,
                    "punishment": None, "triable_by": None, "source_ref": "", "version": "", "reviewed_by_advisor": False}


for _model in (User, FirebaseIdentity, LawyerProfile, NgoProfile, OtpCode, PasswordResetGrant, RefreshToken, Device,
               EmergencyContact, StatuteSection):
    _model._fields()

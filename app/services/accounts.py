from ..db import delete, select
from ..firebase import delete_auth_user, delete_document, delete_user_preferences
from ..models import Device, EmergencyContact, FirebaseIdentity, LawyerProfile, NgoProfile, OtpCode, PasswordResetGrant, RefreshToken, User


def purge_user(db, user: User) -> None:
    """Remove a user and everything we hold about them (E-49, and re-registration of unverified phones).
    Later modules (SOS, evidence vault, incidents) must hook their deletes in here."""
    uid = user.id
    for model in (EmergencyContact, Device, PasswordResetGrant, RefreshToken):
        db.execute(delete(model).where(model.user_id == uid))
    db.execute(delete(OtpCode).where((OtpCode.user_id == uid) | (OtpCode.phone == user.phone)))
    db.execute(delete(LawyerProfile).where(LawyerProfile.user_id == uid))
    db.execute(delete(NgoProfile).where(NgoProfile.user_id == uid))
    identity = db.scalar(select(FirebaseIdentity).where(FirebaseIdentity.user_id == uid))
    db.execute(delete(FirebaseIdentity).where(FirebaseIdentity.user_id == uid))
    if user.verification_document_key:
        delete_document(user.verification_document_key)
    db.delete(user)
    db.commit()
    delete_user_preferences(uid)
    if identity:
        delete_auth_user(identity.firebase_uid)
    if not identity or identity.firebase_uid != uid:
        delete_auth_user(uid)

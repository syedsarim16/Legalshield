"""Encryption helpers for sensitive Firestore fields."""
import base64
import hashlib

from cryptography.fernet import Fernet

from .config import settings


def _fernet() -> Fernet:
    seed = settings.data_encryption_key or settings.jwt_secret
    key = base64.urlsafe_b64encode(hashlib.sha256(seed.encode()).digest())
    return Fernet(key)


def encrypt_value(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()

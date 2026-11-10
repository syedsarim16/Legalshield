import pytest

from app import firebase
from app.errors import ApiError


class FakeFirebaseAuth:
    class UserNotFoundError(Exception):
        pass

    class UidAlreadyExistsError(Exception):
        pass

    def __init__(self, existing=False):
        self.existing = existing
        self.created = []

    def get_user(self, uid):
        if not self.existing:
            raise self.UserNotFoundError(uid)

    def create_user(self, *, uid):
        self.created.append(uid)
        self.existing = True

    def create_custom_token(self, uid):
        assert self.existing
        return b"custom-token"


def test_custom_token_login_provisions_missing_firebase_auth_user(monkeypatch):
    auth = FakeFirebaseAuth()
    monkeypatch.setattr(firebase, "admin_ready", lambda: True)
    monkeypatch.setattr(firebase, "firebase_auth", auth)

    assert firebase.create_custom_token("user-123") == "custom-token"
    assert auth.created == ["user-123"]


def test_custom_token_login_reuses_existing_firebase_auth_user(monkeypatch):
    auth = FakeFirebaseAuth(existing=True)
    monkeypatch.setattr(firebase, "admin_ready", lambda: True)
    monkeypatch.setattr(firebase, "firebase_auth", auth)

    assert firebase.create_custom_token("user-123") == "custom-token"
    assert auth.created == []


def test_invalid_id_token_logs_sdk_reason_without_logging_token(monkeypatch, caplog):
    monkeypatch.setattr(firebase, "admin_ready", lambda: True)
    invalid_token_error = firebase.firebase_auth.InvalidIdTokenError
    verify_options = {}

    def reject_token(*args, **kwargs):
        verify_options.update(kwargs)
        raise invalid_token_error("Firebase ID token has an incorrect audience claim.")

    monkeypatch.setattr(firebase.firebase_auth, "verify_id_token", reject_token)

    with pytest.raises(ApiError) as error:
        firebase.verify_id_token("sensitive-token-value")

    assert error.value.code == "FIREBASE_TOKEN_INVALID"
    assert "incorrect audience claim" in caplog.text
    assert "sensitive-token-value" not in caplog.text
    assert verify_options == {
        "check_revoked": True,
        "clock_skew_seconds": firebase.ID_TOKEN_CLOCK_SKEW_SECONDS,
    }

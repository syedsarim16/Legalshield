import pytest

from app import firebase
from app.errors import ApiError


class FakeFirebaseAuth:
    class UserNotFoundError(Exception):
        pass

    class UidAlreadyExistsError(Exception):
        pass

    class EmailAlreadyExistsError(Exception):
        pass

    def __init__(self, existing=False):
        self.existing = existing
        self.created = []
        self.updated = []

    def get_user(self, uid):
        if not self.existing:
            raise self.UserNotFoundError(uid)

    def create_user(self, *, uid):
        self.created.append(uid)
        self.existing = True

    def create_custom_token(self, uid):
        assert self.existing
        return b"custom-token"

    def update_user(self, uid, **kwargs):
        self.updated.append((uid, kwargs))


class FakeEmailFirebaseAuth(FakeFirebaseAuth):
    def __init__(self):
        super().__init__()
        self.users = {}
        self.created_email_users = []

    def get_user(self, uid):
        if uid not in self.users:
            raise self.UserNotFoundError(uid)
        return self.users[uid]

    def create_user(self, **kwargs):
        self.created_email_users.append(kwargs)
        self.users[kwargs["uid"]] = type("FirebaseUser", (), {"email": kwargs["email"]})()

    def update_user(self, uid, **kwargs):
        self.updated.append((uid, kwargs))


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


def test_create_email_user_sets_password_and_starts_unverified(monkeypatch):
    auth = FakeEmailFirebaseAuth()
    monkeypatch.setattr(firebase, "admin_ready", lambda: True)
    monkeypatch.setattr(firebase, "firebase_auth", auth)

    firebase.create_email_user("user-123", "person@example.test", "Passw0rd!", "Person")

    assert auth.created_email_users == [{
        "uid": "user-123",
        "email": "person@example.test",
        "password": "Passw0rd!",
        "email_verified": False,
        "display_name": "Person",
    }]


def test_firebase_email_otp_completion_and_password_reset_updates_auth(monkeypatch):
    auth = FakeFirebaseAuth(existing=True)
    monkeypatch.setattr(firebase, "admin_ready", lambda: True)
    monkeypatch.setattr(firebase, "firebase_auth", auth)

    firebase.set_email_verified("user-123")
    firebase.set_email_password("user-123", "NewPassw0rd!")

    assert auth.updated == [
        ("user-123", {"email_verified": True}),
        ("user-123", {"password": "NewPassw0rd!"}),
    ]


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

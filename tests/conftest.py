import copy
import os

os.environ.update(
    JWT_SECRET="test-secret",
    OTP_MINUTES="1",
    ALLOW_UNREVIEWED_STATUTES="true",
    OTP_RATE_LIMIT="1000",
    LLM_PROVIDER="mock",
)

import pytest
from fastapi.testclient import TestClient

import app.db as app_db
import app.deps as app_deps
import app.firebase as firebase_module
import app.main as app_main
import app.routers.auth as auth_module
import app.services.accounts as accounts_module
import app.services.otp as otp_module
import app.services.tokens as tokens_module
from app.main import app as fastapi_app
from app.models import User
from app.routers import auth, chat
from app.routers import users as users_module
from app.security import hash_password

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
API = "/api/v1"


class Snapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = copy.deepcopy(data)
        self.exists = data is not None

    def to_dict(self):
        return copy.deepcopy(self._data)


class Document:
    def __init__(self, client, collection, doc_id):
        self.client, self.collection, self.id = client, collection, str(doc_id)

    def get(self, transaction=None):
        data = self.client.data.get(self.collection, {}).get(self.id)
        return Snapshot(self.id, data)

    def set(self, values, merge=False):
        docs = self.client.data.setdefault(self.collection, {})
        current = docs.get(self.id, {}) if merge else {}
        docs[self.id] = {**current, **copy.deepcopy(values)}

    def create(self, values):
        docs = self.client.data.setdefault(self.collection, {})
        if self.id in docs:
            from google.api_core.exceptions import AlreadyExists
            raise AlreadyExists("Document already exists")
        docs[self.id] = copy.deepcopy(values)

    def delete(self):
        self.client.data.setdefault(self.collection, {}).pop(self.id, None)


class Query:
    def __init__(self, client, collection, filters=()):
        self.client, self.collection, self.filters = client, collection, filters

    def where(self, field, operator, value):
        return Query(self.client, self.collection, self.filters + ((field, operator, value),))

    def document(self, doc_id):
        return Document(self.client, self.collection, doc_id)

    def stream(self):
        for doc_id, values in self.client.data.get(self.collection, {}).items():
            if all(_matches(values.get(field), operator, value) for field, operator, value in self.filters):
                yield Snapshot(doc_id, values)


class Batch:
    def __init__(self):
        self.operations = []

    def set(self, ref, values):
        self.operations.append(("set", ref, values))

    def delete(self, ref):
        self.operations.append(("delete", ref, None))

    def commit(self):
        for operation, ref, values in self.operations:
            if operation == "set":
                ref.set(values)
            else:
                ref.delete()


class Transaction:
    def __init__(self):
        self.operations = []

    def get(self, ref):
        return ref.get()

    def update(self, ref, values):
        self.operations.append((ref, values))

    def commit(self):
        for ref, values in self.operations:
            ref.set(values, merge=True)


class Firestore:
    def __init__(self):
        self.data = {}

    def collection(self, name):
        return Query(self, name)

    def batch(self):
        return Batch()

    def transaction(self):
        return Transaction()


def _matches(actual, operator, expected):
    if operator == "==":
        return actual == expected
    if operator == "!=":
        return actual != expected
    if actual is None:
        return False
    return {
        ">=": lambda: actual >= expected,
        ">": lambda: actual > expected,
        "<=": lambda: actual <= expected,
        "<": lambda: actual < expected,
    }[operator]()


def _run_transaction(function, transaction):
    result = function(transaction)
    transaction.commit()
    return result


test_firestore = Firestore()


class TestEmailSender:
    def __init__(self):
        self.messages = []

    def send(self, recipient, subject, body):
        self.messages.append((recipient, subject, body))


test_email_sender = TestEmailSender()


def latest_email_code(email):
    import re

    messages = [message for message in test_email_sender.messages if message[0] == email]
    assert messages, f"No email was sent to {email}"
    codes = re.findall(r"\b\d{6}\b", messages[-1][2])
    assert codes, f"No verification code was included in the email to {email}"
    return codes[-1]


def email_for_phone(phone):
    import re

    digits = re.sub(r"\D", "", phone)
    return f"user-{digits}@example.test"


@pytest.fixture()
def client(monkeypatch):
    test_firestore.data.clear()
    test_email_sender.messages.clear()
    monkeypatch.setattr(app_db, "firestore_client", lambda: test_firestore)
    monkeypatch.setattr(
        app_db,
        "transactional",
        lambda function: lambda transaction: _run_transaction(function, transaction),
    )
    monkeypatch.setattr(app_main, "firestore_client", lambda: test_firestore)
    monkeypatch.setattr(users_module, "firestore_client", lambda: test_firestore)
    monkeypatch.setattr(firebase_module, "admin_ready", lambda: True)
    monkeypatch.setattr(app_main, "admin_ready", lambda: True)

    def verify_token(value):
        if value.startswith("test-email:"):
            _, uid, email, verified = value.split(":", 3)
            return {
                "uid": uid,
                "email": email,
                "email_verified": verified == "true",
                "firebase": {"sign_in_provider": "password"},
            }
        if value.startswith("test-uid:"):
            return {"uid": value.removeprefix("test-uid:"), "email_verified": True}
        if value.startswith("test-phone:"):
            _, uid, phone = value.split(":", 2)
            return {"uid": uid, "phone_number": phone}
        from app.errors import ApiError
        raise ApiError(401, "FIREBASE_TOKEN_INVALID", "Firebase sign-in could not be verified.")

    monkeypatch.setattr(app_deps, "verify_id_token", verify_token)
    monkeypatch.setattr(auth_module, "verify_id_token", verify_token)
    monkeypatch.setattr(tokens_module, "create_custom_token", lambda uid: f"test-uid:{uid}")
    monkeypatch.setattr(auth_module, "create_email_user", lambda *args: None)
    monkeypatch.setattr(auth_module, "set_email_verified", lambda *args: None)
    monkeypatch.setattr(auth_module, "set_email_password", lambda *args: None)
    monkeypatch.setattr(auth_module, "delete_auth_user", lambda *args: None)
    monkeypatch.setattr(auth_module, "upload_document", lambda *args: True)
    monkeypatch.setattr(auth_module, "delete_document", lambda *args: None)
    monkeypatch.setattr(accounts_module, "delete_document", lambda *args: None)
    monkeypatch.setattr(accounts_module, "delete_user_preferences", lambda *args: None)
    monkeypatch.setattr(otp_module, "get_email_sender", lambda: test_email_sender)
    monkeypatch.setattr(auth_module, "revoke_firebase_user", lambda *args: None)
    monkeypatch.setattr(accounts_module, "delete_auth_user", lambda *args: None)
    auth.login_limiter.reset()
    chat.chat_limiter.reset()
    with TestClient(fastapi_app) as test_client:
        yield test_client


def register_and_login(client, role="citizen", phone="03001234567", password="Passw0rd!", **extra):
    email = extra.get("email") or email_for_phone(phone)
    data = {"role": role, "full_name": "Test User", "phone": phone, "email": email, "password": password, **extra}
    files = None
    if role in ("lawyer", "ngo_monitor"):
        files = {"verification_document": ("licence.png", PNG, "image/png")}
    r = client.post(f"{API}/auth/register", data=data, files=files)
    assert r.status_code == 201, r.text
    verified = client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "register", "email": email, "code": latest_email_code(email)},
    )
    assert verified.status_code == 200, verified.text
    v = client.post(
        f"{API}/auth/firebase/email/exchange",
        json={"id_token": f"test-email:{r.json()['user_id']}:{email}:true"},
    )
    assert v.status_code == 200, v.text
    tokens = v.json()
    return tokens, {"Authorization": f"Bearer test-uid:{r.json()['user_id']}"}


@pytest.fixture()
def citizen(client):
    return register_and_login(client)


def make_admin(phone="03009998888", password="AdminPassw0rd!"):
    from app.db import FirestoreSession
    db = FirestoreSession(test_firestore)
    db.add(User(role="admin", full_name="Admin", phone="+92" + phone[1:], password_hash=hash_password(password), phone_verified=True))
    db.commit()
    db.close()
    return phone, password

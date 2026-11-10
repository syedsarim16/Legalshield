from app.config import settings
from app.errors import ApiError
import app.routers.auth as auth_module

from .conftest import API, PNG, email_for_phone, latest_email_code, make_admin, register_and_login


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_citizen_register_verify_login_me(client):
    tokens, h = register_and_login(client, cnic="12345-1234567-1")
    me = client.get(f"{API}/users/me", headers=h).json()
    assert me["role"] == "citizen" and me["phone"] == "+923001234567"
    assert me["email"] == email_for_phone("03001234567") and me["email_verified"] is True
    assert me["cnic_masked"] == "*****-*******-1"
    assert me["verification_status"] == "not_required"
    assert "12345-1234567" not in str(me)
    from .conftest import test_firestore
    raw = next(iter(test_firestore.data["users"].values()))["cnic"]
    assert raw and "12345-1234567-1" not in raw


def test_login_blocked_until_email_verified(client):
    email = email_for_phone("03111111111")
    client.post(f"{API}/auth/register", data={"role": "citizen", "full_name": "A B", "phone": "03111111111", "email": email, "password": "Passw0rd!"})
    r = client.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd!"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"


def test_wrong_password_and_error_shape(client, citizen):
    r = client.post(f"{API}/auth/login", json={"email": email_for_phone("03001234567"), "password": "nope-nope"})
    assert r.status_code == 401 and r.json() == {"error": {"code": "INVALID_CREDENTIALS", "message": "Email address or password is incorrect."}}


def test_admin_cannot_self_register(client):
    r = client.post(f"{API}/auth/register", data={"role": "admin", "full_name": "Evil", "phone": "03001112222", "email": "evil@example.test", "password": "Passw0rd!"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "ADMIN_REGISTRATION_FORBIDDEN"


def test_validation_errors(client):
    base = {"role": "citizen", "full_name": "A B", "phone": "03001112222", "email": "a@example.test", "password": "Passw0rd!"}
    assert client.post(f"{API}/auth/register", data={**base, "email": "not-an-email"}).json()["error"]["code"] == "INVALID_EMAIL"
    assert client.post(f"{API}/auth/register", data={**base, "cnic": "123"}).json()["error"]["code"] == "INVALID_CNIC"
    assert client.post(f"{API}/auth/register", data={**base, "phone": "12345"}).json()["error"]["code"] == "INVALID_PHONE"
    assert client.post(f"{API}/auth/register", data={**base, "password": "short"}).json()["error"]["code"] == "WEAK_PASSWORD"
    assert client.post(f"{API}/auth/register", data={**base, "role": "wizard"}).json()["error"]["code"] == "INVALID_ROLE"
    r = client.post(f"{API}/auth/register", data={"role": "citizen"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_verified_phone(client, citizen):
    r = client.post(f"{API}/auth/register", data={"role": "citizen", "full_name": "X Y", "phone": "0300-1234567", "email": "other@example.test", "password": "Passw0rd!"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "PHONE_IN_USE"


def test_firebase_verification_required_and_exchange(client):
    email = "verified@example.test"
    response = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "A B", "phone": "03101010101", "email": email, "password": "Passw0rd!"},
    )
    assert response.status_code == 201
    assert "firebase_custom_token" not in response.json()
    assert "dev_otp" not in response.json()
    unverified = client.post(
        f"{API}/auth/firebase/email/exchange",
        json={"id_token": f"test-email:{response.json()['user_id']}:{email}:false"},
    )
    assert unverified.status_code == 403
    otp = client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "register", "email": email, "code": latest_email_code(email)},
    )
    assert otp.status_code == 200
    verified = client.post(
        f"{API}/auth/firebase/email/exchange",
        json={"id_token": f"test-email:{response.json()['user_id']}:{email}:true"},
    )
    assert verified.status_code == 200
    assert "firebase_custom_token" not in verified.json()


def test_registration_uses_email_otp_without_verification_links(client):
    from .conftest import test_email_sender, test_firestore

    email = "verify-otp@example.test"
    registration = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "A B", "phone": "03101010102", "email": email, "password": "Passw0rd!"},
    )
    assert registration.status_code == 201
    assert test_email_sender.messages[-1][0] == email
    assert "http" not in test_email_sender.messages[-1][2].lower()
    assert test_firestore.data["users"][registration.json()["user_id"]]["email_verified"] is False
    unverified = client.post(
        f"{API}/auth/firebase/email/exchange",
        json={"id_token": f"test-email:{registration.json()['user_id']}:{email}:false"},
    )
    assert unverified.status_code == 403
    verified = client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "register", "email": email, "code": latest_email_code(email)},
    )
    assert verified.status_code == 200 and verified.json() == {"verified": True}
    assert test_firestore.data["users"][registration.json()["user_id"]]["email_verified"] is True
    assert client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "register", "email": email, "code": latest_email_code(email)},
    ).status_code == 400
    verified = client.post(
        f"{API}/auth/firebase/email/exchange",
        json={"id_token": f"test-email:{registration.json()['user_id']}:{email}:true"},
    )
    assert verified.status_code == 200


def test_firebase_registration_sends_one_email_otp(client):
    from .conftest import test_email_sender

    email = "phone-registration@example.test"
    response = client.post(
        f"{API}/auth/firebase/register",
        data={
            "id_token": "test-phone:firebase-user-1:+923101010105",
            "role": "citizen",
            "full_name": "A B",
            "email": email,
            "password": "Passw0rd!",
        },
    )
    assert response.status_code == 201
    assert len(test_email_sender.messages) == 1
    assert test_email_sender.messages[0][0] == email
    assert client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "register", "email": email, "code": latest_email_code(email)},
    ).status_code == 200


def test_registration_otp_resend_has_server_side_cooldown(client):
    email = "cooldown@example.test"
    registration = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "A B", "phone": "03101010103", "email": email, "password": "Passw0rd!"},
    )
    assert registration.status_code == 201
    response = client.post(f"{API}/auth/otp/request", json={"purpose": "register", "email": email})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "OTP_COOLDOWN"


def test_registration_otp_is_hashed_and_expires(client, monkeypatch):
    from .conftest import test_firestore

    monkeypatch.setattr(settings, "otp_minutes", 0)
    email = "expired@example.test"
    registration = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "A B", "phone": "03101010104", "email": email, "password": "Passw0rd!"},
    )
    assert registration.status_code == 201
    code = latest_email_code(email)
    otp = next(iter(test_firestore.data["otp_codes"].values()))
    assert otp["code_hash"] != code
    response = client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "register", "email": email, "code": code},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "OTP_EXPIRED"


def test_password_reset_email_otp_changes_password_and_revokes_sessions(client, monkeypatch):
    tokens, headers = register_and_login(client, phone="03101010102")
    email = email_for_phone("03101010102")
    from .conftest import test_firestore
    user_id = next(iter(test_firestore.data["users"]))
    changed = []
    monkeypatch.setattr(auth_module, "set_email_password", lambda uid, password: changed.append((uid, password)))
    request = client.post(f"{API}/auth/otp/request", json={"purpose": "reset", "email": email})
    assert request.status_code == 200 and request.json() == {"sent": True}
    verified = client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "reset", "email": email, "code": latest_email_code(email)},
    )
    assert verified.status_code == 200
    assert "code" not in verified.json() and verified.json()["reset_token"]
    reset = client.post(
        f"{API}/auth/password/reset",
        json={"reset_token": verified.json()["reset_token"], "new_password": "NewPassw0rd!"},
    )
    assert reset.status_code == 200 and reset.json() == {"reset": True}
    assert changed == [(user_id, "NewPassw0rd!")]
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post(
        f"{API}/auth/otp/request",
        headers=headers,
        json={"purpose": "change_phone", "new_phone": "03101010103", "current_password": "NewPassw0rd!"},
    ).status_code == 200


def test_duplicate_verified_email_is_rejected(client):
    email = "duplicate@example.test"
    register_and_login(client, email=email)
    response = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "Another User", "phone": "03102020202", "email": email.upper(), "password": "Passw0rd!"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_IN_USE"


def test_firebase_email_exchange_rejects_identity_linked_to_another_account(client):
    first_email = "first@example.test"
    first = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "First User", "phone": "03102020221", "email": first_email, "password": "Passw0rd!"},
    ).json()
    second = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "Second User", "phone": "03102020222", "email": "second@example.test", "password": "Passw0rd!"},
    ).json()
    for account, email in ((first, first_email), (second, "second@example.test")):
        assert client.post(
            f"{API}/auth/otp/verify",
            json={"purpose": "register", "email": email, "code": latest_email_code(email)},
        ).status_code == 200

    response = client.post(
        f"{API}/auth/firebase/email/exchange",
        json={"id_token": f"test-email:{second['user_id']}:{first_email}:true"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FIREBASE_ACCOUNT_EXISTS"


def test_firebase_email_account_creation_failure_is_explicit(client, monkeypatch):
    def fail_create(*args):
        raise ApiError(503, "FIREBASE_UNAVAILABLE", "Firebase email authentication is temporarily unavailable.")

    monkeypatch.setattr(auth_module, "create_email_user", fail_create)
    response = client.post(
        f"{API}/auth/register",
        data={"role": "citizen", "full_name": "A B", "phone": "03103030303", "email": "failed@example.test", "password": "Passw0rd!"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "FIREBASE_UNAVAILABLE"


def test_unverified_phone_can_reregister(client):
    d = {"role": "citizen", "full_name": "A B", "phone": "03121212121", "email": "repeat@example.test", "password": "Passw0rd!"}
    assert client.post(f"{API}/auth/register", data=d).status_code == 201
    assert client.post(f"{API}/auth/register", data=d).status_code == 201


def test_lawyer_pending_and_requires_documents(client):
    d = {"role": "lawyer", "full_name": "Adv One", "phone": "03211234567", "email": "lawyer@example.test", "password": "Passw0rd!"}
    assert client.post(f"{API}/auth/register", data=d).json()["error"]["code"] == "BAR_COUNCIL_REQUIRED"
    d["bar_council_no"] = "PB-1234"
    assert client.post(f"{API}/auth/register", data=d).json()["error"]["code"] == "DOCUMENT_REQUIRED"
    bad = client.post(f"{API}/auth/register", data=d, files={"verification_document": ("x.exe", b"MZ....", "application/octet-stream")})
    assert bad.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    _, h = register_and_login(client, role="lawyer", phone="03211234567", bar_council_no="PB-1234")
    me = client.get(f"{API}/users/me", headers=h).json()
    assert me["verification_status"] == "pending" and me["lawyer"]["bar_council_no"] == "PB-1234"


def test_ngo_registration(client):
    _, h = register_and_login(client, role="ngo_monitor", phone="03221234567", organisation_name="Rights Watch", districts=["Lahore", "Rawalpindi"])
    me = client.get(f"{API}/users/me", headers=h).json()
    assert me["ngo"] == {"organisation_name": "Rights Watch", "districts": ["Lahore", "Rawalpindi"]}


def test_file_too_large(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    r = client.post(
        f"{API}/auth/register",
        data={"role": "lawyer", "full_name": "Adv", "phone": "03231234567", "email": "adv@example.test", "password": "Passw0rd!", "bar_council_no": "X"},
        files={"verification_document": ("a.png", PNG, "image/png")},
    )
    assert r.status_code == 413


def test_otp_wrong_code_then_lockout(client):
    _, headers = register_and_login(client, phone="03141414141")
    email = email_for_phone("03141414141")
    client.post(
        f"{API}/auth/otp/request",
        headers=headers,
        json={"purpose": "change_phone", "new_phone": "03141414142", "current_password": "Passw0rd!"},
    )
    good = latest_email_code(email)
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(5):
        assert client.post(f"{API}/auth/otp/verify", json={"purpose": "change_phone", "email": email, "phone": "03141414142", "code": wrong}).json()["error"]["code"] == "OTP_INCORRECT"
    locked = client.post(f"{API}/auth/otp/verify", json={"purpose": "change_phone", "email": email, "phone": "03141414142", "code": good})
    assert locked.status_code == 429 and locked.json()["error"]["code"] == "OTP_LOCKED"


def test_otp_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "otp_rate_limit", 4)
    _, headers = register_and_login(client, phone="03151515151")
    request = {"purpose": "change_phone", "new_phone": "03151515152", "current_password": "Passw0rd!"}
    for _ in range(3):
        assert client.post(f"{API}/auth/otp/request", headers=headers, json=request).status_code == 200
    r = client.post(f"{API}/auth/otp/request", headers=headers, json=request)
    assert r.status_code == 429 and r.json()["error"]["code"] == "OTP_RATE_LIMITED"


def test_old_otp_stops_working_after_resend(client):
    _, headers = register_and_login(client, phone="03161616161")
    email = email_for_phone("03161616161")
    request = {"purpose": "change_phone", "new_phone": "03161616162", "current_password": "Passw0rd!"}
    client.post(f"{API}/auth/otp/request", headers=headers, json=request)
    first = latest_email_code(email)
    client.post(f"{API}/auth/otp/request", headers=headers, json=request)
    second = latest_email_code(email)
    if first != second:
        assert client.post(f"{API}/auth/otp/verify", json={"purpose": "change_phone", "email": email, "phone": "03161616162", "code": first}).status_code == 400
    assert client.post(f"{API}/auth/otp/verify", json={"purpose": "change_phone", "email": email, "phone": "03161616162", "code": second}).status_code == 200


def test_refresh_rotation_and_reuse_detection(client, citizen):
    tokens, _ = citizen
    new = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert new.status_code == 200
    # the old token is now burned; replaying it kills the whole family
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": new.json()["refresh_token"]}).status_code == 401


def test_logout(client, citizen):
    tokens, h = citizen
    assert client.post(f"{API}/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_logout_without_refresh_token(client):
    assert client.post(f"{API}/auth/logout", json={}).status_code == 204
    assert client.post(f"{API}/auth/logout").status_code == 204


def test_auth_required_and_bad_token(client):
    r = client.get(f"{API}/users/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHENTICATED"
    r = client.get(f"{API}/users/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "FIREBASE_TOKEN_INVALID"


def test_login_rate_limit(client):
    for _ in range(10):
        client.post(f"{API}/auth/login", json={"phone": "03171717171", "password": "wrong-wrong"})
    r = client.post(f"{API}/auth/login", json={"phone": "03171717171", "password": "wrong-wrong"})
    assert r.status_code == 429


def test_admin_login_and_role_checks(client):
    phone, pw = make_admin()
    assert client.post(f"{API}/auth/login", json={"phone": phone, "password": pw}).json()["role"] == "admin"

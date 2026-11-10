from app.config import settings

from .conftest import API, PNG, make_admin, register_and_login


def test_password_reset_requires_verified_otp_and_single_use_grant(client):
    tokens, _ = register_and_login(client)
    req = client.post(f"{API}/auth/otp/request", json={"purpose": "reset", "phone": "03001234567"}).json()
    code = req["dev_otp"]
    wrong = "000000" if code != "000000" else "111111"
    invalid = client.post(f"{API}/auth/otp/verify", json={"purpose": "reset", "phone": "03001234567", "code": wrong})
    assert invalid.status_code == 400
    assert "reset_token" not in invalid.json()

    verified = client.post(f"{API}/auth/otp/verify", json={"purpose": "reset", "phone": "03001234567", "code": code})
    assert verified.status_code == 200 and verified.json()["verified"] is True
    grant = verified.json()["reset_token"]
    reset = client.post(f"{API}/auth/password/reset", json={"reset_token": grant, "new_password": "NewPassw0rd!"})
    assert reset.status_code == 200 and reset.json() == {"reset": True}
    replay = client.post(f"{API}/auth/password/reset", json={"reset_token": grant, "new_password": "OtherPassw0rd!"})
    assert replay.status_code == 400 and replay.json()["error"]["code"] == "RESET_TOKEN_INVALID"
    assert client.post(f"{API}/auth/otp/verify", json={"purpose": "reset", "phone": "03001234567", "code": code}).status_code == 400
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"phone": "03001234567", "password": "NewPassw0rd!"}).status_code == 200


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_citizen_register_verify_login_me(client):
    tokens, h = register_and_login(client, cnic="12345-1234567-1")
    me = client.get(f"{API}/users/me", headers=h).json()
    assert me["role"] == "citizen" and me["phone"] == "+923001234567"
    assert me["cnic_masked"] == "*****-*******-1"
    assert me["verification_status"] == "not_required"
    assert "12345-1234567" not in str(me)
    from .conftest import test_firestore
    raw = next(iter(test_firestore.data["users"].values()))["cnic"]
    assert raw and "12345-1234567-1" not in raw


def test_login_blocked_until_phone_verified(client):
    client.post(f"{API}/auth/register", data={"role": "citizen", "full_name": "A B", "phone": "03111111111", "password": "Passw0rd!"})
    r = client.post(f"{API}/auth/login", json={"phone": "03111111111", "password": "Passw0rd!"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "PHONE_NOT_VERIFIED"


def test_wrong_password_and_error_shape(client, citizen):
    r = client.post(f"{API}/auth/login", json={"phone": "03001234567", "password": "nope-nope"})
    assert r.status_code == 401 and r.json() == {"error": {"code": "INVALID_CREDENTIALS", "message": "Phone number or password is incorrect."}}


def test_admin_cannot_self_register(client):
    r = client.post(f"{API}/auth/register", data={"role": "admin", "full_name": "Evil", "phone": "03001112222", "password": "Passw0rd!"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "ADMIN_REGISTRATION_FORBIDDEN"


def test_validation_errors(client):
    base = {"role": "citizen", "full_name": "A B", "phone": "03001112222", "password": "Passw0rd!"}
    assert client.post(f"{API}/auth/register", data={**base, "cnic": "123"}).json()["error"]["code"] == "INVALID_CNIC"
    assert client.post(f"{API}/auth/register", data={**base, "phone": "12345"}).json()["error"]["code"] == "INVALID_PHONE"
    assert client.post(f"{API}/auth/register", data={**base, "password": "short"}).json()["error"]["code"] == "WEAK_PASSWORD"
    assert client.post(f"{API}/auth/register", data={**base, "role": "wizard"}).json()["error"]["code"] == "INVALID_ROLE"
    r = client.post(f"{API}/auth/register", data={"role": "citizen"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_verified_phone(client, citizen):
    r = client.post(f"{API}/auth/register", data={"role": "citizen", "full_name": "X Y", "phone": "0300-1234567", "password": "Passw0rd!"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "PHONE_IN_USE"


def test_unverified_phone_can_reregister(client):
    d = {"role": "citizen", "full_name": "A B", "phone": "03121212121", "password": "Passw0rd!"}
    assert client.post(f"{API}/auth/register", data=d).status_code == 201
    assert client.post(f"{API}/auth/register", data=d).status_code == 201


def test_lawyer_pending_and_requires_documents(client):
    d = {"role": "lawyer", "full_name": "Adv One", "phone": "03211234567", "password": "Passw0rd!"}
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
        data={"role": "lawyer", "full_name": "Adv", "phone": "03231234567", "password": "Passw0rd!", "bar_council_no": "X"},
        files={"verification_document": ("a.png", PNG, "image/png")},
    )
    assert r.status_code == 413


def test_otp_wrong_code_then_lockout(client):
    r = client.post(f"{API}/auth/register", data={"role": "citizen", "full_name": "A B", "phone": "03141414141", "password": "Passw0rd!"})
    good = r.json()["dev_otp"]
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(5):
        assert client.post(f"{API}/auth/otp/verify", json={"purpose": "register", "phone": "03141414141", "code": wrong}).json()["error"]["code"] == "OTP_INVALID"
    locked = client.post(f"{API}/auth/otp/verify", json={"purpose": "register", "phone": "03141414141", "code": good})
    assert locked.status_code == 429 and locked.json()["error"]["code"] == "OTP_LOCKED"


def test_otp_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "otp_rate_limit", 3)
    d = {"role": "citizen", "full_name": "A B", "phone": "03151515151", "password": "Passw0rd!"}
    assert client.post(f"{API}/auth/register", data=d).status_code == 201
    for _ in range(2):
        assert client.post(f"{API}/auth/otp/request", json={"purpose": "register", "phone": "03151515151"}).status_code == 200
    r = client.post(f"{API}/auth/otp/request", json={"purpose": "register", "phone": "03151515151"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "OTP_RATE_LIMITED"


def test_old_otp_stops_working_after_resend(client):
    d = {"role": "citizen", "full_name": "A B", "phone": "03161616161", "password": "Passw0rd!"}
    first = client.post(f"{API}/auth/register", data=d).json()["dev_otp"]
    second = client.post(f"{API}/auth/otp/request", json={"purpose": "register", "phone": "03161616161"}).json()["dev_otp"]
    if first != second:
        assert client.post(f"{API}/auth/otp/verify", json={"purpose": "register", "phone": "03161616161", "code": first}).status_code == 400
    assert client.post(f"{API}/auth/otp/verify", json={"purpose": "register", "phone": "03161616161", "code": second}).status_code == 200


def test_password_reset_revokes_sessions(client):
    tokens, _ = register_and_login(client)
    req = client.post(f"{API}/auth/otp/request", json={"purpose": "reset", "phone": "03001234567"}).json()
    ok = client.post(f"{API}/auth/otp/verify", json={"purpose": "reset", "phone": "03001234567", "code": req["dev_otp"], "new_password": "NewPassw0rd!"})
    assert ok.status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"phone": "03001234567", "password": "Passw0rd!"}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"phone": "03001234567", "password": "NewPassw0rd!"}).status_code == 200


def test_reset_for_unknown_phone_returns_clear_mismatch(client):
    r = client.post(f"{API}/auth/otp/request", json={"purpose": "reset", "phone": "03009990000"})
    assert r.status_code == 404
    assert r.json()["error"] == {
        "code": "RESET_PHONE_NOT_FOUND",
        "message": "No verified account is registered with that phone number.",
    }


def test_reset_otp_expires(client):
    from datetime import timedelta

    from app.db import FirestoreSession
    from app.models import OtpCode
    from app.utils import utcnow
    from .conftest import test_firestore

    register_and_login(client)
    req = client.post(f"{API}/auth/otp/request", json={"purpose": "reset", "phone": "03001234567"}).json()
    assert len(req["dev_otp"]) == 6 and req["dev_otp"].isdigit()
    db = FirestoreSession(test_firestore)
    otp = db.query(OtpCode).filter_by(phone="+923001234567", purpose="reset").one()
    assert abs((otp.expires_at - otp.created_at).total_seconds() - 60) < 0.01
    otp.expires_at = utcnow()
    db.commit()
    db.close()
    expired = client.post(
        f"{API}/auth/otp/verify",
        json={"purpose": "reset", "phone": "03001234567", "code": req["dev_otp"]},
    )
    assert expired.status_code == 400 and expired.json()["error"]["code"] == "OTP_INVALID"


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

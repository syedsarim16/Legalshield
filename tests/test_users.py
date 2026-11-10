from .conftest import API, make_admin, register_and_login


def test_update_profile(client, citizen):
    _, h = citizen
    r = client.patch(f"{API}/users/me", headers=h, json={"full_name": "New Name", "cnic": "35202-1234567-9"})
    assert r.status_code == 200 and r.json()["full_name"] == "New Name" and r.json()["cnic_masked"].endswith("9")
    assert client.patch(f"{API}/users/me", headers=h, json={"cnic": "bad"}).json()["error"]["code"] == "INVALID_CNIC"


def test_preferences_are_saved_and_loaded_from_firestore(client, citizen):
    _, headers = citizen
    path = f"{API}/users/me/preferences"
    assert client.get(path, headers=headers).json() == {}
    preferences = {"lang": "ur", "theme": "dark", "discreet": True}
    saved = client.put(path, headers=headers, json=preferences)
    assert saved.status_code == 200 and saved.json() == preferences
    assert client.get(path, headers=headers).json() == preferences
    assert client.put(path, headers=headers, json={**preferences, "unknown": "value"}).status_code == 422


def test_emergency_contacts_crud_and_ownership(client, citizen):
    _, h = citizen
    c = client.post(f"{API}/users/me/contacts", headers=h, json={"name": "Ali", "phone": "0312 3456789"})
    assert c.status_code == 201 and c.json()["phone"] == "+923123456789"
    assert len(client.get(f"{API}/users/me/contacts", headers=h).json()["contacts"]) == 1
    _, h2 = register_and_login(client, phone="03331234567")
    assert client.delete(f"{API}/users/me/contacts/{c.json()['id']}", headers=h2).status_code == 404
    assert client.delete(f"{API}/users/me/contacts/{c.json()['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/users/me/contacts", headers=h).json()["contacts"] == []


def test_contacts_are_citizen_only(client):
    _, h = register_and_login(client, role="lawyer", phone="03241234567", bar_council_no="L-1")
    assert client.get(f"{API}/users/me/contacts", headers=h).status_code == 403


def test_device_registration_is_idempotent(client, citizen):
    _, h = citizen
    for _ in range(2):
        assert client.post(f"{API}/users/me/devices", headers=h, json={"fcm_token": "x" * 40}).json() == {"registered": True}


def test_change_phone_flow(client, citizen):
    tokens, h = citizen
    bad = client.post(f"{API}/auth/otp/request", headers=h, json={"purpose": "change_phone", "new_phone": "03351234567", "current_password": "wrong-pass"})
    assert bad.status_code == 401
    r = client.post(f"{API}/auth/otp/request", headers=h, json={"purpose": "change_phone", "new_phone": "03351234567", "current_password": "Passw0rd!"})
    assert r.status_code == 200
    v = client.post(f"{API}/auth/otp/verify", json={"purpose": "change_phone", "phone": "03351234567", "code": r.json()["dev_otp"]})
    assert v.status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.post(f"{API}/auth/login", json={"phone": "03351234567", "password": "Passw0rd!"}).status_code == 200
    assert client.post(f"{API}/auth/login", json={"phone": "03001234567", "password": "Passw0rd!"}).status_code == 401


def test_change_phone_rejects_taken_number(client, citizen):
    _, h = citizen
    register_and_login(client, phone="03361234567")
    r = client.post(f"{API}/auth/otp/request", headers=h, json={"purpose": "change_phone", "new_phone": "03361234567", "current_password": "Passw0rd!"})
    assert r.status_code == 409


def test_delete_account(client, citizen):
    _, h = citizen
    client.post(f"{API}/users/me/contacts", headers=h, json={"name": "Ali", "phone": "03123456789"})
    wrong = client.request("DELETE", f"{API}/users/me", headers=h, json={"password": "wrong-pass"})
    assert wrong.status_code == 401
    ok = client.request("DELETE", f"{API}/users/me", headers=h, json={"password": "Passw0rd!"})
    assert ok.status_code == 204
    assert client.post(f"{API}/auth/login", json={"phone": "03001234567", "password": "Passw0rd!"}).status_code == 401
    assert client.get(f"{API}/users/me", headers=h).status_code == 401
    # the number is free again
    register_and_login(client)


def test_admin_cannot_delete_account(client):
    phone, pw = make_admin()
    tokens = client.post(f"{API}/auth/login", json={"phone": phone, "password": pw}).json()
    h = {"Authorization": f"Bearer {tokens['firebase_custom_token']}"}
    r = client.request("DELETE", f"{API}/users/me", headers=h, json={"password": pw})
    assert r.status_code == 403 and r.json()["error"]["code"] == "ADMIN_DELETE_FORBIDDEN"

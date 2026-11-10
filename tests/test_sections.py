from app.config import settings
from legalshield_ai.ingest import upsert_statutes
from app.db import FirestoreSession
from .conftest import test_firestore

from .conftest import API, register_and_login


def test_get_offence_section(client, citizen):
    _, h = citizen
    r = client.get(f"{API}/sections/PPC/302", headers=h).json()
    s = r["section"]
    assert r["covered"] is True and s["kind"] == "offence"
    assert s["bailable"] is False and s["cognizable"] is True
    assert "not legal advice" in r["disclaimer"]


def test_law_and_number_are_case_insensitive(client, citizen):
    _, h = citizen
    assert client.get(f"{API}/sections/crpc/497", headers=h).json()["section"]["section_number"] == "497"
    assert client.get(f"{API}/sections/ppc/302", headers=h).json()["covered"] is True


def test_uncovered_section_is_not_guessed(client, citizen):
    _, h = citizen
    r = client.get(f"{API}/sections/PPC/999", headers=h)
    assert r.status_code == 200 and r.json() == {"covered": False, "section": None, "disclaimer": r.json()["disclaimer"]}


def test_invalid_law(client, citizen):
    _, h = citizen
    assert client.get(f"{API}/sections/XYZ/1", headers=h).json()["error"]["code"] == "INVALID_LAW"
    assert client.get(f"{API}/sections/search?q=theft&law=XYZ", headers=h).status_code == 422


def test_search_by_number_and_keyword(client, citizen):
    _, h = citizen
    by_number = client.get(f"{API}/sections/search", params={"q": "302"}, headers=h).json()["results"]
    assert by_number[0]["section_number"] == "302"
    by_word = client.get(f"{API}/sections/search", params={"q": "theft"}, headers=h).json()["results"]
    assert any(x["section_number"] == "379" for x in by_word)
    roman = client.get(f"{API}/sections/search", params={"q": "chori"}, headers=h).json()["results"]
    assert any(x["section_number"] == "379" for x in roman)
    only_crpc = client.get(f"{API}/sections/search", params={"q": "bail", "law": "CrPC"}, headers=h).json()["results"]
    assert only_crpc and all(x["law"] == "CrPC" for x in only_crpc)


def test_search_requires_login_and_works_for_lawyers(client):
    assert client.get(f"{API}/sections/search?q=theft").status_code == 401
    _, h = register_and_login(client, role="lawyer", phone="03251234567", bar_council_no="L-2")
    assert client.get(f"{API}/sections/search?q=theft", headers=h).status_code == 200


def test_unreviewed_hidden_when_not_allowed(client, citizen, monkeypatch):
    _, h = citizen
    monkeypatch.setattr(settings, "allow_unreviewed_statutes", False)
    assert client.get(f"{API}/sections/PPC/302", headers=h).json()["covered"] is False


def test_ingest_rejects_incomplete_and_unreviewed():
    base = dict(law="PPC", section_number="1", title="T", text_en="x", kind="offence", bailable=True, cognizable=False, compoundable="yes")
    with FirestoreSession(test_firestore) as db:
        res = upsert_statutes(db, [{**base, "section_number": "901"}, {**base, "section_number": "902", "compoundable": None}], allow_unreviewed=False)
        assert res["upserted"] == 0 and len(res["rejected"]) == 2
        res = upsert_statutes(db, [{**base, "section_number": "903", "reviewed_by_advisor": True}], allow_unreviewed=False)
        assert res["upserted"] == 1
        res = upsert_statutes(db, [{**base, "section_number": "903", "title": "Changed", "reviewed_by_advisor": True}], allow_unreviewed=False)
        assert res["upserted"] == 1

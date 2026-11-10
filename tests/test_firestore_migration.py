import sqlite3

from scripts import migrate_sqlite_to_firestore
from .conftest import Firestore


def _legacy_db(path):
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE users (id TEXT PRIMARY KEY, role TEXT, full_name TEXT, phone TEXT, cnic TEXT, "
            "password_hash TEXT, phone_verified INTEGER, verification_status TEXT, verification_note TEXT, "
            "verification_document_key TEXT, created_at TEXT)"
        )
        connection.executemany(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("existing", "citizen", "Old Name", "+923000000001", None, "hash", 1, "verified", None, None, "2024-01-01T00:00:00"),
                ("new", "citizen", "New Name", "+923000000002", None, "hash", 0, "not_required", None, None, "2024-01-01T00:00:00"),
            ],
        )


def test_migration_creates_new_documents_and_never_overwrites(tmp_path, monkeypatch):
    source = tmp_path / "legacy.db"
    _legacy_db(source)
    firestore = Firestore()
    firestore.collection("users").document("existing").set({"full_name": "Preserve me"})
    monkeypatch.setattr(migrate_sqlite_to_firestore, "firestore_client", lambda: firestore)

    report = migrate_sqlite_to_firestore.migrate(source)

    assert report == {"users": {"copied": 1, "already_present": 1}}
    assert firestore.collection("users").document("existing").get().to_dict() == {"full_name": "Preserve me"}
    assert firestore.collection("users").document("new").get().to_dict()["full_name"] == "New Name"


def test_migration_dry_run_does_not_connect_to_firebase(tmp_path, monkeypatch):
    source = tmp_path / "legacy.db"
    _legacy_db(source)

    def fail_if_called():
        raise AssertionError("dry run must not connect to Firebase")

    monkeypatch.setattr(migrate_sqlite_to_firestore, "firestore_client", fail_if_called)
    assert migrate_sqlite_to_firestore.migrate(source, dry_run=True) == {"users": {"copied": 2, "already_present": 0}}

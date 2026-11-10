"""Copy legacy SQLite records to Firestore without overwriting destination documents."""
import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from google.api_core.exceptions import AlreadyExists

from app.firebase import firestore_client
from app.models import (
    Device,
    EmergencyContact,
    FirebaseIdentity,
    LawyerProfile,
    NgoProfile,
    OtpCode,
    PasswordResetGrant,
    RefreshToken,
    StatuteSection,
    User,
)
from app.utils import normalize_utc

MODELS = (
    User,
    FirebaseIdentity,
    LawyerProfile,
    NgoProfile,
    OtpCode,
    PasswordResetGrant,
    RefreshToken,
    Device,
    EmergencyContact,
    StatuteSection,
)
JSON_FIELDS = {"cities", "specializations", "districts"}
BOOL_FIELDS = {"phone_verified", "consumed", "revoked", "pro_bono", "sos_opt_in", "reviewed_by_advisor"}
DATETIME_FIELDS = {"created_at", "expires_at"}


def _convert(values: dict) -> dict:
    for key, value in values.items():
        if value is None:
            continue
        if key in JSON_FIELDS and isinstance(value, str):
            values[key] = json.loads(value)
        elif key in BOOL_FIELDS:
            values[key] = bool(value)
        elif key in DATETIME_FIELDS and isinstance(value, str):
            values[key] = normalize_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))
    return values


def migrate(source: Path, dry_run: bool = False) -> dict[str, dict[str, int]]:
    if not source.is_file():
        raise FileNotFoundError(f"SQLite source does not exist: {source}")
    client = None if dry_run else firestore_client()
    connection = sqlite3.connect(source)
    connection.row_factory = sqlite3.Row
    counts = {}
    try:
        existing_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        for model in MODELS:
            table = model.__collection__
            if table not in existing_tables:
                continue
            copied = skipped = 0
            key_field = model.__key__
            for row in connection.execute(f'SELECT * FROM "{table}"'):
                values = _convert(dict(row))
                document_id = values[key_field]
                if dry_run:
                    copied += 1
                    continue
                reference = client.collection(table).document(str(document_id))
                try:
                    reference.create(values)
                    copied += 1
                except AlreadyExists:
                    skipped += 1
            counts[table] = {"copied": copied, "already_present": skipped}
    finally:
        connection.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("legalshield.db"))
    parser.add_argument("--dry-run", action="store_true", help="Count source records without connecting to Firebase.")
    args = parser.parse_args()
    results = migrate(args.source, dry_run=args.dry_run)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

"""Load statute records (F-06) from a JSON file: either a list, or {"records": [...]}.
Records need reviewed_by_advisor=true unless --allow-unreviewed is passed.
Usage: python -m scripts.load_statutes path/to/statutes.json [--allow-unreviewed]"""
import argparse
import json

from app.db import FirestoreSession, firestore_client
from legalshield_ai.ingest import upsert_statutes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--allow-unreviewed", action="store_true")
    a = ap.parse_args()
    data = json.load(open(a.path, encoding="utf-8"))
    records = data["records"] if isinstance(data, dict) else data
    with FirestoreSession(firestore_client()) as db:
        print(json.dumps(upsert_statutes(db, records, allow_unreviewed=a.allow_unreviewed), indent=2))


if __name__ == "__main__":
    main()

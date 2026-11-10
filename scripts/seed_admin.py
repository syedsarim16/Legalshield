"""Create (or reset) an admin account. Admins cannot self-register.
Usage: python -m scripts.seed_admin --phone 0300 1234567 --name "Admin" --password 'S0me-long-pass'"""
import argparse

from app.db import FirestoreSession, firestore_client, select
from app.models import User
from app.security import hash_password
from app.utils import normalize_phone, validate_password


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phone", required=True)
    ap.add_argument("--name", default="Administrator")
    ap.add_argument("--password", required=True)
    a = ap.parse_args()
    phone = normalize_phone(a.phone)
    validate_password(a.password)
    with FirestoreSession(firestore_client()) as db:
        user = db.scalar(select(User).where(User.phone == phone))
        if user is None:
            user = User(role="admin", full_name=a.name, phone=phone, password_hash=hash_password(a.password), phone_verified=True)
            db.add(user)
            print(f"Created admin {phone}")
        else:
            user.role, user.password_hash, user.phone_verified = "admin", hash_password(a.password), True
            print(f"Updated existing user {phone} to admin")
        db.commit()


if __name__ == "__main__":
    main()

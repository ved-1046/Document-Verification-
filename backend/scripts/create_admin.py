"""Interactively bootstrap the first administrator without exposing secrets.

Run from backend after the configured database schema is migrated:
    python scripts/create_admin.py
"""
from getpass import getpass

from sqlalchemy import func

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def main() -> None:
    name = input("Administrator full name: ").strip()
    email = input("Administrator email: ").strip().lower()
    password = getpass("Administrator password (12+ characters): ")
    confirmation = getpass("Confirm password: ")
    if not name or not email:
        raise SystemExit("Name and email are required.")
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise SystemExit("Password must be between 12 and 72 UTF-8 bytes.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        existing = db.query(User.id).filter(func.lower(User.email) == email).first()
        if existing:
            raise SystemExit("An account with this email already exists; no changes were made.")
        db.add(User(
            display_name=name,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.admin,
            is_active=True,
        ))
        db.commit()
    print("Administrator account created. Password was not stored in plaintext or written to logs.")


if __name__ == "__main__":
    main()

"""
Seed demo users for local testing.

Run from backend/:
    .venv/Scripts/python.exe scripts/seed_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password

DEMO_USERS = [
    ("Alex Submitter", "submitter@example.com", UserRole.submitter),
    ("Riley Reviewer", "reviewer@example.com", UserRole.reviewer),
    ("Avery Approver", "approver@example.com", UserRole.approver),
]

PASSWORD = "password123"


def main() -> None:
    db = SessionLocal()

    try:
        for name, email, role in DEMO_USERS:
            email = email.lower()
            existing = db.query(User).filter(User.email == email).first()

            if existing:
                # Never reset an existing account's password, role, or status.
                print(f"  kept existing account unchanged: {email}")
            else:
                user = User(
                    display_name=name,
                    email=email,
                    password_hash=hash_password(PASSWORD),
                    role=role,
                    is_active=True,
                )
                db.add(user)
                print(f"  created {email}")

        db.commit()
        print("\nDemo password applies only to accounts created by this run.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()

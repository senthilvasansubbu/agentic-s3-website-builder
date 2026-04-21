"""
Create the platform superuser (admin) account.

Usage:
    python scripts/create_superuser.py

Environment variables used:
    ADMIN_EMAIL    (default: admin@websitebuilder.ai)
    ADMIN_PASSWORD (default: Admin@1234  — CHANGE IN PRODUCTION)
    ADMIN_NAME     (default: Super Admin)
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from database.snowflake_client import db
from database.migrations import run_migrations
from services.auth_service import hash_password

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL",    "admin@websitebuilder.ai")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")
ADMIN_NAME     = os.getenv("ADMIN_NAME",     "Super Admin")


def create_superuser():
    # Ensure tables exist first
    run_migrations()

    existing = db.fetchone("SELECT user_id FROM users WHERE email = ?", (ADMIN_EMAIL,))
    if existing:
        # Update password and ensure plan=superuser
        pw_hash = hash_password(ADMIN_PASSWORD)
        db.execute(
            "UPDATE users SET password_hash=?, plan='superuser', role='superuser', is_verified=1 WHERE email=?",
            (pw_hash, ADMIN_EMAIL),
        )
        print(f"✅ Superuser '{ADMIN_EMAIL}' updated (password reset).")
        return

    user_id   = str(uuid.uuid4())
    pw_hash   = hash_password(ADMIN_PASSWORD)

    db.execute(
        "INSERT INTO users (user_id, email, password_hash, full_name, is_verified, plan, role) "
        "VALUES (?, ?, ?, ?, 1, 'superuser', 'superuser')",
        (user_id, ADMIN_EMAIL, pw_hash, ADMIN_NAME),
    )

    print("✅ Superuser created successfully!")
    print(f"   Email   : {ADMIN_EMAIL}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"   Role    : superuser")
    print("\n   Login at: http://localhost:8000/login")
    print("   ⚠️  Change your password after first login!")


if __name__ == "__main__":
    create_superuser()

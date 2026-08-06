"""Create the first local administrator from environment variables.

Run from the backend directory after setting ADMIN_EMAIL and ADMIN_PASSWORD.
"""

import os
import sys

from app.db.database import SessionLocal, init_db
from app.models.user import User
from app.services.security import hash_password


def main() -> int:
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    nickname = os.getenv("ADMIN_NICKNAME", "管理员").strip() or "管理员"
    if not email or not password:
        print("Please set ADMIN_EMAIL and ADMIN_PASSWORD before running this script.")
        return 1
    if len(password) < 8:
        print("ADMIN_PASSWORD must contain at least 8 characters.")
        return 1

    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.role = "admin"
            user.nickname = nickname
            user.password_hash = hash_password(password)
            user.is_active = True
            message = "Existing account promoted to administrator."
        else:
            db.add(User(
                email=email,
                nickname=nickname,
                password_hash=hash_password(password),
                role="admin",
            ))
            message = "Administrator account created."
        db.commit()
        print(message)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

"""
Reset admin password utility.
Usage: python reset_password.py <new_password>
       python reset_password.py              (defaults to 'admin123')
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.models import User
from app.core.database import Base, engine

# Ensure tables exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

new_password = sys.argv[1] if len(sys.argv) > 1 else "admin123"

admin = db.query(User).filter(User.is_admin == True).first()

if not admin:
    print("No admin user found. Creating one...")
    admin = User(
        email="admin@admin.com",
        hashed_password=hash_password(new_password),
        full_name="Admin",
        is_admin=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print(f"Admin created: admin@admin.com / {new_password}")
else:
    admin.hashed_password = hash_password(new_password)
    admin.is_active = True
    db.commit()
    print(f"Password reset for: {admin.email}")
    print(f"New password: {new_password}")

db.close()

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from auth.database import auth_engine, AuthBase, AuthSessionLocal
from auth.models import User
from auth.security import generate_id, hash_password
from auth.audit import next_user_id

DEMO_USERS = [
    {
        "full_name": "Admin User",
        "email": "admin@sankalp.gov.in",
        "password": "admin123",
        "role": "admin",
        "department": "Digital India Corporation",
        "designation": "System Administrator",
    },
    {
        "full_name": "Rajesh Kumar",
        "email": "officer@sankalp.gov.in",
        "password": "officer123",
        "role": "officer",
        "department": "Ministry of Road Transport",
        "designation": "Project Monitoring Officer",
    },
    {
        "full_name": "Priya Sharma",
        "email": "analyst@sankalp.gov.in",
        "password": "analyst123",
        "role": "analyst",
        "department": "NITI Aayog",
        "designation": "Risk Analyst",
    },
    {
        "full_name": "Amit Verma",
        "email": "viewer@sankalp.gov.in",
        "password": "viewer123",
        "role": "viewer",
        "department": "Ministry of Finance",
        "designation": "Budget Review Officer",
    },
]

EXPECTED_USER_IDS = {
    "admin@sankalp.gov.in": "USR-0001",
    "officer@sankalp.gov.in": "USR-0002",
    "analyst@sankalp.gov.in": "USR-0003",
    "viewer@sankalp.gov.in": "USR-0004",
}

LEGACY_DEMO_EMAILS = {
    "admin@govrisk.gov.in": "admin@sankalp.gov.in",
    "officer@govrisk.gov.in": "officer@sankalp.gov.in",
    "analyst@govrisk.gov.in": "analyst@sankalp.gov.in",
    "viewer@govrisk.gov.in": "viewer@sankalp.gov.in",
}


def seed_auth():
    AuthBase.metadata.create_all(bind=auth_engine)
    db = AuthSessionLocal()
    try:
        created = 0
        migrated = 0
        skipped = 0
        for u in DEMO_USERS:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                if not existing.user_id:
                    existing.user_id = EXPECTED_USER_IDS.get(u["email"]) or next_user_id(db)
                    print(f"  [backfill] {u['email']} -> {existing.user_id}")
                else:
                    print(f"  [skip] {u['email']} already exists ({existing.user_id})")
                skipped += 1
                continue
            legacy_email = next(
                (old_email for old_email, new_email in LEGACY_DEMO_EMAILS.items() if new_email == u["email"]),
                None,
            )
            existing = db.query(User).filter(User.email == legacy_email).first() if legacy_email else None
            if existing:
                existing.email = u["email"]
                existing.password_hash = hash_password(u["password"])
                existing.is_active = True
                migrated += 1
                print(f"  [migrated] {legacy_email} -> {u['email']} ({existing.user_id})")
                continue
            user = User(
                id=generate_id(),
                user_id=EXPECTED_USER_IDS.get(u["email"]) or next_user_id(db),
                full_name=u["full_name"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                role=u["role"],
                department=u["department"],
                designation=u["designation"],
                is_active=True,
            )
            db.add(user)
            created += 1
            print(f"  [created] {u['email']} ({u['role']}) {user.user_id}")
        db.commit()
        print(f"\nAuth seed complete. {created} users created, {migrated} migrated, {skipped} skipped.")
        print("\nDemo accounts:")
        for u in DEMO_USERS:
            uid = EXPECTED_USER_IDS.get(u["email"], "")
            print(f"  {uid}  {u['email']} / {u['password']} ({u['role']})")
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding auth database...\n")
    seed_auth()
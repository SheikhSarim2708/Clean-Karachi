from werkzeug.security import generate_password_hash
from db import get_db

USERS = [
    ("System Admin", "admin@cleankarachi.com", "admin123", 3),
    ("Ahmed Raza", "staff1@cleankarachi.com", "staff123", 2),
    ("Bilal Khan", "staff2@cleankarachi.com", "staff123", 2),
]

db = get_db()
try:
    with db.cursor() as cur:
        for name, email, password, role_id in USERS:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                print(f"Skipped (already exists): {email}")
                continue
            cur.execute(
                "INSERT INTO users (name, email, password_hash, role_id) "
                "VALUES (%s, %s, %s, %s)",
                (name, email, generate_password_hash(password), role_id),
            )
            print(f"Created: {email}")
    db.commit()
finally:
    db.close()
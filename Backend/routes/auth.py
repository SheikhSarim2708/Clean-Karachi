from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash , check_password_hash
from db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

CITIZEN_ROLE_ID = 1

@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""

    # Input validation
    if not name or not email or not password:
        return jsonify(error="Name, email, and password are required"), 400
    if "@" not in email or "." not in email:
        return jsonify(error="Please provide a valid email address"), 400
    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters long"), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            # Reject duplicate email addresses
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify(error="Email is already registered"), 409

            cur.execute(
                "INSERT INTO users (name, email, phone, password_hash, role_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (name, email, phone, generate_password_hash(password), CITIZEN_ROLE_ID),
            )
        db.commit()
    finally:
        db.close()

    return jsonify(message="Registration successful"), 201

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify(error="Email and password are required"), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.name, u.password_hash, r.name AS role "
                "FROM users u JOIN roles r ON u.role_id = r.id "
                "WHERE u.email = %s AND u.is_active = 1",
                (email,),
            )
            user = cur.fetchone()
    finally:
        db.close()

    # Same message for unknown email and wrong password
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Invalid email or password"), 401

    session.clear()
    session["user_id"] = user["id"]
    session["role"] = user["role"]
    return jsonify(message="Login successful", name=user["name"], role=user["role"])


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify(message="Logout successful")


@auth_bp.get("/me")
def me():
    if "user_id" not in session:
        return jsonify(error="Login required"), 401
    return jsonify(user_id=session["user_id"], role=session["role"])

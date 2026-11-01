from flask import Blueprint, jsonify
from db import get_db
from utils.auth_utils import role_required

lookup_bp = Blueprint("lookup", __name__, url_prefix="/api")


def fetch_active(table):
    """Return all active rows (id, name) from the given lookup table."""
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(f"SELECT id, name FROM {table} WHERE is_active = 1 ORDER BY name")
            return cur.fetchall()
    finally:
        db.close()


@lookup_bp.get("/categories")
@role_required("citizen", "staff", "admin")
def get_categories():
    return jsonify(fetch_active("categories"))


@lookup_bp.get("/areas")
@role_required("citizen", "staff", "admin")
def get_areas():
    return jsonify(fetch_active("areas"))
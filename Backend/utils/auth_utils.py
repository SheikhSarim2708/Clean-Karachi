from functools import wraps
from flask import session, jsonify


def role_required(*roles):
    """Allow access only to logged-in users having one of the given roles."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify(error="Login required"), 401
            if session.get("role") not in roles:
                return jsonify(error="Access denied"), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
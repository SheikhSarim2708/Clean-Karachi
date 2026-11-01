from flask import Blueprint, request, jsonify, session, Response
import csv
import io
from werkzeug.security import generate_password_hash
from db import get_db
from utils.auth_utils import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

PAGE_SIZE = 10


@admin_bp.get("/complaints")
@role_required("admin")
def list_all_complaints():
    args = request.args
    where = []
    params = []

    # Each filter is optional; add a condition only if it was supplied
    if args.get("status"):
        where.append("c.status = %s")
        params.append(args["status"])
    if args.get("category_id", type=int):
        where.append("c.category_id = %s")
        params.append(args.get("category_id", type=int))
    if args.get("area_id", type=int):
        where.append("c.area_id = %s")
        params.append(args.get("area_id", type=int))
    if args.get("from"):
        where.append("DATE(c.created_at) >= %s")
        params.append(args["from"])
    if args.get("to"):
        where.append("DATE(c.created_at) <= %s")
        params.append(args["to"])
    if args.get("search"):
        where.append("c.title LIKE %s")
        params.append("%" + args["search"] + "%")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    page = max(args.get("page", default=1, type=int), 1)
    offset = (page - 1) * PAGE_SIZE

    base = (
        "FROM complaints c "
        "JOIN users u ON c.citizen_id = u.id "
        "JOIN categories cat ON c.category_id = cat.id "
        "JOIN areas a ON c.area_id = a.id"
        + where_sql
    )

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total " + base, params)
            total = cur.fetchone()["total"]

            cur.execute(
                "SELECT c.id, c.title, c.status, c.created_at, "
                "u.name AS citizen, cat.name AS category, a.name AS area "
                + base +
                " ORDER BY c.created_at DESC, c.id DESC LIMIT %s OFFSET %s",
                params + [PAGE_SIZE, offset],
            )
            rows = cur.fetchall()
    finally:
        db.close()

    return jsonify(page=page, page_size=PAGE_SIZE, total=total, complaints=rows)

@admin_bp.put("/complaints/<int:complaint_id>/assign")
@role_required("admin")
def assign_complaint(complaint_id):
    data = request.get_json(silent=True) or {}
    staff_id = data.get("staff_id")

    if not isinstance(staff_id, int):
        return jsonify(error="A valid staff member must be selected"), 400

    admin_id = session["user_id"]

    db = get_db()
    try:
        with db.cursor() as cur:
            # 1) The complaint must exist and must not be resolved
            cur.execute("SELECT id, status FROM complaints WHERE id = %s", (complaint_id,))
            complaint = cur.fetchone()
            if not complaint:
                return jsonify(error="Complaint not found"), 404
            if complaint["status"] == "resolved":
                return jsonify(error="A resolved complaint cannot be reassigned"), 409

            # 2) The target must be an active staff member
            cur.execute(
                "SELECT u.id FROM users u JOIN roles r ON u.role_id = r.id "
                "WHERE u.id = %s AND r.name = 'staff' AND u.is_active = 1",
                (staff_id,),
            )
            if not cur.fetchone():
                return jsonify(error="Selected user is not an active staff member"), 400

            # 3) Reject if this staff member already holds the complaint
            cur.execute(
                "SELECT id FROM assignments "
                "WHERE complaint_id = %s AND staff_id = %s AND is_current = 1",
                (complaint_id, staff_id),
            )
            if cur.fetchone():
                return jsonify(error="Complaint is already assigned to this staff member"), 409

            # 4) Mark any previous assignment as old (history is kept)
            cur.execute(
                "UPDATE assignments SET is_current = 0 "
                "WHERE complaint_id = %s AND is_current = 1",
                (complaint_id,),
            )

            # 5) Create the new current assignment
            cur.execute(
                "INSERT INTO assignments (complaint_id, staff_id, assigned_by) "
                "VALUES (%s, %s, %s)",
                (complaint_id, staff_id, admin_id),
            )

            # 6) First assignment only: move status pending -> assigned
            if complaint["status"] == "pending":
                cur.execute(
                    "UPDATE complaints SET status = 'assigned' WHERE id = %s",
                    (complaint_id,),
                )
                cur.execute(
                    "INSERT INTO complaint_status_history (complaint_id, status, changed_by) "
                    "VALUES (%s, 'assigned', %s)",
                    (complaint_id, admin_id),
                )
        db.commit()
    except Exception:
        db.rollback()
        return jsonify(error="Could not assign the complaint. Please try again"), 500
    finally:
        db.close()

    return jsonify(message="Complaint assigned successfully")

@admin_bp.get("/complaints/<int:complaint_id>")
@role_required("admin")
def get_complaint_detail(complaint_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            # Main complaint info (no ownership restriction for admin)
            cur.execute(
                "SELECT c.id, c.title, c.description, c.address_detail, c.status, "
                "c.created_at, c.updated_at, "
                "u.name AS citizen, u.email AS citizen_email, u.phone AS citizen_phone, "
                "cat.name AS category, a.name AS area "
                "FROM complaints c "
                "JOIN users u ON c.citizen_id = u.id "
                "JOIN categories cat ON c.category_id = cat.id "
                "JOIN areas a ON c.area_id = a.id "
                "WHERE c.id = %s",
                (complaint_id,),
            )
            complaint = cur.fetchone()
            if not complaint:
                return jsonify(error="Complaint not found"), 404

            # Current staff member (None if not assigned yet)
            cur.execute(
                "SELECT s.id, s.name, asg.assigned_at "
                "FROM assignments asg JOIN users s ON asg.staff_id = s.id "
                "WHERE asg.complaint_id = %s AND asg.is_current = 1",
                (complaint_id,),
            )
            complaint["assigned_to"] = cur.fetchone()

            # Full assignment history, including past staff
            cur.execute(
                "SELECT s.name AS staff, b.name AS assigned_by, "
                "asg.assigned_at, asg.is_current "
                "FROM assignments asg "
                "JOIN users s ON asg.staff_id = s.id "
                "JOIN users b ON asg.assigned_by = b.id "
                "WHERE asg.complaint_id = %s ORDER BY asg.id",
                (complaint_id,),
            )
            complaint["assignment_history"] = cur.fetchall()

            # Status timeline
            cur.execute(
                "SELECT h.status, h.changed_at, u.name AS changed_by "
                "FROM complaint_status_history h "
                "JOIN users u ON h.changed_by = u.id "
                "WHERE h.complaint_id = %s ORDER BY h.changed_at, h.id",
                (complaint_id,),
            )
            complaint["history"] = cur.fetchall()

            # Attachments (complaint photos and resolution proofs)
            cur.execute(
                "SELECT id, file_path, type, uploaded_at "
                "FROM attachments WHERE complaint_id = %s ORDER BY id",
                (complaint_id,),
            )
            complaint["attachments"] = cur.fetchall()
    finally:
        db.close()
    return jsonify(complaint)

@admin_bp.get("/users")
@role_required("admin")
def list_users():
    # Optional filter: /api/admin/users?role=staff
    role = request.args.get("role")

    query = (
        "SELECT u.id, u.name, u.email, u.phone, u.is_active, u.created_at, "
        "r.name AS role FROM users u JOIN roles r ON u.role_id = r.id"
    )
    params = []
    if role:
        query += " WHERE r.name = %s"
        params.append(role)
    query += " ORDER BY u.id"

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        db.close()
    return jsonify(rows)


@admin_bp.post("/users")
@role_required("admin")
def create_user():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip() or None
    password = data.get("password") or ""
    role = (data.get("role") or "staff").strip()

    if not name or not email or not password:
        return jsonify(error="Name, email, and password are required"), 400
    if "@" not in email or "." not in email:
        return jsonify(error="Please provide a valid email address"), 400
    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters long"), 400
    if role not in ("staff", "admin"):
        return jsonify(error="Role must be 'staff' or 'admin'"), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify(error="Email is already registered"), 409

            cur.execute("SELECT id FROM roles WHERE name = %s", (role,))
            role_id = cur.fetchone()["id"]

            cur.execute(
                "INSERT INTO users (name, email, phone, password_hash, role_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (name, email, phone, generate_password_hash(password), role_id),
            )
            user_id = cur.lastrowid
        db.commit()
    finally:
        db.close()
    return jsonify(message="User created successfully", user_id=user_id), 201


@admin_bp.put("/users/<int:user_id>")
@role_required("admin")
def edit_user(user_id):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip() or None

    if not name:
        return jsonify(error="Name is required"), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                return jsonify(error="User not found"), 404
            cur.execute(
                "UPDATE users SET name = %s, phone = %s WHERE id = %s",
                (name, phone, user_id),
            )
        db.commit()
    finally:
        db.close()
    return jsonify(message="User updated successfully")


@admin_bp.put("/users/<int:user_id>/status")
@role_required("admin")
def set_user_status(user_id):
    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")

    if not isinstance(is_active, bool):
        return jsonify(error="is_active must be true or false"), 400
    if user_id == session["user_id"] and not is_active:
        return jsonify(error="You cannot deactivate your own account"), 409

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                return jsonify(error="User not found"), 404
            cur.execute(
                "UPDATE users SET is_active = %s WHERE id = %s",
                (1 if is_active else 0, user_id),
            )
        db.commit()
    finally:
        db.close()
    state = "activated" if is_active else "deactivated"
    return jsonify(message=f"User {state} successfully")

# Lookup tables managed by the admin: table name -> maximum name length.
# Table names come from this dictionary (our code), never from the user.
LOOKUP_TABLES = {"categories": 80, "areas": 100}


def list_lookup(table):
    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(f"SELECT id, name, is_active FROM {table} ORDER BY name")
            rows = cur.fetchall()
    finally:
        db.close()
    return jsonify(rows)


def create_lookup(table):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()

    if not name:
        return jsonify(error="Name is required"), 400
    if len(name) > LOOKUP_TABLES[table]:
        return jsonify(error=f"Name must not exceed {LOOKUP_TABLES[table]} characters"), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(f"SELECT id FROM {table} WHERE name = %s", (name,))
            if cur.fetchone():
                return jsonify(error="This name already exists"), 409
            cur.execute(f"INSERT INTO {table} (name) VALUES (%s)", (name,))
            new_id = cur.lastrowid
        db.commit()
    finally:
        db.close()
    return jsonify(message="Created successfully", id=new_id), 201


def update_lookup(table, item_id):
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    is_active = data.get("is_active")

    if name is None and is_active is None:
        return jsonify(error="Provide a name and/or is_active to update"), 400
    if name is not None:
        name = name.strip()
        if not name:
            return jsonify(error="Name cannot be empty"), 400
        if len(name) > LOOKUP_TABLES[table]:
            return jsonify(error=f"Name must not exceed {LOOKUP_TABLES[table]} characters"), 400
    if is_active is not None and not isinstance(is_active, bool):
        return jsonify(error="is_active must be true or false"), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(f"SELECT id FROM {table} WHERE id = %s", (item_id,))
            if not cur.fetchone():
                return jsonify(error="Item not found"), 404

            if name is not None:
                cur.execute(
                    f"SELECT id FROM {table} WHERE name = %s AND id <> %s", (name, item_id)
                )
                if cur.fetchone():
                    return jsonify(error="This name already exists"), 409
                cur.execute(f"UPDATE {table} SET name = %s WHERE id = %s", (name, item_id))

            if is_active is not None:
                cur.execute(
                    f"UPDATE {table} SET is_active = %s WHERE id = %s",
                    (1 if is_active else 0, item_id),
                )
        db.commit()
    finally:
        db.close()
    return jsonify(message="Updated successfully")


# ---- Categories ----
@admin_bp.get("/categories")
@role_required("admin")
def admin_list_categories():
    return list_lookup("categories")


@admin_bp.post("/categories")
@role_required("admin")
def admin_create_category():
    return create_lookup("categories")


@admin_bp.put("/categories/<int:item_id>")
@role_required("admin")
def admin_update_category(item_id):
    return update_lookup("categories", item_id)


# ---- Areas ----
@admin_bp.get("/areas")
@role_required("admin")
def admin_list_areas():
    return list_lookup("areas")


@admin_bp.post("/areas")
@role_required("admin")
def admin_create_area():
    return create_lookup("areas")


@admin_bp.put("/areas/<int:item_id>")
@role_required("admin")
def admin_update_area(item_id):
    return update_lookup("areas", item_id)

def date_filter(args):
    """Build an optional date condition from ?from= and ?to= (YYYY-MM-DD)."""
    where, params = [], []
    if args.get("from"):
        where.append("DATE(c.created_at) >= %s")
        params.append(args["from"])
    if args.get("to"):
        where.append("DATE(c.created_at) <= %s")
        params.append(args["to"])
    sql = (" WHERE " + " AND ".join(where)) if where else ""
    return sql, params


@admin_bp.get("/reports/summary")
@role_required("admin")
def report_summary():
    where_sql, params = date_filter(request.args)

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT c.status, COUNT(*) AS count FROM complaints c"
                + where_sql + " GROUP BY c.status",
                params,
            )
            rows = cur.fetchall()
    finally:
        db.close()

    # Start every status at 0 so the response always has all four keys
    by_status = {"pending": 0, "assigned": 0, "in_progress": 0, "resolved": 0}
    for row in rows:
        by_status[row["status"]] = row["count"]

    return jsonify(total=sum(by_status.values()), **by_status)


@admin_bp.get("/reports/by-category")
@role_required("admin")
def report_by_category():
    where_sql, params = date_filter(request.args)

    db = get_db()
    try:
        with db.cursor() as cur:
            # LEFT JOIN keeps categories that have zero complaints
            cur.execute(
                "SELECT cat.name AS category, COUNT(c.id) AS count "
                "FROM categories cat LEFT JOIN complaints c ON c.category_id = cat.id"
                + (where_sql.replace(" WHERE ", " AND ", 1) if where_sql else "")
                + " GROUP BY cat.id, cat.name ORDER BY count DESC, cat.name",
                params,
            )
            rows = cur.fetchall()
    finally:
        db.close()
    return jsonify(rows)


@admin_bp.get("/reports/by-area")
@role_required("admin")
def report_by_area():
    where_sql, params = date_filter(request.args)

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT a.name AS area, COUNT(c.id) AS count "
                "FROM areas a LEFT JOIN complaints c ON c.area_id = a.id"
                + (where_sql.replace(" WHERE ", " AND ", 1) if where_sql else "")
                + " GROUP BY a.id, a.name ORDER BY count DESC, a.name",
                params,
            )
            rows = cur.fetchall()
    finally:
        db.close()
    return jsonify(rows)


@admin_bp.get("/reports/range")
@role_required("admin")
def report_range():
    where_sql, params = date_filter(request.args)

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT DATE(c.created_at) AS day, COUNT(*) AS count FROM complaints c"
                + where_sql + " GROUP BY DATE(c.created_at) ORDER BY day",
                params,
            )
            rows = cur.fetchall()
    finally:
        db.close()

    # Dates become plain strings so JSON output is clean
    for row in rows:
        row["day"] = str(row["day"])
    return jsonify(rows)

def csv_safe(value):
    """Neutralise values that Excel could treat as formulas (CSV injection)."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@"):
        return "'" + text
    return text


@admin_bp.get("/reports/export")
@role_required("admin")
def export_complaints_csv():
    args = request.args
    where = []
    params = []

    # Same optional filters as the admin complaints list
    if args.get("status"):
        where.append("c.status = %s")
        params.append(args["status"])
    if args.get("category_id", type=int):
        where.append("c.category_id = %s")
        params.append(args.get("category_id", type=int))
    if args.get("area_id", type=int):
        where.append("c.area_id = %s")
        params.append(args.get("area_id", type=int))
    if args.get("from"):
        where.append("DATE(c.created_at) >= %s")
        params.append(args["from"])
    if args.get("to"):
        where.append("DATE(c.created_at) <= %s")
        params.append(args["to"])
    if args.get("search"):
        where.append("c.title LIKE %s")
        params.append("%" + args["search"] + "%")

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(
                "SELECT c.id, c.title, c.status, c.created_at, "
                "u.name AS citizen, cat.name AS category, a.name AS area, "
                "s.name AS assigned_to "
                "FROM complaints c "
                "JOIN users u ON c.citizen_id = u.id "
                "JOIN categories cat ON c.category_id = cat.id "
                "JOIN areas a ON c.area_id = a.id "
                "LEFT JOIN assignments asg ON asg.complaint_id = c.id AND asg.is_current = 1 "
                "LEFT JOIN users s ON asg.staff_id = s.id"
                + where_sql + " ORDER BY c.created_at DESC, c.id DESC",
                params,
            )
            rows = cur.fetchall()
    finally:
        db.close()

    # Write the CSV into memory
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["ID", "Title", "Status", "Created At", "Citizen",
                     "Category", "Area", "Assigned To"])
    for r in rows:
        writer.writerow([
            r["id"], csv_safe(r["title"]), r["status"], r["created_at"],
            csv_safe(r["citizen"]), r["category"], r["area"],
            csv_safe(r["assigned_to"]),
        ])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=complaints_report.csv"},
    )
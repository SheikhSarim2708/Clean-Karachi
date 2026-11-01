from flask import Blueprint, request, jsonify, session , send_from_directory
from db import get_db
from config import UPLOAD_FOLDER
from utils.auth_utils import role_required
from utils.file_utils import save_image

complaints_bp = Blueprint("complaints", __name__, url_prefix="/api")

@complaints_bp.post("/complaints")
@role_required("citizen")
def submit_complaint():
    data = request.form

    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    address_detail = (data.get("address_detail") or "").strip() or None
    category_id = data.get("category_id", type=int)
    area_id = data.get("area_id", type=int)

    # Input validation
    if not title or not description:
        return jsonify(error="Title and description are required"), 400
    if len(title) > 150:
        return jsonify(error="Title must not exceed 150 characters"), 400
    if category_id is None or area_id is None:
        return jsonify(error="A valid category and area must be selected"), 400

    filename, file_error = save_image(request.files.get("image"))
    if file_error:
        return jsonify(error=file_error), 400
    db = get_db()
    try:
        with db.cursor() as cur:
            # Category and area must exist and be active
            cur.execute("SELECT id FROM categories WHERE id = %s AND is_active = 1", (category_id,))
            if not cur.fetchone():
                return jsonify(error="Selected category is invalid"), 400
            cur.execute("SELECT id FROM areas WHERE id = %s AND is_active = 1", (area_id,))
            if not cur.fetchone():
                return jsonify(error="Selected area is invalid"), 400

            # 1) Insert the complaint
            cur.execute(
                "INSERT INTO complaints "
                "(citizen_id, category_id, area_id, title, description, address_detail) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session["user_id"], category_id, area_id, title, description, address_detail),
            )
            complaint_id = cur.lastrowid

            # 2) Insert the first history row
            cur.execute(
                "INSERT INTO complaint_status_history (complaint_id, status, changed_by) "
                "VALUES (%s, 'pending', %s)",
                (complaint_id, session["user_id"]),
            )

            # 3) Insert the attachment row (only if an image was uploaded)
            if filename:
                cur.execute(
                    "INSERT INTO attachments (complaint_id, file_path, type, uploaded_by) "
                    "VALUES (%s, %s, 'complaint', %s)",
                    (complaint_id, filename, session["user_id"]),
                )
            
        db.commit()
    except Exception:
        db.rollback()
        return jsonify(error="Could not submit the complaint. Please try again"), 500
    finally:
        db.close()

    return jsonify(message="Complaint submitted successfully", complaint_id=complaint_id), 201

@complaints_bp.get("/complaints")
@role_required("citizen")
def list_my_complaints():
    # Optional filter: /api/complaints?status=pending
    status = request.args.get("status")

    query = (
        "SELECT c.id, c.title, c.status, c.created_at, "
        "cat.name AS category, a.name AS area "
        "FROM complaints c "
        "JOIN categories cat ON c.category_id = cat.id "
        "JOIN areas a ON c.area_id = a.id "
        "WHERE c.citizen_id = %s"
    )
    params = [session["user_id"]]

    if status:
        query += " AND c.status = %s"
        params.append(status)

    query += " ORDER BY c.created_at DESC, c.id DESC"

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        db.close()
    return jsonify(rows)


@complaints_bp.get("/complaints/<int:complaint_id>")
@role_required("citizen")
def get_my_complaint(complaint_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            # Ownership check: the complaint must belong to the logged-in citizen
            cur.execute(
                "SELECT c.id, c.title, c.description, c.address_detail, c.status, "
                "c.created_at, c.updated_at, cat.name AS category, a.name AS area "
                "FROM complaints c "
                "JOIN categories cat ON c.category_id = cat.id "
                "JOIN areas a ON c.area_id = a.id "
                "WHERE c.id = %s AND c.citizen_id = %s",
                (complaint_id, session["user_id"]),
            )
            complaint = cur.fetchone()
            if not complaint:
                return jsonify(error="Complaint not found"), 404

            # Status timeline
            cur.execute(
                "SELECT h.status, h.changed_at, u.name AS changed_by "
                "FROM complaint_status_history h "
                "JOIN users u ON h.changed_by = u.id "
                "WHERE h.complaint_id = %s ORDER BY h.changed_at, h.id",
                (complaint_id,),
            )
            complaint["history"] = cur.fetchall()
                        # Attachments (complaint photos and, later, resolution proofs)
            cur.execute(
                "SELECT id, file_path, type, uploaded_at "
                "FROM attachments WHERE complaint_id = %s ORDER BY id",
                (complaint_id,),
            )
            complaint["attachments"] = cur.fetchall()
    finally:
        db.close()
    return jsonify(complaint)

@complaints_bp.get("/uploads/<filename>")
@role_required("citizen", "staff", "admin")
def serve_upload(filename):
    db = get_db()
    try:
        with db.cursor() as cur:
            # Find which complaint this file belongs to
            cur.execute(
                "SELECT a.complaint_id, c.citizen_id "
                "FROM attachments a JOIN complaints c ON a.complaint_id = c.id "
                "WHERE a.file_path = %s",
                (filename,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify(error="File not found"), 404

            role = session["role"]
            user_id = session["user_id"]

            if role == "citizen" and row["citizen_id"] != user_id:
                return jsonify(error="File not found"), 404

            if role == "staff":
                cur.execute(
                    "SELECT id FROM assignments "
                    "WHERE complaint_id = %s AND staff_id = %s AND is_current = 1",
                    (row["complaint_id"], user_id),
                )
                if not cur.fetchone():
                    return jsonify(error="File not found"), 404
    finally:
        db.close()

    return send_from_directory(UPLOAD_FOLDER, filename)
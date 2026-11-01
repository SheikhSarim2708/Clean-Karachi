from flask import Blueprint, request, jsonify, session
from db import get_db
from utils.file_utils import save_image
from utils.auth_utils import role_required

staff_bp = Blueprint("staff", __name__, url_prefix="/api/staff")


@staff_bp.get("/complaints")
@role_required("staff")
def list_assigned_complaints():
    # Optional filter: /api/staff/complaints?status=in_progress
    status = request.args.get("status")

    query = (
        "SELECT c.id, c.title, c.status, c.created_at, "
        "cat.name AS category, a.name AS area, asg.assigned_at "
        "FROM complaints c "
        "JOIN assignments asg ON asg.complaint_id = c.id "
        "JOIN categories cat ON c.category_id = cat.id "
        "JOIN areas a ON c.area_id = a.id "
        "WHERE asg.staff_id = %s AND asg.is_current = 1"
    )
    params = [session["user_id"]]

    if status:
        query += " AND c.status = %s"
        params.append(status)

    query += " ORDER BY asg.assigned_at DESC, c.id DESC"

    db = get_db()
    try:
        with db.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    finally:
        db.close()
    return jsonify(rows)


@staff_bp.get("/complaints/<int:complaint_id>")
@role_required("staff")
def get_assigned_complaint(complaint_id):
    db = get_db()
    try:
        with db.cursor() as cur:
            # Ownership check: complaint must currently be assigned to this staff member
            cur.execute(
                "SELECT c.id, c.title, c.description, c.address_detail, c.status, "
                "c.created_at, c.updated_at, cat.name AS category, a.name AS area, "
                "u.name AS citizen "
                "FROM complaints c "
                "JOIN assignments asg ON asg.complaint_id = c.id "
                "JOIN categories cat ON c.category_id = cat.id "
                "JOIN areas a ON c.area_id = a.id "
                "JOIN users u ON c.citizen_id = u.id "
                "WHERE c.id = %s AND asg.staff_id = %s AND asg.is_current = 1",
                (complaint_id, session["user_id"]),
            )
            complaint = cur.fetchone()
            if not complaint:
                return jsonify(error="Complaint not found"), 404

            cur.execute(
                "SELECT h.status, h.changed_at, u.name AS changed_by "
                "FROM complaint_status_history h "
                "JOIN users u ON h.changed_by = u.id "
                "WHERE h.complaint_id = %s ORDER BY h.changed_at, h.id",
                (complaint_id,),
            )
            complaint["history"] = cur.fetchall()

            cur.execute(
                "SELECT id, file_path, type, uploaded_at "
                "FROM attachments WHERE complaint_id = %s ORDER BY id",
                (complaint_id,),
            )
            complaint["attachments"] = cur.fetchall()
    finally:
        db.close()
    return jsonify(complaint)

# Allowed status transitions for staff: current status -> next status
NEXT_STATUS = {
    "assigned": "in_progress",
    "in_progress": "resolved",
}


@staff_bp.put("/complaints/<int:complaint_id>/status")
@role_required("staff")
def update_status(complaint_id):
    data = request.get_json(silent=True) or {}
    new_status = (data.get("status") or "").strip()

    if new_status not in ("in_progress", "resolved"):
        return jsonify(error="Status must be 'in_progress' or 'resolved'"), 400

    staff_id = session["user_id"]

    db = get_db()
    try:
        with db.cursor() as cur:
            # Ownership check: complaint must currently be assigned to this staff member
            cur.execute(
                "SELECT c.id, c.status FROM complaints c "
                "JOIN assignments asg ON asg.complaint_id = c.id "
                "WHERE c.id = %s AND asg.staff_id = %s AND asg.is_current = 1",
                (complaint_id, staff_id),
            )
            complaint = cur.fetchone()
            if not complaint:
                return jsonify(error="Complaint not found"), 404

            # Enforce the status order
            if NEXT_STATUS.get(complaint["status"]) != new_status:
                return jsonify(
                    error=f"Cannot change status from '{complaint['status']}' to '{new_status}'"
                ), 409

            cur.execute(
                "UPDATE complaints SET status = %s WHERE id = %s",
                (new_status, complaint_id),
            )
            cur.execute(
                "INSERT INTO complaint_status_history (complaint_id, status, changed_by) "
                "VALUES (%s, %s, %s)",
                (complaint_id, new_status, staff_id),
            )
        db.commit()
    except Exception:
        db.rollback()
        return jsonify(error="Could not update the status. Please try again"), 500
    finally:
        db.close()

    return jsonify(message="Status updated successfully", status=new_status)

@staff_bp.post("/complaints/<int:complaint_id>/proof")
@role_required("staff")
def upload_proof(complaint_id):
    staff_id = session["user_id"]

    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify(error="A proof image is required"), 400

    db = get_db()
    try:
        with db.cursor() as cur:
            # Ownership check: complaint must currently be assigned to this staff member
            cur.execute(
                "SELECT c.id, c.status FROM complaints c "
                "JOIN assignments asg ON asg.complaint_id = c.id "
                "WHERE c.id = %s AND asg.staff_id = %s AND asg.is_current = 1",
                (complaint_id, staff_id),
            )
            complaint = cur.fetchone()
            if not complaint:
                return jsonify(error="Complaint not found"), 404

            if complaint["status"] == "assigned":
                return jsonify(error="Start the work before uploading proof"), 409

            # Validate and save the image only after the checks above pass
            filename, file_error = save_image(file)
            if file_error:
                return jsonify(error=file_error), 400

            cur.execute(
                "INSERT INTO attachments (complaint_id, file_path, type, uploaded_by) "
                "VALUES (%s, %s, 'resolution', %s)",
                (complaint_id, filename, staff_id),
            )
        db.commit()
    except Exception:
        db.rollback()
        return jsonify(error="Could not upload the proof. Please try again"), 500
    finally:
        db.close()

    return jsonify(message="Proof uploaded successfully", file=filename), 201
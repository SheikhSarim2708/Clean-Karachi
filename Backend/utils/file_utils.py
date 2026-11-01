import os
import uuid
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS


def save_image(file):
    """Validate and save an uploaded image. Return (filename, error)."""
    if not file or not file.filename:
        return None, None  # no file supplied (optional)

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return None, "Only JPG, JPEG, and PNG images are allowed"

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return filename, None
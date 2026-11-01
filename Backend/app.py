from flask import Flask, jsonify
from config import SECRET_KEY, MAX_UPLOAD_SIZE
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.staff import staff_bp
from routes.lookup import lookup_bp
from routes.complaints import complaints_bp

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(lookup_bp)
app.register_blueprint(complaints_bp)


@app.errorhandler(404)
def handle_not_found(e):
    return jsonify(error="The requested resource was not found"), 404


@app.errorhandler(405)
def handle_method_not_allowed(e):
    return jsonify(error="This method is not allowed for the requested URL"), 405


@app.errorhandler(413)
def handle_file_too_large(e):
    return jsonify(error="The uploaded file is too large (maximum 5 MB)"), 413


@app.errorhandler(500)
def handle_server_error(e):
    return jsonify(error="An internal server error occurred"), 500


@app.get("/")
def home():
    return jsonify(message="CleanKarachi backend is running")


if __name__ == "__main__":
    app.run(debug=True)
    
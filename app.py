import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.getenv("DATABASE_PATH", "/tmp/drainwatch.db"))
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_PATH", "/tmp/uploads"))
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
STATUSES = ["Reported", "Verified", "Assigned", "In Progress", "Resolved"]

# Prototype ward ranges. Replace this function with GIS boundary data later.
WARD_RANGES = [
    {"name": "Ward 27", "min_lat": 10.00, "max_lat": 13.50, "min_lng": 76.00, "max_lng": 78.00},
    {"name": "Ward 14", "min_lat": 8.00, "max_lat": 10.00, "min_lng": 76.00, "max_lng": 78.00},
    {"name": "Ward 8", "min_lat": 13.50, "max_lat": 15.00, "min_lng": 74.00, "max_lng": 78.00},
]

load_dotenv(BASE_DIR / ".env")
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(16)),
    UPLOAD_FOLDER=str(UPLOAD_FOLDER),
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
)
UPLOAD_FOLDER.mkdir(exist_ok=True)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute(
        """CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE NOT NULL,
            photo_path TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            address TEXT DEFAULT '',
            ward TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Reported',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            escalated INTEGER NOT NULL DEFAULT 0
        )"""
    )
    db.commit()
    db.close()


def detect_ward(latitude, longitude):
    for ward in WARD_RANGES:
        if ward["min_lat"] <= latitude < ward["max_lat"] and ward["min_lng"] <= longitude < ward["max_lng"]:
            return ward["name"]
    return "Prototype Review Zone"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def make_ticket_id(report_id):
    return f"DRN-{datetime.now().year}-{report_id:04d}"


def refresh_escalations():
    db = get_db()
    cutoff = (datetime.now() - timedelta(hours=48)).isoformat(timespec="seconds")
    db.execute(
        "UPDATE reports SET escalated = 1 WHERE status != 'Resolved' AND created_at < ?",
        (cutoff,),
    )
    db.commit()


@app.context_processor
def inject_globals():
    return {"statuses": STATUSES}


@app.route("/")
def index():
    try:
        refresh_escalations()
        db = get_db()
        totals = db.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN status != 'Resolved' THEN 1 ELSE 0 END), 0) AS open_count FROM reports"
        ).fetchone()
    except sqlite3.Error:
        # Keep the public homepage available if an old or incomplete local DB exists.
        totals = {"total": 0, "open_count": 0}
    return render_template("index.html", totals=totals)


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "GET":
        return render_template("report.html")

    # --- Begin robust report handling ---
    try:
        # Validate and parse location
        try:
            latitude = float(request.form.get("latitude", ""))
            longitude = float(request.form.get("longitude", ""))
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError
        except (TypeError, ValueError):
            flash("Please select a valid location on the map.", "danger")
            return render_template("report.html"), 400

        # Validate image
        photo = request.files.get("photo")
        if not photo or not photo.filename or not allowed_file(photo.filename):
            flash("Upload a JPG, JPEG, or PNG photo of the blockage.", "danger")
            return render_template("report.html"), 400

        # Validate description
        description = request.form.get("description", "").strip()
        if not description:
            flash("Add a short description of the blockage.", "danger")
            return render_template("report.html"), 400

        # Optional fields
        address = request.form.get("address", "").strip()

        # Ensure upload folder exists (defensive)
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

        # Secure and store the uploaded file
        filename = f"{secrets.token_hex(8)}_{secure_filename(photo.filename)}"
        photo_path = UPLOAD_FOLDER / filename
        photo.save(photo_path)

        # Insert into DB (temporary ticket_id, will be updated)
        now = datetime.now().isoformat(timespec="seconds")
        db = get_db()
        cursor = db.execute(
            """INSERT INTO reports
            (ticket_id, photo_path, latitude, longitude, address, ward, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Reported', ?, ?)""",
            ("PENDING", filename, latitude, longitude, address,
             detect_ward(latitude, longitude), description, now, now),
        )
        report_id = cursor.lastrowid
        ticket_id = make_ticket_id(report_id)
        db.execute("UPDATE reports SET ticket_id = ? WHERE id = ?", (ticket_id, report_id))
        db.commit()
        flash(f"{ticket_id} submitted successfully!", "success")
        return redirect(url_for("ticket", ticket_id=ticket_id))
    except Exception as e:
        # Log the exception for debugging (stdout is captured by Vercel)
        app.logger.error(f"Report submission failed: {e}", exc_info=True)
        flash("An unexpected error occurred while submitting the report. Please try again.", "danger")
        return render_template("report.html"), 500
    # --- End robust report handling ---


@app.route("/ticket/<ticket_id>")
def ticket(ticket_id):
    refresh_escalations()
    report_row = get_db().execute("SELECT * FROM reports WHERE ticket_id = ?", (ticket_id.upper(),)).fetchone()
    if report_row is None:
        flash("That ticket ID was not found.", "warning")
        return redirect(url_for("track"))
    return render_template("ticket.html", report=report_row)


@app.route("/track", methods=["GET", "POST"])
def track():
    report_row = None
    query = request.form.get("ticket_id", "") if request.method == "POST" else request.args.get("ticket_id", "")
    if query:
        refresh_escalations()
        report_row = get_db().execute("SELECT * FROM reports WHERE ticket_id = ?", (query.strip().upper(),)).fetchone()
        if report_row is None:
            flash("No report found for that ticket ID.", "warning")
    return render_template("track.html", report=report_row, query=query)


@app.route("/reports")
def reports():
    refresh_escalations()
    rows = get_db().execute("SELECT * FROM reports WHERE status != 'Resolved' ORDER BY created_at DESC").fetchall()
    return render_template("reports.html", reports=rows, public_reports=[dict(row) for row in rows])


@app.route("/admin")
def admin():
    refresh_escalations()
    rows = get_db().execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
    return render_template("admin.html", reports=rows)


@app.post("/admin/<ticket_id>/status")
def update_status(ticket_id):
    new_status = request.form.get("status")
    if new_status not in STATUSES:
        flash("Invalid status selected.", "danger")
        return redirect(url_for("admin"))
    db = get_db()
    db.execute(
        "UPDATE reports SET status = ?, updated_at = ? WHERE ticket_id = ?",
        (new_status, datetime.now().isoformat(timespec="seconds"), ticket_id),
    )
    db.commit()
    flash(f"{ticket_id} updated to {new_status}.", "success")
    return redirect(url_for("admin"))


@app.post("/admin/<ticket_id>/escalate")
def escalate(ticket_id):
    db = get_db()
    db.execute("UPDATE reports SET escalated = 1, updated_at = ? WHERE ticket_id = ?", (datetime.now().isoformat(timespec="seconds"), ticket_id))
    db.commit()
    flash(f"Escalation simulated for {ticket_id}.", "warning")
    return redirect(url_for("admin"))


@app.get("/api/wards")
def wards():
    try:
        latitude = float(request.args["lat"])
        longitude = float(request.args["lng"])
    except (KeyError, ValueError):
        return jsonify({"error": "Invalid coordinates"}), 400
    return jsonify({"ward": detect_ward(latitude, longitude)})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.errorhandler(413)
def too_large(_error):
    flash("The photo is too large. Please choose an image under 8 MB.", "danger")
    return redirect(url_for("report"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)

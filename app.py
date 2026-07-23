from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from pathlib import Path
from datetime import date
from functools import wraps

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "autocare.db"

app = Flask(__name__)
app.secret_key = "change-this-secret-key-for-production"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            make TEXT NOT NULL,
            model TEXT NOT NULL,
            year INTEGER NOT NULL,
            mileage INTEGER NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            service_type TEXT NOT NULL,
            service_date TEXT NOT NULL,
            mileage INTEGER NOT NULL,
            cost REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            service_type TEXT NOT NULL,
            due_date TEXT,
            due_mileage INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def reminder_status(reminder, current_mileage):
    today = date.today().isoformat()
    date_due = bool(reminder["due_date"] and reminder["due_date"] <= today)
    mileage_due = reminder["due_mileage"] is not None and current_mileage >= reminder["due_mileage"]
    return "Due" if date_due or mileage_due else "Upcoming"


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


def get_user_vehicle(vehicle_id):
    conn = get_db_connection()
    vehicle = conn.execute(
        "SELECT * FROM vehicles WHERE id = ? AND user_id = ?",
        (vehicle_id, session["user_id"]),
    ).fetchone()
    conn.close()
    if vehicle is None:
        abort(404)
    return vehicle


def get_user_maintenance_record(record_id):
    conn = get_db_connection()
    record = conn.execute(
        """
        SELECT m.*
        FROM maintenance_records m
        JOIN vehicles v ON v.id = m.vehicle_id
        WHERE m.id = ? AND v.user_id = ?
        """,
        (record_id, session["user_id"]),
    ).fetchone()
    conn.close()
    if record is None:
        abort(404)
    return record


@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please fill out all fields.", "error")
            return render_template("register.html")

        conn = get_db_connection()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        conn.commit()
        user = conn.execute("SELECT id, name FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash("Account created successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    vehicles = conn.execute(
        """
        SELECT v.*,
               COUNT(m.id) AS maintenance_count,
               COALESCE(SUM(m.cost), 0) AS maintenance_cost
        FROM vehicles v
        LEFT JOIN maintenance_records m ON m.vehicle_id = v.id
        WHERE v.user_id = ?
        GROUP BY v.id
        ORDER BY v.created_at DESC
        """,
        (session["user_id"],),
    ).fetchall()

    total_mileage = sum(v["mileage"] for v in vehicles)
    total_maintenance = sum(float(v["maintenance_cost"] or 0) for v in vehicles)
    total_records = sum(int(v["maintenance_count"] or 0) for v in vehicles)

    current_year = str(date.today().year)
    yearly_cost = conn.execute(
        """
        SELECT COALESCE(SUM(m.cost), 0) AS total
        FROM maintenance_records m
        JOIN vehicles v ON v.id = m.vehicle_id
        WHERE v.user_id = ? AND substr(m.service_date, 1, 4) = ?
        """,
        (session["user_id"], current_year),
    ).fetchone()["total"]

    reminder_rows = conn.execute(
        """
        SELECT r.*, v.make, v.model, v.year, v.mileage AS current_mileage
        FROM reminders r
        JOIN vehicles v ON v.id = r.vehicle_id
        WHERE v.user_id = ?
        ORDER BY CASE WHEN r.due_date IS NULL OR r.due_date = '' THEN 1 ELSE 0 END,
                 r.due_date ASC, r.id DESC
        """,
        (session["user_id"],),
    ).fetchall()

    reminders = []
    due_count = 0
    upcoming_count = 0
    for row in reminder_rows:
        item = dict(row)
        item["status"] = reminder_status(row, row["current_mileage"])
        if item["status"] == "Due":
            due_count += 1
        else:
            upcoming_count += 1
        reminders.append(item)

    reminders.sort(key=lambda r: (0 if r["status"] == "Due" else 1, r.get("due_date") or "9999-12-31"))
    conn.close()

    return render_template(
        "dashboard.html",
        vehicles=vehicles,
        total_mileage=total_mileage,
        total_maintenance=total_maintenance,
        total_records=total_records,
        yearly_cost=float(yearly_cost or 0),
        reminders=reminders,
        due_count=due_count,
        upcoming_count=upcoming_count,
        current_year=current_year,
    )


@app.route("/vehicles/add", methods=["POST"])
@login_required
def add_vehicle():
    make = request.form.get("make", "").strip()
    model = request.form.get("model", "").strip()
    year = request.form.get("year", "").strip()
    mileage = request.form.get("mileage", "").strip()
    notes = request.form.get("notes", "").strip()

    if not make or not model or not year or not mileage:
        flash("Make, model, year, and mileage are required.", "error")
        return redirect(url_for("dashboard"))

    try:
        year_int = int(year)
        mileage_int = int(mileage)
        if mileage_int < 0 or year_int < 1950 or year_int > 2035:
            raise ValueError
    except ValueError:
        flash("Year and mileage must be valid numbers.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO vehicles (user_id, make, model, year, mileage, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (session["user_id"], make, model, year_int, mileage_int, notes),
    )
    conn.commit()
    conn.close()
    flash("Vehicle added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/vehicles/<int:vehicle_id>/edit", methods=["GET", "POST"])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = get_user_vehicle(vehicle_id)

    if request.method == "POST":
        make = request.form.get("make", "").strip()
        model = request.form.get("model", "").strip()
        year = request.form.get("year", "").strip()
        mileage = request.form.get("mileage", "").strip()
        notes = request.form.get("notes", "").strip()

        if not make or not model or not year or not mileage:
            flash("Make, model, year, and mileage are required.", "error")
            return render_template("edit_vehicle.html", vehicle=vehicle)

        try:
            year_int = int(year)
            mileage_int = int(mileage)
            if mileage_int < 0 or year_int < 1950 or year_int > 2035:
                raise ValueError
        except ValueError:
            flash("Year and mileage must be valid numbers.", "error")
            return render_template("edit_vehicle.html", vehicle=vehicle)

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE vehicles
            SET make = ?, model = ?, year = ?, mileage = ?, notes = ?
            WHERE id = ? AND user_id = ?
            """,
            (make, model, year_int, mileage_int, notes, vehicle_id, session["user_id"]),
        )
        conn.commit()
        conn.close()
        flash("Vehicle updated successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("edit_vehicle.html", vehicle=vehicle)


@app.route("/vehicles/<int:vehicle_id>/delete", methods=["POST"])
@login_required
def delete_vehicle(vehicle_id):
    get_user_vehicle(vehicle_id)
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM vehicles WHERE id = ? AND user_id = ?",
        (vehicle_id, session["user_id"]),
    )
    conn.commit()
    conn.close()
    flash("Vehicle and its related records were deleted successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/vehicles/<int:vehicle_id>")
@login_required
def vehicle_detail(vehicle_id):
    vehicle = get_user_vehicle(vehicle_id)
    service_filter = request.args.get("service_type", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    sql = "SELECT * FROM maintenance_records WHERE vehicle_id = ?"
    params = [vehicle_id]
    if service_filter:
        sql += " AND service_type = ?"
        params.append(service_filter)
    if date_from:
        sql += " AND service_date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND service_date <= ?"
        params.append(date_to)
    sql += " ORDER BY service_date DESC, id DESC"

    conn = get_db_connection()
    records = conn.execute(sql, params).fetchall()

    total_cost = conn.execute(
        "SELECT COALESCE(SUM(cost), 0) AS total FROM maintenance_records WHERE vehicle_id = ?",
        (vehicle_id,),
    ).fetchone()["total"]
    total_records = conn.execute(
        "SELECT COUNT(*) AS count FROM maintenance_records WHERE vehicle_id = ?",
        (vehicle_id,),
    ).fetchone()["count"]

    reminder_rows = conn.execute(
        "SELECT * FROM reminders WHERE vehicle_id = ? ORDER BY due_date ASC, id DESC",
        (vehicle_id,),
    ).fetchall()
    reminders = []
    for row in reminder_rows:
        item = dict(row)
        item["status"] = reminder_status(row, vehicle["mileage"])
        reminders.append(item)
    reminders.sort(key=lambda r: (0 if r["status"] == "Due" else 1, r.get("due_date") or "9999-12-31"))
    conn.close()

    return render_template(
        "vehicle_detail.html",
        vehicle=vehicle,
        records=records,
        total_cost=float(total_cost or 0),
        total_records=total_records,
        reminders=reminders,
        service_filter=service_filter,
        date_from=date_from,
        date_to=date_to,
    )


@app.route("/vehicles/<int:vehicle_id>/maintenance/add", methods=["POST"])
@login_required
def add_maintenance(vehicle_id):
    vehicle = get_user_vehicle(vehicle_id)
    service_type = request.form.get("service_type", "").strip()
    service_date = request.form.get("service_date", "").strip()
    mileage = request.form.get("mileage", "").strip()
    cost = request.form.get("cost", "0").strip() or "0"
    notes = request.form.get("notes", "").strip()

    if not service_type or not service_date or not mileage:
        flash("Service type, service date, and mileage are required.", "error")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    try:
        mileage_int = int(mileage)
        cost_float = float(cost)
        if mileage_int < 0 or cost_float < 0:
            raise ValueError
    except ValueError:
        flash("Mileage and cost must be valid non-negative numbers.", "error")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO maintenance_records
            (vehicle_id, service_type, service_date, mileage, cost, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (vehicle_id, service_type, service_date, mileage_int, cost_float, notes),
    )
    if mileage_int > vehicle["mileage"]:
        conn.execute("UPDATE vehicles SET mileage = ? WHERE id = ?", (mileage_int, vehicle_id))
    conn.commit()
    conn.close()

    flash("Maintenance record added successfully.", "success")
    return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))


@app.route("/maintenance/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_maintenance(record_id):
    record = get_user_maintenance_record(record_id)
    vehicle = get_user_vehicle(record["vehicle_id"])

    if request.method == "POST":
        service_type = request.form.get("service_type", "").strip()
        service_date = request.form.get("service_date", "").strip()
        mileage = request.form.get("mileage", "").strip()
        cost = request.form.get("cost", "0").strip() or "0"
        notes = request.form.get("notes", "").strip()

        if not service_type or not service_date or not mileage:
            flash("Service type, service date, and mileage are required.", "error")
            return render_template("edit_maintenance.html", vehicle=vehicle, record=record)

        try:
            mileage_int = int(mileage)
            cost_float = float(cost)
            if mileage_int < 0 or cost_float < 0:
                raise ValueError
        except ValueError:
            flash("Mileage and cost must be valid non-negative numbers.", "error")
            return render_template("edit_maintenance.html", vehicle=vehicle, record=record)

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE maintenance_records
            SET service_type = ?, service_date = ?, mileage = ?, cost = ?, notes = ?
            WHERE id = ?
            """,
            (service_type, service_date, mileage_int, cost_float, notes, record_id),
        )
        if mileage_int > vehicle["mileage"]:
            conn.execute("UPDATE vehicles SET mileage = ? WHERE id = ?", (mileage_int, vehicle["id"]))
        conn.commit()
        conn.close()

        flash("Maintenance record updated successfully.", "success")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle["id"]))

    return render_template("edit_maintenance.html", vehicle=vehicle, record=record)


@app.route("/maintenance/<int:record_id>/delete", methods=["POST"])
@login_required
def delete_maintenance(record_id):
    record = get_user_maintenance_record(record_id)
    vehicle_id = record["vehicle_id"]

    conn = get_db_connection()
    conn.execute("DELETE FROM maintenance_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

    flash("Maintenance record deleted successfully.", "success")
    return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))


@app.route("/vehicles/<int:vehicle_id>/reminders/add", methods=["POST"])
@login_required
def add_reminder(vehicle_id):
    vehicle = get_user_vehicle(vehicle_id)
    service_type = request.form.get("service_type", "").strip()
    due_date = request.form.get("due_date", "").strip() or None
    due_mileage = request.form.get("due_mileage", "").strip()
    notes = request.form.get("notes", "").strip()

    if not service_type or (not due_date and not due_mileage):
        flash("Choose a service and enter a due date or due mileage.", "error")
        return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    mileage_value = None
    if due_mileage:
        try:
            mileage_value = int(due_mileage)
            if mileage_value < 0:
                raise ValueError
        except ValueError:
            flash("Due mileage must be a valid non-negative number.", "error")
            return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))

    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO reminders (vehicle_id, service_type, due_date, due_mileage, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (vehicle["id"], service_type, due_date, mileage_value, notes),
    )
    conn.commit()
    conn.close()
    flash("Maintenance reminder added successfully.", "success")
    return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))


@app.route("/reminders/<int:reminder_id>/delete", methods=["POST"])
@login_required
def delete_reminder(reminder_id):
    conn = get_db_connection()
    reminder = conn.execute(
        """
        SELECT r.* FROM reminders r
        JOIN vehicles v ON v.id = r.vehicle_id
        WHERE r.id = ? AND v.user_id = ?
        """,
        (reminder_id, session["user_id"]),
    ).fetchone()
    if reminder is None:
        conn.close()
        abort(404)
    vehicle_id = reminder["vehicle_id"]
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
    flash("Reminder deleted successfully.", "success")
    return redirect(url_for("vehicle_detail", vehicle_id=vehicle_id))


@app.route("/api/vehicles")
@login_required
def api_vehicles():
    conn = get_db_connection()
    vehicles = conn.execute(
        "SELECT id, make, model, year, mileage, notes, created_at FROM vehicles WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    conn.close()
    return jsonify([dict(vehicle) for vehicle in vehicles])


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

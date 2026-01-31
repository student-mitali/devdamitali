from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "phase1-secret-key"

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect("issues.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # issues table
    c.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            issue TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)
    
    # admins table
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    # default admin
    c.execute("INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)", ("admin", "admin123"))
    conn.commit()
    conn.close()

init_db()

# ---------- USER PAGE ----------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        room = request.form["room"].strip()
        category = request.form["category"]
        priority = request.form["priority"]
        issue = request.form["issue"].strip()[:200]  # max 200 chars
        time = datetime.now().strftime("%d %b %Y, %I:%M %p")

        conn = get_db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO issues (room, category, priority, issue, time, status) VALUES (?, ?, ?, ?, ?, ?)",
            (room, category, priority, issue, time, "Pending")
        )
        conn.commit()
        conn.close()

        flash("✅ Issue submitted successfully! Our team will look into it.", "success")
        return redirect(url_for("index"))

    return render_template("index.html")

# ---------- ADMIN LOGIN ----------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM admins WHERE username=? AND password=?", (username, password))
        admin = c.fetchone()
        conn.close()

        if admin:
            session["admin"] = True
            return redirect(url_for("admin"))
        else:
            error = "Invalid credentials"

    return render_template("admin_login.html", error=error)

# ---------- ADMIN DASHBOARD ----------
@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM issues ORDER BY id DESC")
    issues = c.fetchall()

    total = c.execute("SELECT COUNT(*) FROM issues").fetchone()[0]
    pending = c.execute("SELECT COUNT(*) FROM issues WHERE status='Pending'").fetchone()[0]
    in_progress = c.execute("SELECT COUNT(*) FROM issues WHERE status='In-Progress'").fetchone()[0]
    resolved = c.execute("SELECT COUNT(*) FROM issues WHERE status='Resolved'").fetchone()[0]
    conn.close()

    return render_template(
        "admin.html",
        issues=issues,
        total=total,
        pending=pending,
        in_progress=in_progress,
        resolved=resolved
    )

# ---------- UPDATE STATUS ----------
ALLOWED_STATUS = ["Pending", "In-Progress", "Resolved"]

@app.route("/update/<int:id>/<status>", methods=["POST"])
def update(id, status):
    if not session.get("admin") or status not in ALLOWED_STATUS:
        return redirect(url_for("admin_login"))

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE issues SET status=? WHERE id=?", (status, id))
    conn.commit()
    conn.close()

    print(f"[{datetime.now()}] Issue {id} set to {status}")
    return redirect(url_for("admin"))

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(debug=True)

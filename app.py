import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CATEGORIES = [
    "Electrical Issues", "Water & Plumbing", "Internet & Computer Lab",
    "Classrooms & Infrastructure", "Cleanliness & Waste", "Transport & Parking",
    "Safety & Security", "Furniture & Equipment", "Library", "Canteen",
    "Sports Facilities", "Other Issues"
]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]
STATUSES = ["Submitted", "Under Review", "Assigned", "In Progress", "Resolved", "Rejected"]

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "fixmycampus")
    )

def query_db(sql, params=(), one=False, commit=False):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return cur.lastrowid
        return cur.fetchone() if one else cur.fetchall()
    finally:
        cur.close()
        conn.close()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.context_processor
def inject_globals():
    return {"categories": CATEGORIES, "statuses": STATUSES, "current_year": datetime.now().year}

@app.route("/")
def index():
    stats = {"total": 0, "resolved": 0, "pending": 0}
    try:
        row = query_db("""SELECT COUNT(*) total,
            SUM(status='Resolved') resolved,
            SUM(status NOT IN ('Resolved','Rejected')) pending
            FROM complaints""", one=True)
        stats = {k: int(row[k] or 0) for k in stats}
        latest = query_db("""SELECT c.id,c.title,c.category,c.status,c.priority,c.created_at,
            u.name reporter FROM complaints c JOIN users u ON u.id=c.user_id
            ORDER BY c.created_at DESC LIMIT 5""")
    except Error:
        latest = []
    return render_template("index.html", stats=stats, latest=latest)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department = request.form.get("department", "").strip()
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")
        if not all([name, email, department, password]):
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("register.html")
        try:
            query_db("""INSERT INTO users(name,email,password_hash,department,student_id,role)
                        VALUES(%s,%s,%s,%s,%s,'student')""",
                     (name, email, generate_password_hash(password), department, student_id or None), commit=True)
            flash("Account created. You can now sign in.", "success")
            return redirect(url_for("login"))
        except Error as e:
            if getattr(e, "errno", None) == 1062:
                flash("That email address is already registered.", "danger")
            else:
                app.logger.exception("Registration failed")
                flash("Could not create account. Check your database setup.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        try:
            user = query_db("SELECT * FROM users WHERE email=%s", (email,), one=True)
        except Error:
            user = None
            flash("Database connection failed. Check your .env settings.", "danger")
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], name=user["name"], role=user["role"], email=user["email"])
            flash("Welcome back, " + user["name"] + "!", "success")
            return redirect(url_for("dashboard"))
        if user is not None:
            flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    if session["role"] == "admin":
        complaints = query_db("""SELECT c.*,u.name reporter,u.department FROM complaints c
            JOIN users u ON u.id=c.user_id ORDER BY c.created_at DESC""")
        stats_row = query_db("""SELECT COUNT(*) total,
            SUM(status='Submitted') submitted,
            SUM(status IN ('Under Review','Assigned','In Progress')) active,
            SUM(status='Resolved') resolved FROM complaints""", one=True)
        stats = {k: int(v or 0) for k, v in stats_row.items()}
    elif session["role"] == "staff":
        complaints = query_db("""SELECT c.*,u.name reporter,u.department FROM complaints c
            JOIN users u ON u.id=c.user_id WHERE c.assigned_to=%s OR c.assigned_to IS NULL
            ORDER BY c.created_at DESC""", (session["user_id"],))
        stats = {"total": len(complaints), "submitted": 0, "active": 0, "resolved": 0}
    else:
        complaints = query_db("""SELECT * FROM complaints WHERE user_id=%s ORDER BY created_at DESC""",
                              (session["user_id"],))
        stats_row = query_db("""SELECT COUNT(*) total,SUM(status='Resolved') resolved,
            SUM(status NOT IN ('Resolved','Rejected')) active FROM complaints WHERE user_id=%s""",
            (session["user_id"],), one=True)
        stats = {k: int(v or 0) for k, v in stats_row.items()}
    return render_template("dashboard.html", complaints=complaints, stats=stats)

@app.route("/complaints/new", methods=["GET", "POST"])
@role_required("student", "staff", "admin")
def new_complaint():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        location = request.form.get("location", "").strip()
        priority = request.form.get("priority", "Medium")
        file = request.files.get("photo")
        if not title or not description or not category or not location:
            flash("Please complete all required fields.", "danger")
            return render_template("new_complaint.html")
        if category not in CATEGORIES or priority not in PRIORITIES:
            abort(400)
        photo_path = None
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("Photo must be PNG, JPG, JPEG, or WEBP.", "danger")
                return render_template("new_complaint.html")
            filename = secure_filename(file.filename)
            filename = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + filename
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            photo_path = "uploads/" + filename
        cid = query_db("""INSERT INTO complaints(user_id,title,description,category,location,priority,photo_path)
            VALUES(%s,%s,%s,%s,%s,%s,%s)""",
            (session["user_id"], title, description, category, location, priority, photo_path), commit=True)
        query_db("INSERT INTO complaint_updates(complaint_id,user_id,status,note) VALUES(%s,%s,'Submitted','Complaint created')",
                 (cid, session["user_id"]), commit=True)
        flash("Complaint submitted successfully. Your ticket is #" + str(cid) + ".", "success")
        return redirect(url_for("complaint_detail", complaint_id=cid))
    return render_template("new_complaint.html", priorities=PRIORITIES)

@app.route("/complaints/<int:complaint_id>")
@login_required
def complaint_detail(complaint_id):
    complaint = query_db("""SELECT c.*,u.name reporter,u.email reporter_email,u.department,
        a.name assignee FROM complaints c JOIN users u ON u.id=c.user_id
        LEFT JOIN users a ON a.id=c.assigned_to WHERE c.id=%s""", (complaint_id,), one=True)
    if not complaint:
        abort(404)
    if session["role"] == "student" and complaint["user_id"] != session["user_id"]:
        abort(403)
    updates = query_db("""SELECT cu.*,u.name updater FROM complaint_updates cu
        LEFT JOIN users u ON u.id=cu.user_id WHERE complaint_id=%s ORDER BY cu.created_at DESC""",
        (complaint_id,))
    staff = query_db("SELECT id,name FROM users WHERE role='staff' ORDER BY name")
    return render_template("complaint_detail.html", complaint=complaint, updates=updates,
                           priorities=PRIORITIES, staff=staff)

@app.route("/complaints/<int:complaint_id>/update", methods=["POST"])
@role_required("admin", "staff")
def update_complaint(complaint_id):
    complaint = query_db("SELECT * FROM complaints WHERE id=%s", (complaint_id,), one=True)
    if not complaint:
        abort(404)
    status = request.form.get("status", "")
    note = request.form.get("note", "").strip()
    if status not in STATUSES:
        abort(400)
    assigned = request.form.get("assigned_to") if session["role"] == "admin" else None
    if session["role"] == "admin" and assigned:
        query_db("UPDATE complaints SET status=%s,assigned_to=%s WHERE id=%s",
                 (status, int(assigned), complaint_id), commit=True)
    else:
        query_db("UPDATE complaints SET status=%s WHERE id=%s", (status, complaint_id), commit=True)
    query_db("""INSERT INTO complaint_updates(complaint_id,user_id,status,note)
                VALUES(%s,%s,%s,%s)""",
             (complaint_id, session["user_id"], status, note or "Status updated"), commit=True)
    flash("Complaint updated.", "success")
    return redirect(url_for("complaint_detail", complaint_id=complaint_id))

@app.route("/admin/users", methods=["GET", "POST"])
@role_required("admin")
def admin_users():
    if request.method == "POST":
        uid = request.form.get("user_id", type=int)
        role = request.form.get("role", "")
        if role not in ("student", "staff", "admin"):
            abort(400)
        if uid == session["user_id"] and role != "admin":
            flash("You cannot remove your own admin role.", "warning")
        else:
            query_db("UPDATE users SET role=%s WHERE id=%s", (role, uid), commit=True)
            flash("User role updated.", "success")
        return redirect(url_for("admin_users"))
    users = query_db("SELECT id,name,email,department,role,created_at FROM users ORDER BY created_at DESC")
    return render_template("admin_users.html", users=users)

@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="You do not have permission to view this page."), 403

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="The page or complaint could not be found."), 404

@app.errorhandler(413)
def too_large(error):
    flash("Upload too large. Maximum image size is 5 MB.", "danger")
    return redirect(request.referrer or url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "true").lower() == "true")

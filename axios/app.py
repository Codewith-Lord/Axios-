from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os

import db
import auth
import email_utils
from parser import parse_resume
from matcher import calculate_match_score

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-this")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

with app.app_context():
    db.init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_user():
    return {"current_user": auth.current_user(), "brand_name": "Axios"}


# ---------- Home ----------
@app.route("/")
def home():
    return render_template("index.html")


# ---------- Auth: Register / Login / Logout (single Admin role) ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))

        if db.get_user_by_email(email):
            flash("An account with that email already exists.", "danger")
            return redirect(url_for("register"))

        password_hash = auth.hash_password(password)
        user_id = db.create_user(name, email, password_hash, role="Admin")
        user = db.get_user(user_id)
        auth.login_user(user)
        flash(f"Welcome, {name}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.get_user_by_email(email)
        if user and auth.verify_password(password, user["password_hash"]):
            auth.login_user(user)
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    auth.logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("home"))


# ---------- Dashboard & Analytics ----------
@app.route("/dashboard")
@auth.login_required
def dashboard():
    stats = db.get_dashboard_stats()
    jobs = db.get_all_jobs()
    return render_template("dashboard.html", stats=stats, jobs=jobs)


# ---------- Job Management ----------
@app.route("/jobs", methods=["GET", "POST"])
def jobs():
    if request.method == "POST":
        if not auth.current_user():
            flash("Please log in to post a job.", "danger")
            return redirect(url_for("login"))

        title = request.form.get("title")
        location = request.form.get("location")
        description = request.form.get("description")
        required_skills = request.form.get("required_skills")
        min_experience = request.form.get("min_experience", 0)

        db.create_job(
            title, description, required_skills, float(min_experience or 0),
            location=location, created_by=auth.current_user()["_id"],
        )
        flash("Job posted successfully!", "success")
        return redirect(url_for("jobs"))

    all_jobs = db.get_all_jobs()
    return render_template("jobs.html", jobs=all_jobs)


@app.route("/jobs/<job_id>/edit", methods=["GET", "POST"])
@auth.login_required
def edit_job(job_id):
    job = db.get_job(job_id)
    if job is None:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    if request.method == "POST":
        db.update_job(
            job_id,
            request.form.get("title"),
            request.form.get("description"),
            request.form.get("required_skills"),
            float(request.form.get("min_experience") or 0),
            location=request.form.get("location"),
        )
        flash("Job updated.", "success")
        return redirect(url_for("jobs"))

    return render_template("edit_job.html", job=job)


@app.route("/jobs/<job_id>/delete", methods=["POST"])
@auth.login_required
def delete_job(job_id):
    db.delete_job(job_id)
    flash("Job deleted.", "info")
    return redirect(url_for("jobs"))


# ---------- Candidate: Resume Upload ----------
@app.route("/jobs/<job_id>/apply", methods=["GET", "POST"])
def apply(job_id):
    job = db.get_job(job_id)
    if job is None:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    if request.method == "POST":
        file = request.files.get("resume")
        candidate_name = request.form.get("name")
        candidate_email = request.form.get("email")

        if not file or file.filename == "":
            flash("Please select a resume file.", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("Only PDF and DOCX files are allowed.", "danger")
            return redirect(request.url)

        filename = secure_filename(f"{candidate_email}_{file.filename}")
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        parsed_data = parse_resume(filepath)

        score = calculate_match_score(
            parsed_data,
            db.job_skills_list(job),
            job["min_experience"],
            resume_text=parsed_data.get("raw_text", ""),
            job_description=job.get("description", ""),
        )

        db.create_candidate(
            job_id=job_id,
            name=candidate_name or parsed_data.get("name") or "Unknown",
            email=candidate_email or parsed_data.get("email") or "",
            phone=parsed_data.get("phone"),
            skills=", ".join(parsed_data.get("skills", [])),
            experience_years=parsed_data.get("experience_years", 0),
            resume_path=filename,
            match_score=score,
            resume_text=parsed_data.get("raw_text", ""),
        )

        flash(f"Application submitted! Match score: {score}%", "success")
        return redirect(url_for("apply", job_id=job_id))

    return render_template("apply.html", job=job)


# ---------- Screening Dashboard (search + filter) ----------
@app.route("/jobs/<job_id>/candidates")
@auth.login_required
def candidates(job_id):
    job = db.get_job(job_id)
    if job is None:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    keyword = request.args.get("keyword", "").strip()
    min_score = request.args.get("min_score", "").strip()
    status = request.args.get("status", "").strip()

    ranked = db.search_candidates(
        job_id,
        keyword=keyword or None,
        min_score=float(min_score) if min_score else None,
        status=status or None,
    )
    return render_template(
        "candidates.html", job=job, candidates=ranked,
        keyword=keyword, min_score=min_score, status=status,
    )


@app.route("/jobs/<job_id>/shortlist")
@auth.login_required
def shortlist(job_id):
    job = db.get_job(job_id)
    if job is None:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    threshold = request.args.get("threshold", "70")
    threshold = float(threshold) if threshold else 70
    shortlisted = db.get_shortlist(job_id, threshold)
    return render_template("shortlist.html", job=job, candidates=shortlisted, threshold=threshold)


@app.route("/candidates/<candidate_id>/status", methods=["POST"])
@auth.login_required
def update_status(candidate_id):
    candidate = db.get_candidate(candidate_id)
    if candidate is None:
        flash("Candidate not found.", "danger")
        return redirect(url_for("jobs"))

    new_status = request.form.get("status")
    interview_datetime = request.form.get("interview_datetime", "").strip()

    if new_status not in ("Applied", "Shortlisted", "Rejected", "Interview Scheduled"):
        return redirect(url_for("candidates", job_id=candidate["job_id"]))

    if new_status == "Interview Scheduled":
        db.schedule_interview(candidate_id, interview_datetime or None)
    else:
        db.update_candidate_status(candidate_id, new_status)

    job = db.get_job(candidate["job_id"])
    subject = f"Application Update: {job['title']}"
    body = email_utils.status_update_body(
        candidate["name"], job["title"], new_status,
        interview_datetime=interview_datetime or None,
    )
    success, mode = email_utils.send_email(candidate["email"], subject, body)
    if success:
        db.mark_candidate_notified(candidate_id)
        note = "Email sent." if mode == "smtp" else "Email logged (no SMTP configured) — see notifications.log."
        flash(f"Status updated to {new_status}. {note}", "success")
    else:
        flash(f"Status updated to {new_status}, but notification could not be sent.", "info")

    return redirect(url_for("candidates", job_id=candidate["job_id"]))


# ---------- Simple JSON API (real-time dashboard polling) ----------
@app.route("/api/jobs/<job_id>/candidates")
def api_candidates(job_id):
    ranked = db.get_candidates_for_job(job_id)
    for c in ranked:
        c["_id"] = str(c["_id"])
    return jsonify(ranked)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")

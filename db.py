"""
Database layer — MongoDB (via pymongo), connecting to a local instance.

Collections:
    users       - Admin accounts
    jobs        - Job postings
    candidates  - Applicants + parsed data + scores + status

All document IDs are MongoDB ObjectIds. Routes/templates work with
their string representation (str(ObjectId)) so URLs stay clean.
"""

from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from datetime import datetime

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "axios_db"

client = MongoClient(MONGO_URI)
database = client[DB_NAME]

users = database["users"]
jobs = database["jobs"]
candidates = database["candidates"]


def init_db():
    """Create indexes. Mongo creates collections lazily on first insert,
    so nothing else to set up here."""
    users.create_index("email", unique=True)
    jobs.create_index([("created_at", DESCENDING)])
    candidates.create_index("job_id")


def _oid(id_str):
    """Safely convert a string to ObjectId; returns None if invalid."""
    try:
        return ObjectId(id_str)
    except Exception:
        return None


# ---------- User queries (auth) ----------
def create_user(name, email, password_hash, role="Admin"):
    result = users.insert_one({
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "created_at": datetime.utcnow(),
    })
    return str(result.inserted_id)


def get_user_by_email(email):
    return users.find_one({"email": email})


def get_user(user_id):
    oid = _oid(user_id)
    if not oid:
        return None
    return users.find_one({"_id": oid})


# ---------- Job queries ----------
def create_job(title, description, required_skills, min_experience, location=None, created_by=None):
    result = jobs.insert_one({
        "title": title,
        "location": location,
        "description": description,
        "required_skills": required_skills,
        "min_experience": min_experience,
        "created_by": created_by,
        "created_at": datetime.utcnow(),
    })
    return str(result.inserted_id)


def update_job(job_id, title, description, required_skills, min_experience, location=None):
    oid = _oid(job_id)
    if not oid:
        return
    jobs.update_one(
        {"_id": oid},
        {"$set": {
            "title": title,
            "location": location,
            "description": description,
            "required_skills": required_skills,
            "min_experience": min_experience,
        }},
    )


def get_all_jobs():
    return list(jobs.find().sort("created_at", DESCENDING))


def get_job(job_id):
    oid = _oid(job_id)
    if not oid:
        return None
    return jobs.find_one({"_id": oid})


def delete_job(job_id):
    oid = _oid(job_id)
    if not oid:
        return
    jobs.delete_one({"_id": oid})
    # Cascade delete candidates for this job (Mongo has no FK cascade)
    candidates.delete_many({"job_id": job_id})


def job_skills_list(job_doc):
    return [s.strip().lower() for s in (job_doc.get("required_skills") or "").split(",") if s.strip()]


# ---------- Candidate queries ----------
def create_candidate(job_id, name, email, phone, skills, experience_years,
                      resume_path, match_score, resume_text=""):
    result = candidates.insert_one({
        "job_id": job_id,
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "experience_years": experience_years,
        "resume_path": resume_path,
        "resume_text": resume_text,
        "match_score": match_score,
        "status": "Applied",
        "notified": False,
        "interview_datetime": None,
        "applied_at": datetime.utcnow(),
    })
    return str(result.inserted_id)


def get_candidates_for_job(job_id):
    return list(candidates.find({"job_id": job_id}).sort("match_score", DESCENDING))


def get_candidate(candidate_id):
    oid = _oid(candidate_id)
    if not oid:
        return None
    return candidates.find_one({"_id": oid})


def update_candidate_status(candidate_id, status):
    oid = _oid(candidate_id)
    if not oid:
        return
    candidates.update_one({"_id": oid}, {"$set": {"status": status}})


def schedule_interview(candidate_id, interview_datetime):
    oid = _oid(candidate_id)
    if not oid:
        return
    candidates.update_one(
        {"_id": oid},
        {"$set": {"status": "Interview Scheduled", "interview_datetime": interview_datetime}},
    )


def mark_candidate_notified(candidate_id):
    oid = _oid(candidate_id)
    if not oid:
        return
    candidates.update_one({"_id": oid}, {"$set": {"notified": True}})


def search_candidates(job_id, keyword=None, min_score=None, status=None):
    query = {"job_id": job_id}

    if keyword:
        like = keyword.strip().lower()
        query["$or"] = [
            {"name": {"$regex": like, "$options": "i"}},
            {"skills": {"$regex": like, "$options": "i"}},
        ]

    if min_score is not None:
        query["match_score"] = {"$gte": min_score}

    if status:
        query["status"] = status

    return list(candidates.find(query).sort("match_score", DESCENDING))


def get_shortlist(job_id, threshold=70):
    return list(
        candidates.find({"job_id": job_id, "match_score": {"$gte": threshold}})
        .sort("match_score", DESCENDING)
    )


# ---------- Analytics ----------
def get_dashboard_stats():
    total_jobs = jobs.count_documents({})
    total_candidates = candidates.count_documents({})

    avg_pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$match_score"}}}]
    avg_result = list(candidates.aggregate(avg_pipeline))
    avg_score = round(avg_result[0]["avg"], 2) if avg_result and avg_result[0]["avg"] is not None else 0

    status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    status_counts = {row["_id"]: row["count"] for row in candidates.aggregate(status_pipeline)}

    jobs_by_applicants = []
    for job in jobs.find().sort("created_at", DESCENDING):
        job_id_str = str(job["_id"])
        count = candidates.count_documents({"job_id": job_id_str})
        jobs_by_applicants.append({"id": job_id_str, "title": job["title"], "applicant_count": count})
    jobs_by_applicants.sort(key=lambda j: j["applicant_count"], reverse=True)
    jobs_by_applicants = jobs_by_applicants[:5]

    return {
        "total_jobs": total_jobs,
        "total_candidates": total_candidates,
        "avg_score": avg_score,
        "status_counts": status_counts,
        "jobs_by_applicants": jobs_by_applicants,
    }

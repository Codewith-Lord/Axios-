"""
Matching / Screening Engine
----------------------------
Combines two scoring approaches into one final match score:

1. STRUCTURED matching (skills list + years of experience) — precise,
   rule-based comparison against the job's stated requirements.

2. SEMANTIC matching — compares the full resume text against the job
   description using TF-IDF vectorization + cosine similarity. This
   captures contextual/textual similarity beyond exact keyword hits
   (e.g. a resume describing "built REST APIs with Django" will score
   well against a job asking for "backend web development experience"
   even without identical wording).

Final score is a weighted blend of both, so ranking reflects both
precise requirement-matching and overall contextual fit.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_skill_score(candidate_skills, required_skills):
    if not required_skills:
        return 100.0

    candidate_set = set(s.lower() for s in candidate_skills)
    required_set = set(s.lower() for s in required_skills)

    matched = candidate_set.intersection(required_set)
    return (len(matched) / len(required_set)) * 100 if required_set else 100.0


def calculate_experience_score(candidate_years, min_required_years):
    if min_required_years <= 0:
        return 100.0
    if candidate_years >= min_required_years:
        return 100.0
    return round((candidate_years / min_required_years) * 100, 2)


def calculate_semantic_score(resume_text, job_description, job_required_skills):
    """
    Returns 0-100 similarity between the resume text and the job's
    description + required skills, using TF-IDF + cosine similarity.
    """
    job_text = f"{job_description or ''} {' '.join(job_required_skills or [])}".strip()

    if not resume_text or not job_text:
        return 0.0

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([resume_text, job_text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return round(float(similarity) * 100, 2)
    except ValueError:
        # Happens if both texts are empty after stopword removal
        return 0.0


def calculate_match_score(parsed_data, job_required_skills, job_min_experience,
                           resume_text="", job_description=""):
    """
    parsed_data: dict returned by parser.parse_resume()
    job_required_skills: list of required skill strings
    job_min_experience: minimum years required (float)
    resume_text: full raw resume text, for semantic comparison
    job_description: job's free-text description, for semantic comparison

    Weighting:
        40% skill overlap (structured)
        20% experience match (structured)
        40% semantic similarity (contextual)
    """
    skill_score = calculate_skill_score(parsed_data.get("skills", []), job_required_skills)
    experience_score = calculate_experience_score(
        parsed_data.get("experience_years", 0), job_min_experience or 0
    )
    semantic_score = calculate_semantic_score(resume_text, job_description, job_required_skills)

    final_score = (0.4 * skill_score) + (0.2 * experience_score) + (0.4 * semantic_score)
    return round(final_score, 2)

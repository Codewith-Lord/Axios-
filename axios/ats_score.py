"""
ATS Score
----------
Estimates how well a resume would survive an Applicant Tracking
System's automated parsing — independent of any specific job.

This is deliberately NOT the same thing as the match score:
  - Match score = how well this resume fits THIS job
  - ATS score   = how well-structured/parseable this resume is, period

Real ATS software checks things like: can key fields be extracted
cleanly, are standard resume sections present, is there enough
substance to work with, and does it avoid parser-breaking formatting
(tables, images, columns — which we can't directly detect from
extracted text, but very short/garbled extracted text is a strong
proxy for "this file didn't extract cleanly").

Scoring is out of 100, split into five weighted checks:
    - Contact info present (email, phone)      20%
    - Skills section detected                  20%
    - Experience section detected               20%
    - Education section detected                 20%
    - Adequate content length (not too thin/       20%
      not obviously a parsing failure)
"""

import re

EXPERIENCE_KEYWORDS = [
    "experience", "worked", "developed", "managed", "led", "built",
    "designed", "implemented", "responsible for", "internship",
]

EDUCATION_KEYWORDS = [
    "degree", "university", "college", "bachelor", "master", "b.e",
    "b.tech", "m.tech", "b.sc", "m.sc", "diploma", "school",
]


def calculate_ats_score(parsed_data):
    """
    parsed_data: dict returned by parser.parse_resume()
    Returns (score: float 0-100, tips: list[str])
    """
    text_lower = (parsed_data.get("raw_text") or "").lower()
    tips = []
    score = 0.0

    # 1. Contact info (20%)
    has_email = bool(parsed_data.get("email"))
    has_phone = bool(parsed_data.get("phone"))
    contact_score = (has_email * 10) + (has_phone * 10)
    score += contact_score
    if not has_email:
        tips.append("Add a clearly visible email address.")
    if not has_phone:
        tips.append("Add a clearly visible phone number.")

    # 2. Skills section (20%)
    skills = parsed_data.get("skills", [])
    if len(skills) >= 5:
        score += 20
    elif len(skills) >= 2:
        score += 12
        tips.append("List more relevant skills explicitly (aim for 5+).")
    else:
        tips.append("Add a dedicated 'Skills' section listing your technical skills.")

    # 3. Experience section (20%)
    experience_hits = sum(1 for kw in EXPERIENCE_KEYWORDS if kw in text_lower)
    if experience_hits >= 2:
        score += 20
    elif experience_hits == 1:
        score += 10
        tips.append("Describe your work experience with more action verbs (built, led, developed...).")
    else:
        tips.append("Add a clear 'Experience' section describing your work history.")

    # 4. Education section (20%)
    education_hits = sum(1 for kw in EDUCATION_KEYWORDS if kw in text_lower)
    if education_hits >= 1:
        score += 20
    else:
        tips.append("Add a clear 'Education' section with your degree and institution.")

    # 5. Adequate content length (20%)
    text_length = len(parsed_data.get("raw_text") or "")
    if 300 <= text_length <= 8000:
        score += 20
    elif text_length < 300:
        tips.append("Resume text looks very short — the file may not be extracting cleanly, or needs more detail.")
        score += max(0, (text_length / 300) * 20)
    else:
        # Very long extracted text is usually fine, don't penalize hard
        score += 15

    return round(min(score, 100), 2), tips

"""
Resume Parsing Module
----------------------
Extracts structured data (name, email, phone, skills, experience)
from raw PDF/DOCX resume files using text extraction + regex/keyword matching.
"""

import re
import os
import docx
from pypdf import PdfReader

# A basic predefined skills dictionary — extend this as needed for your project
SKILLS_DB = [
    "python", "java", "c++", "c", "javascript", "typescript", "react", "angular",
    "vue", "node.js", "express", "django", "flask", "sql", "mysql", "postgresql",
    "mongodb", "html", "css", "bootstrap", "git", "github", "docker", "kubernetes",
    "aws", "azure", "gcp", "machine learning", "deep learning", "data analysis",
    "excel", "power bi", "tableau", "php", "laravel", "spring boot", "rest api",
    "linux", "agile", "scrum", "tensorflow", "pandas", "numpy", "r", "c#", ".net",
]

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
PHONE_REGEX = r"(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}"
EXPERIENCE_REGEX = r"(\d+(?:\.\d+)?)\s*\+?\s*years?"


def extract_text(filepath):
    """Extract raw text from a PDF or DOCX file."""
    ext = filepath.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif ext == "docx":
        document = docx.Document(filepath)
        return "\n".join(p.text for p in document.paragraphs)

    else:
        raise ValueError(f"Unsupported file type: {ext}")


def extract_email(text):
    match = re.search(EMAIL_REGEX, text)
    return match.group(0) if match else None


def extract_phone(text):
    match = re.search(PHONE_REGEX, text)
    return match.group(0).strip() if match else None


def extract_name(text):
    """Naive heuristic: assume the first non-empty line is the candidate's name."""
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and len(line.split()) <= 5 and not re.search(EMAIL_REGEX, line):
            return line
    return None


def extract_skills(text):
    text_lower = text.lower()
    found = []
    for skill in SKILLS_DB:
        # Word-boundary match so short skills like "c" or "r" don't match
        # inside unrelated words (e.g. "Computer", "years").
        pattern = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
        if re.search(pattern, text_lower):
            found.append(skill)
    return sorted(set(found))


def extract_experience_years(text):
    """Look for patterns like '3 years', '2.5+ years of experience'."""
    matches = re.findall(EXPERIENCE_REGEX, text.lower())
    if matches:
        years = [float(m) for m in matches]
        return max(years)  # take the largest mentioned figure
    return 0


def parse_resume(filepath):
    """
    Main entry point: takes a filepath to a resume (PDF/DOCX),
    returns a structured dict of extracted candidate data.
    """
    text = extract_text(filepath)

    parsed = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "experience_years": extract_experience_years(text),
        "raw_text_length": len(text),
        "raw_text": text,
    }
    return parsed


if __name__ == "__main__":
    # Quick manual test: python parser.py path/to/resume.pdf
    import sys
    if len(sys.argv) > 1:
        result = parse_resume(sys.argv[1])
        import json
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python parser.py <path_to_resume>")

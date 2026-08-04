# Axios — Finding Talent. Building Futures.

An AI-assisted resume screening system: single-admin auth, resume
parsing (PDF/DOCX), semantic + structured candidate scoring, real-time
ranking dashboard, and automated status-change notifications. Backed
by local MongoDB.

## What changed in this version

- **Database:** SQLite → local **MongoDB** (`pymongo`), DB name `axios_db`
- **Auth:** single **Admin** role only (no HR/Admin split)
- **Matching:** now combines structured skill/experience matching with
  **semantic similarity** (TF-IDF + cosine similarity) between the full
  resume text and the job description — see `matcher.py`
- **Workflow automation:** status updates can now also **schedule an
  interview date/time**, included automatically in the notification email
- **Branding:** rebranded to **Axios**, using your logo (`static/logo.png`)
- **UI:** redesigned with a navy/blue professional theme

## Requirements before running

1. **MongoDB must be installed and running locally** on the default port:
   ```
   mongodb://localhost:27017
   ```
   Start it (however you normally do, e.g. `mongod` in a terminal, or
   via a background service/MongoDB Compass) **before** running the app.

2. Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Run

```bash
python app.py
```

Open **http://127.0.0.1:5000**, then click **Get Started** to register
the (single) Admin account.

## How scoring works now

Final match score is a weighted blend:

| Component | Weight | What it measures |
|---|---|---|
| Skill overlap | 40% | Required skills the candidate's resume mentions |
| Experience | 20% | Candidate's years vs. job's minimum |
| Semantic similarity | 40% | TF-IDF + cosine similarity between full resume text and job description — captures contextual fit even without exact keyword matches |

## Project structure

```
axios/ (folder still named onresume — rename freely)
├── app.py            # Flask routes
├── db.py             # MongoDB layer (pymongo)
├── auth.py            # Password hashing + login-required decorator
├── email_utils.py       # Notifications (SMTP or logged fallback)
├── parser.py              # Resume parsing (PDF/DOCX -> structured data)
├── matcher.py                # Structured + semantic scoring
├── requirements.txt
├── templates/                  # Jinja2 pages, rebranded
├── static/
│   ├── style.css                # Axios navy/blue theme
│   └── logo.png                  # Your logo
└── uploads/                        # Uploaded resumes
```

## Email notifications

Same as before — set `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` /
`SMTP_PASSWORD` environment variables for real email sending;
otherwise notifications are written to `notifications.log` so you can
still demo the feature without real credentials.

## A note on testing

I tested the semantic matching engine and all Python files' syntax
directly. I could not run a full live end-to-end test against MongoDB
in the sandbox I built this in (no MongoDB server or internet access
there) — so please test the MongoDB-backed flows (register → post job
→ apply → view candidates → dashboard) on your machine first, and send
me any error you hit. The code follows standard, well-established
`pymongo` patterns, but a first real run is worth doing before your
demo/submission.

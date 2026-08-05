"""
Email Notification Module
---------------------------
Sends status-update emails to candidates via SMTP.

For a college project demo, real SMTP credentials often aren't
available. To keep this fully working either way:
- If SMTP_* environment variables are set, it sends a real email.
- If not, it "sends" the email by logging it to notifications.log
  (and printing to console) so you can still demo and screenshot
  the notification content for your report.
"""

import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOG_PATH = os.path.join(BASE_DIR, "notifications.log")

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")


def _log_notification(to_email, subject, body):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n--- {datetime.now().isoformat()} ---\n")
        f.write(f"To: {to_email}\nSubject: {subject}\n\n{body}\n")


def send_email(to_email, subject, body):
    """
    Returns (success: bool, mode: str) where mode is 'smtp' or 'logged'.
    Never raises — a failed/unconfigured send should not crash the app.
    """
    if not to_email:
        return False, "no_recipient"

    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = to_email

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, [to_email], msg.as_string())
            return True, "smtp"
        except Exception as e:
            # Fall back to logging so the workflow still completes
            _log_notification(to_email, subject, f"[SMTP send failed: {e}]\n\n{body}")
            return False, "logged"
    else:
        _log_notification(to_email, subject, body)
        return True, "logged"


def status_update_body(candidate_name, job_title, status, interview_datetime=None):
    interview_line = f" on {interview_datetime}" if interview_datetime else ""
    templates = {
        "Shortlisted": (
            f"Dear {candidate_name},\n\n"
            f"Congratulations! You have been shortlisted for the position of "
            f"{job_title}. Our HR team will reach out with next steps shortly.\n\n"
            f"Best regards,\nAxios Recruitment Team"
        ),
        "Interview Scheduled": (
            f"Dear {candidate_name},\n\n"
            f"We are pleased to inform you that your interview for the position "
            f"of {job_title} has been scheduled{interview_line}. Please be "
            f"available and prepared; further details will follow if needed.\n\n"
            f"Best regards,\nAxios Recruitment Team"
        ),
        "Rejected": (
            f"Dear {candidate_name},\n\n"
            f"Thank you for applying for the position of {job_title}. After "
            f"careful review, we have decided to move forward with other "
            f"candidates at this time. We wish you the best in your job search.\n\n"
            f"Best regards,\nAxios Recruitment Team"
        ),
    }
    return templates.get(
        status,
        f"Dear {candidate_name},\n\nYour application status for {job_title} "
        f"has been updated to: {status}.\n\nBest regards,\nAxios Recruitment Team",
    )

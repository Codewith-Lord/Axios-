"""
Authentication helpers — single Admin login.
Uses Flask's session (signed cookie) to track the logged-in admin, and
Werkzeug's password hashing (no extra dependency needed).
"""

from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

import db


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return check_password_hash(password_hash, password)


def login_user(user_doc):
    session["user_id"] = str(user_doc["_id"])
    session["user_name"] = user_doc["name"]


def logout_user():
    session.clear()


def current_user():
    if "user_id" not in session:
        return None
    return db.get_user(session["user_id"])


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "danger")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped

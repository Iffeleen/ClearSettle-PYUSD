from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services import auth_service
from app.utils import ratelimit

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if "@" not in email:
            flash("Please enter a valid email address.")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.")
        elif auth_service.create_merchant(email, password) is None:
            flash("An account with this email already exists.")
        else:
            flash("Account created. Please log in.")
            return redirect(url_for("auth.login"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        throttle_key = (request.remote_addr or "?") + "|" + email.lower()
        if ratelimit.is_blocked(throttle_key):
            flash("Too many failed attempts. Try again in a few minutes.")
            return render_template("login.html"), 429
        merchant = auth_service.authenticate_merchant(email, password)
        if merchant is None:
            ratelimit.record_failure(throttle_key)
            flash("Invalid email or password.")
        else:
            ratelimit.clear(throttle_key)
            session.clear()
            session["merchant_id"] = str(merchant["_id"])
            return redirect(url_for("dashboard.index"))
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("auth.login"))

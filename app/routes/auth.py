from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.services import auth_service
from app.utils import ratelimit, csrf
from app.utils.auth import login_required
from app.utils.choices import COUNTRIES, BUSINESS_TYPES

auth_bp = Blueprint("auth", __name__)


def _profile_from_form(form):
    return {f: form.get(f, "").strip() for f in auth_service.PROFILE_FIELDS}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        profile = _profile_from_form(request.form)
        username = request.form.get("username", "").strip()
        problem = auth_service.validate_profile(profile) or auth_service.validate_username(username)
        if "@" not in email or len(email) > 254:
            flash("Please enter a valid email address.")
        elif problem:
            flash(problem)
        elif len(password) < 8:
            flash("Password must be at least 8 characters.")
        elif auth_service.username_taken(username):
            flash("That username is already taken. Please choose another.")
        elif auth_service.create_merchant(email, password, profile, username) is None:
            flash("An account with this email already exists.")
        else:
            flash("Account created. Please log in.")
            return redirect(url_for("auth.login"))
    return render_template(
        "register.html",
        form=request.form,
        countries=COUNTRIES,
        business_types=BUSINESS_TYPES,
    )


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
            flash("Invalid username/email or password.")
        else:
            ratelimit.clear(throttle_key)
            session.clear()
            session["merchant_id"] = str(merchant["_id"])
            return redirect(url_for("dashboard.index"))
    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Log in with another account." if request.form.get("switch") == "1" else "You have been logged out.")
    return redirect(url_for("auth.login"))


@auth_bp.app_context_processor
def inject_current_merchant():
    """Make the logged-in merchant available to every template (sidebar chip)."""
    merchant_id = session.get("merchant_id")
    if not merchant_id:
        return {}
    merchant = auth_service.get_merchant(merchant_id)
    if merchant is None:
        return {}
    return {"current_merchant": auth_service.ensure_business_id(merchant)}


def _current_merchant_or_none():
    merchant = auth_service.get_merchant(session["merchant_id"])
    if merchant is None:
        session.clear()
        return None
    return auth_service.ensure_business_id(merchant)


def _profile_page(merchant, values):
    return render_template(
        "profile.html",
        merchant=merchant,
        values=values,
        countries=COUNTRIES,
        business_types=BUSINESS_TYPES,
        csrf_token=csrf.get_token(),
    )


@auth_bp.route("/profile")
@login_required
def profile():
    merchant = _current_merchant_or_none()
    if merchant is None:
        return redirect(url_for("auth.login"))
    return _profile_page(merchant, merchant)


@auth_bp.route("/profile/update", methods=["POST"])
@login_required
def profile_update():
    merchant = _current_merchant_or_none()
    if merchant is None:
        return redirect(url_for("auth.login"))
    if not csrf.is_valid():
        flash("Your session expired. Please try again.")
        return redirect(url_for("auth.profile"))

    email = request.form.get("email", "").strip()
    username = request.form.get("username", "").strip()
    values = _profile_from_form(request.form)
    values["email"] = email
    values["username"] = username

    problem = None
    if "@" not in email or len(email) > 254:
        problem = "Please enter a valid email address."
    if problem is None:
        problem = auth_service.validate_profile(values)
    if problem is None and (username or merchant.get("username")):
        problem = auth_service.validate_username(username)
    if problem is None and auth_service.email_taken(email, merchant["_id"]):
        problem = "Another account already uses that email."
    if problem is None and username and auth_service.username_taken(username, merchant["_id"]):
        problem = "That username is already taken."
    if problem:
        flash(problem)
        return _profile_page(merchant, values)

    auth_service.update_profile(merchant["_id"], email, username, values)
    flash("Profile updated.")
    return redirect(url_for("auth.profile"))


@auth_bp.route("/profile/password", methods=["POST"])
@login_required
def password_change():
    merchant = _current_merchant_or_none()
    if merchant is None:
        return redirect(url_for("auth.login"))
    if not csrf.is_valid():
        flash("Your session expired. Please try again.")
        return redirect(url_for("auth.profile"))

    key = "pw|" + str(merchant["_id"])
    if ratelimit.is_blocked(key):
        flash("Too many failed attempts. Try again in a few minutes.")
        return redirect(url_for("auth.profile"))

    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    if len(new) < 8:
        flash("New password must be at least 8 characters.")
    elif new != confirm:
        flash("New password and confirmation do not match.")
    elif not auth_service.change_password(merchant, current, new):
        ratelimit.record_failure(key)
        flash("Current password is incorrect.")
    else:
        ratelimit.clear(key)
        flash("Password changed.")
    return redirect(url_for("auth.profile"))

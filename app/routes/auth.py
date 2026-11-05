from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services import auth_service

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
            flash("Account created. Login comes in the next step.")
            return redirect(url_for("auth.register"))
    return render_template("register.html")

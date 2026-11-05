from flask import Blueprint, render_template, session, redirect, url_for
from app.services import auth_service
from app.utils.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    merchant = auth_service.get_merchant(session["merchant_id"])
    if merchant is None:
        session.clear()
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", merchant=merchant)

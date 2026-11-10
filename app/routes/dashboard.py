from flask import Blueprint, render_template, session, redirect, url_for
from app.services import auth_service, order_service
from app.utils.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    merchant = auth_service.get_merchant(session["merchant_id"])
    if merchant is None:
        session.clear()
        return redirect(url_for("auth.login"))
    orders = order_service.list_orders(session["merchant_id"])
    return render_template(
        "dashboard.html",
        merchant=merchant,
        stats=order_service.dashboard_stats(session["merchant_id"], orders),
        recent=orders[:5],
    )

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.services import order_service
from app.utils.auth import login_required
from app.utils.money import dollars_to_cents

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders")
@login_required
def index():
    orders = order_service.list_orders(session["merchant_id"])
    return render_template("orders_list.html", orders=orders)


@orders_bp.route("/orders/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        buyer_name = request.form.get("buyer_name", "").strip()
        buyer_email = request.form.get("buyer_email", "").strip()
        description = request.form.get("description", "").strip()
        amount_cents = dollars_to_cents(request.form.get("amount", ""))
        if not buyer_name or len(buyer_name) > 100:
            flash("Enter the buyer's name (up to 100 characters).")
        elif "@" not in buyer_email:
            flash("Enter a valid buyer email.")
        elif not description or len(description) > 200:
            flash("Enter a description (up to 200 characters).")
        elif amount_cents is None:
            flash("Enter an amount from 0.01 to 10000.00 with at most 2 decimals.")
        else:
            order_id = order_service.create_order(
                session["merchant_id"], buyer_name, buyer_email, description, amount_cents
            )
            flash("Order created.")
            return redirect(url_for("orders.detail", order_id=str(order_id)))
    return render_template("order_new.html")


@orders_bp.route("/orders/<order_id>")
@login_required
def detail(order_id):
    order = order_service.get_order(session["merchant_id"], order_id)
    if order is None:
        abort(404)
    return render_template("order_detail.html", order=order)

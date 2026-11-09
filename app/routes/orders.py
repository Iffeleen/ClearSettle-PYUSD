import secrets
import hmac

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
)

from app.services import order_service
from app.services import evidence_service
from app.services import braintree_service
from app.services.policy_service import get_verified_policies
from app.utils.auth import login_required
from app.utils.money import dollars_to_cents, cents_to_dollars


orders_bp = Blueprint("orders", __name__)


def get_buyer_protection_policy():
    policies = get_verified_policies()

    return next(
        (
            policy for policy in policies
            if policy.get("id") == "buyer_protection"
        ),
        None,
    )


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
                session["merchant_id"],
                buyer_name,
                buyer_email,
                description,
                amount_cents,
            )
            flash("Order created.")
            return redirect(
                url_for("orders.detail", order_id=str(order_id))
            )

    return render_template("order_new.html")


@orders_bp.route("/orders/<order_id>")
@login_required
def detail(order_id):
    order = order_service.get_order(
        session["merchant_id"],
        order_id,
    )

    if order is None:
        abort(404)

    csrf_token = session.setdefault(
        "csrf_token",
        secrets.token_urlsafe(32),
    )

    policy = get_buyer_protection_policy()

    # Show the newly generated buyer link only once.
    buyer_consent_link = session.pop("buyer_consent_link", None)

    evidence_items = evidence_service.list_evidence(
        session["merchant_id"], order_id
    )
    missing, readiness_label = evidence_service.readiness(evidence_items)

    return render_template(
        "order_detail.html",
        evidence_items=evidence_items,
        missing=missing,
        readiness_label=readiness_label,
        order=order,
        policy=policy,
        csrf_token=csrf_token,
        buyer_consent_link=buyer_consent_link,
    )


@orders_bp.route(
    "/orders/<order_id>/merchant-consent",
    methods=["POST"],
)
@login_required
def merchant_consent(order_id):
    submitted_token = request.form.get("csrf_token", "")
    stored_token = session.get("csrf_token", "")

    if (
        not submitted_token
        or not stored_token
        or not hmac.compare_digest(submitted_token, stored_token)
    ):
        abort(400)

    if get_buyer_protection_policy() is None:
        flash("The verified Buyer Protection policy is unavailable.")
        return redirect(
            url_for("orders.detail", order_id=order_id)
        )

    decision = request.form.get("decision", "")

    result = order_service.record_merchant_consent(
        session["merchant_id"],
        order_id,
        decision,
    )

    if result is None:
        flash(
            "Decision not recorded. Check the order or whether "
            "a decision was already submitted."
        )

    elif decision == "accepted":
        session["buyer_consent_link"] = url_for(
            "orders.buyer_consent",
            token=result,
            _external=True,
        )
        flash("Merchant consent recorded. Share the buyer link below.")

    else:
        flash("Merchant declined the explanation. No buyer link was created.")

    return redirect(
        url_for("orders.detail", order_id=order_id)
    )


@orders_bp.route(
    "/buyer-consent/<token>",
    methods=["GET", "POST"],
)
def buyer_consent(token):
    order = order_service.get_order_by_buyer_token(token)

    if order is None:
        return render_template(
            "buyer_consent_unavailable.html"
        ), 404

    policy = get_buyer_protection_policy()

    if policy is None:
        return render_template(
            "buyer_consent_unavailable.html"
        ), 503

    csrf_token = session.setdefault(
        "csrf_token",
        secrets.token_urlsafe(32),
    )

    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        stored_token = session.get("csrf_token", "")

        if (
            not submitted_token
            or not stored_token
            or not hmac.compare_digest(submitted_token, stored_token)
        ):
            abort(400)

        decision = request.form.get("decision", "")

        success = order_service.record_buyer_consent(
            token,
            decision,
        )

        if not success:
            return render_template(
                "buyer_consent_unavailable.html"
            ), 409

        return render_template(
            "buyer_consent_result.html",
            decision=decision,
        )

    return render_template(
        "buyer_consent.html",
        order=order,
        policy=policy,
        csrf_token=csrf_token,
    )


@orders_bp.route(
    "/orders/<order_id>/new-buyer-link",
    methods=["POST"],
)
@login_required
def new_buyer_link(order_id):
    submitted_token = request.form.get("csrf_token", "")
    stored_token = session.get("csrf_token", "")

    if (
        not submitted_token
        or not stored_token
        or not hmac.compare_digest(submitted_token, stored_token)
    ):
        abort(400)

    token = order_service.regenerate_buyer_link_token(
        session["merchant_id"],
        order_id,
    )

    if token is None:
        flash("Could not create a link. The buyer may have already responded.")
    else:
        session["buyer_consent_link"] = url_for(
            "orders.buyer_consent",
            token=token,
            _external=True,
        )
        flash("New buyer link created. Any older link no longer works.")

    return redirect(url_for("orders.detail", order_id=order_id))


@orders_bp.route("/orders/<order_id>/evidence", methods=["POST"])
@login_required
def upload_evidence(order_id):
    submitted_token = request.form.get("csrf_token", "")
    stored_token = session.get("csrf_token", "")

    if (
        not submitted_token
        or not stored_token
        or not hmac.compare_digest(submitted_token, stored_token)
    ):
        abort(400)

    evidence_id, error = evidence_service.save_evidence(
        session["merchant_id"],
        order_id,
        request.form.get("evidence_type", ""),
        request.files.get("file"),
    )

    flash(error or "Evidence uploaded and fingerprinted.")
    return redirect(url_for("orders.detail", order_id=order_id))


@orders_bp.route("/orders/<order_id>/pay", methods=["GET", "POST"])
@login_required
def pay(order_id):
    order = order_service.get_order(session["merchant_id"], order_id)
    if order is None:
        abort(404)

    detail_url = url_for("orders.detail", order_id=order_id)

    if order["status"] != "pending":
        flash("This order is not waiting for payment.")
        return redirect(detail_url)

    buyer = order.get("consents", {}).get("buyer", {})
    if buyer.get("status") != "accepted":
        flash("The buyer must accept the consent explanation before payment.")
        return redirect(detail_url)

    csrf_token = session.setdefault("csrf_token", secrets.token_urlsafe(32))

    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        if not submitted or not hmac.compare_digest(submitted, csrf_token):
            abort(400)

        nonce = request.form.get("payment_method_nonce", "")
        if not nonce:
            flash("No payment method was provided.")
            return redirect(url_for("orders.pay", order_id=order_id))

        amount = cents_to_dollars(order["amount_cents"])
        details, error = braintree_service.create_sale(amount, nonce)

        if error:
            flash("Payment failed: " + error)
            return redirect(url_for("orders.pay", order_id=order_id))

        saved = order_service.mark_order_paid(
            order_id, details["transaction_id"], details["status"]
        )
        if saved:
            flash("Sandbox payment successful.")
        else:
            flash("Payment went through but the order was not updated. "
                  "Transaction ID: " + details["transaction_id"])
        return redirect(detail_url)

    return render_template(
        "pay.html",
        order=order,
        client_token=braintree_service.generate_client_token(),
        csrf_token=csrf_token,
    )


@orders_bp.route("/orders/<order_id>/shipping", methods=["POST"])
@login_required
def save_shipping(order_id):
    submitted = request.form.get("csrf_token", "")
    stored = session.get("csrf_token", "")
    if not submitted or not stored or not hmac.compare_digest(submitted, stored):
        abort(400)

    courier = request.form.get("courier", "").strip()
    tracking = request.form.get("tracking_number", "").strip()

    if not courier or len(courier) > 50:
        flash("Enter the courier name (up to 50 characters).")
    elif not (6 <= len(tracking) <= 40) or not tracking.replace("-", "").isalnum():
        flash("Tracking number must be 6-40 letters, digits or hyphens.")
    elif order_service.set_shipping(session["merchant_id"], order_id, courier, tracking):
        flash("Shipping details saved.")
    else:
        flash("Could not save. The order must be yours and already paid.")

    return redirect(url_for("orders.detail", order_id=order_id))

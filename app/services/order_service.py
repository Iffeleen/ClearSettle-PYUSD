from datetime import datetime, timezone, timedelta
import hashlib
import secrets

from bson import ObjectId
from bson.errors import InvalidId

from app.db import get_db


POLICY_ID = "buyer_protection"
POLICY_VERSION = "2026-11-06-v1"
BUYER_TOKEN_VALIDITY_DAYS = 7


def hash_buyer_token(token):
    """Hash a buyer token before storing or searching for it."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_order(merchant_id, buyer_name, buyer_email, description, amount_cents):
    now = datetime.now(timezone.utc)

    order = {
        "merchant_id": ObjectId(merchant_id),
        "buyer_name": buyer_name,
        "buyer_email": buyer_email,
        "description": description,
        "currency": "USD",
        "amount_cents": amount_cents,
        "status": "pending",
        "paypal_order_id": None,
        "created_at": now,
        "consents": {
            "merchant": {
                "status": "pending",
                "timestamp": None,
                "policy_id": POLICY_ID,
                "policy_version": POLICY_VERSION,
                "jurisdiction": "US",
            },
            "buyer": {
                "status": "pending",
                "timestamp": None,
                "policy_id": POLICY_ID,
                "policy_version": POLICY_VERSION,
                "jurisdiction": "US",
            },
        },
        "buyer_consent_token_hash": None,
        "buyer_consent_expires_at": None,
    }

    result = get_db().orders.insert_one(order)
    return result.inserted_id


def list_orders(merchant_id):
    cursor = (
        get_db()
        .orders
        .find({"merchant_id": ObjectId(merchant_id)})
        .sort("created_at", -1)
    )
    return list(cursor)


def get_order(merchant_id, order_id):
    try:
        return get_db().orders.find_one(
            {
                "_id": ObjectId(order_id),
                "merchant_id": ObjectId(merchant_id),
            }
        )
    except InvalidId:
        return None


def record_merchant_consent(merchant_id, order_id, decision):
    """
    Record one merchant decision.
    If accepted, create a one-time buyer token and return it.
    If declined, return an empty string after recording the decision.
    Return None if the decision could not be recorded.
    """
    if decision not in ("accepted", "declined"):
        return None

    now = datetime.now(timezone.utc)
    buyer_token = None

    update_fields = {
        "consents.merchant.status": decision,
        "consents.merchant.timestamp": now,
    }

    if decision == "accepted":
        buyer_token = secrets.token_urlsafe(32)
        update_fields["buyer_consent_token_hash"] = hash_buyer_token(
            buyer_token
        )
        update_fields["buyer_consent_expires_at"] = (
            now + timedelta(days=BUYER_TOKEN_VALIDITY_DAYS)
        )

    try:
        result = get_db().orders.update_one(
            {
                "_id": ObjectId(order_id),
                "merchant_id": ObjectId(merchant_id),
                "consents.merchant.status": "pending",
            },
            {"$set": update_fields},
        )
    except InvalidId:
        return None

    if result.modified_count != 1:
        return None

    return buyer_token if decision == "accepted" else ""


def get_order_by_buyer_token(token):
    """Find an order using a valid, unexpired, pending buyer token."""
    if not token:
        return None

    token_hash = hash_buyer_token(token)
    now = datetime.now(timezone.utc)

    return get_db().orders.find_one(
        {
            "buyer_consent_token_hash": token_hash,
            "buyer_consent_expires_at": {"$gt": now},
            "consents.buyer.status": "pending",
        }
    )


def record_buyer_consent(token, decision):
    """Record one buyer decision and invalidate the token."""
    if not token or decision not in ("accepted", "declined"):
        return False

    now = datetime.now(timezone.utc)
    token_hash = hash_buyer_token(token)

    result = get_db().orders.update_one(
        {
            "buyer_consent_token_hash": token_hash,
            "buyer_consent_expires_at": {"$gt": now},
            "consents.buyer.status": "pending",
        },
        {
            "$set": {
                "consents.buyer.status": decision,
                "consents.buyer.timestamp": now,
            },
            "$unset": {
                "buyer_consent_token_hash": "",
                "buyer_consent_expires_at": "",
            },
        },
    )

    return result.modified_count == 1


def regenerate_buyer_link_token(merchant_id, order_id):
    """Create a fresh buyer token for an owned order whose merchant
    consent is accepted and buyer consent is still pending.
    Returns the raw token (shown once) or None."""
    import secrets
    from datetime import timedelta

    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    try:
        result = get_db().orders.update_one(
            {
                "_id": ObjectId(order_id),
                "merchant_id": ObjectId(merchant_id),
                "consents.merchant.status": "accepted",
                "consents.buyer.status": "pending",
            },
            {
                "$set": {
                    "buyer_consent_token_hash": hash_buyer_token(token),
                    "buyer_consent_expires_at": now + timedelta(days=7),
                }
            },
        )
    except InvalidId:
        return None

    return token if result.modified_count == 1 else None


def mark_order_paid(order_id, transaction_id, braintree_status):
    """Record a successful Braintree sandbox payment on a pending order.
    Returns True only if exactly one pending order was updated."""
    try:
        result = get_db().orders.update_one(
            {"_id": ObjectId(order_id), "status": "pending"},
            {
                "$set": {
                    "status": "paid",
                    "payment": {
                        "provider": "braintree_sandbox",
                        "transaction_id": transaction_id,
                        "provider_status": braintree_status,
                        "paid_at": datetime.now(timezone.utc),
                    },
                }
            },
        )
    except InvalidId:
        return False
    return result.modified_count == 1


def set_shipping(merchant_id, order_id, courier, tracking_number):
    """Save courier and tracking number on a paid order the merchant owns."""
    try:
        result = get_db().orders.update_one(
            {
                "_id": ObjectId(order_id),
                "merchant_id": ObjectId(merchant_id),
                "status": "paid",
            },
            {
                "$set": {
                    "shipping": {
                        "courier": courier,
                        "tracking_number": tracking_number,
                        "recorded_at": datetime.now(timezone.utc),
                    }
                }
            },
        )
    except InvalidId:
        return False
    return result.matched_count == 1


def filter_orders(merchant_id, orders, name):
    """Narrow a merchant's order list for the sidebar buttons.
    name is one of: unpaid, paid, disputes, settled (anything else = all)."""
    if name == "unpaid":
        return [o for o in orders if o["status"] == "pending"]
    if name == "paid":
        return [o for o in orders if o["status"] == "paid"]
    if name == "settled":
        return [o for o in orders if o.get("settlement")]
    if name == "disputes":
        ids = {
            d["order_id"]
            for d in get_db().disputes.find(
                {"merchant_id": ObjectId(merchant_id)}, {"order_id": 1}
            )
        }
        return [o for o in orders if o["_id"] in ids]
    return orders


def dashboard_stats(merchant_id, orders):
    """Simple counts for the dashboard cards."""
    open_disputes = get_db().disputes.count_documents(
        {"merchant_id": ObjectId(merchant_id), "status": "open"}
    )
    paid = [o for o in orders if o["status"] == "paid"]
    return {
        "total": len(orders),
        "awaiting": sum(1 for o in orders if o["status"] == "pending"),
        "paid": len(paid),
        "paid_cents": sum(o["amount_cents"] for o in paid),
        "open_disputes": open_disputes,
        "settled": sum(1 for o in orders if o.get("settlement")),
    }

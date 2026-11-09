from datetime import datetime, timedelta, timezone

from app.db import get_db
from app.services.evidence_service import list_evidence, readiness
from app.services.order_service import get_order

DISPUTE_REASONS = ("item_not_received", "item_not_as_described")


def create_simulated_dispute(merchant_id, order_id, reason):
    """Create a SIMULATED dispute on a paid order. Returns (id, error)."""
    if reason not in DISPUTE_REASONS:
        return None, "Invalid dispute reason."
    order = get_order(merchant_id, order_id)
    if order is None:
        return None, "Order not found."
    if order["status"] != "paid":
        return None, "Only paid orders can have a dispute."
    if get_db().disputes.find_one({"order_id": order["_id"], "status": "open"}):
        return None, "An open dispute already exists for this order."

    now = datetime.now(timezone.utc)
    doc = {
        "order_id": order["_id"],
        "merchant_id": order["merchant_id"],
        "reason": reason,
        "status": "open",
        "simulated": True,
        "demo_deadline": now + timedelta(days=10),
        "created_at": now,
        "draft_response": None,
        "merchant_approved": False,
    }
    return get_db().disputes.insert_one(doc).inserted_id, None


def build_dispute_facts(merchant_id, order_id):
    """Collect verified facts from our own database. Returns a dict or None."""
    order = get_order(merchant_id, order_id)
    if order is None:
        return None
    items = list_evidence(merchant_id, order_id)
    missing, label = readiness(items)
    consents = order.get("consents", {})
    payment = order.get("payment") or {}
    shipping = order.get("shipping") or {}
    return {
        "item": order["description"],
        "amount": f"{order['amount_cents'] // 100}.{order['amount_cents'] % 100:02d} {order['currency']}",
        "payment_provider": payment.get("provider"),
        "payment_transaction_id": payment.get("transaction_id"),
        "buyer_consent_status": consents.get("buyer", {}).get("status", "pending"),
        "buyer_consent_time": str(consents.get("buyer", {}).get("timestamp")),
        "courier": shipping.get("courier"),
        "tracking_number": shipping.get("tracking_number"),
        "evidence": [
            {"type": e["evidence_type"], "sha256": e["sha256"],
             "uploaded_at": str(e["uploaded_at"])}
            for e in items
        ],
        "missing_evidence": missing,
        "completeness": label,
    }

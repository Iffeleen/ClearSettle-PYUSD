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


import os

import requests

from app.services import ai_service


def get_dispute(merchant_id, order_id):
    """Latest dispute for an order the merchant owns, or None."""
    order = get_order(merchant_id, order_id)
    if order is None:
        return None
    return get_db().disputes.find_one(
        {"order_id": order["_id"]}, sort=[("created_at", -1)]
    )


def generate_draft(merchant_id, order_id):
    """Ask the AI for a draft reply from verified facts. Returns (draft, error)."""
    dispute = get_dispute(merchant_id, order_id)
    if dispute is None or dispute["status"] != "open":
        return None, "No open dispute for this order."
    facts = build_dispute_facts(merchant_id, order_id)
    system, user = ai_service.build_dispute_prompt(facts, dispute["reason"])
    try:
        draft = ai_service.call_llm(system, user)
    except (RuntimeError, requests.exceptions.RequestException):
        return None, "The AI service is unavailable right now. Please try again."
    get_db().disputes.update_one(
        {"_id": dispute["_id"], "status": "open"},
        {"$set": {
            "draft_response": draft,
            "draft_generated_at": datetime.now(timezone.utc),
            "ai_model": os.getenv("GEMINI_MODEL", "unknown"),
            "merchant_approved": False,
        }},
    )
    return draft, None


def save_response(merchant_id, order_id, text, approve):
    """Save the merchant's edited text; if approve, mark it submitted (SIMULATED).
    Returns (ok, message)."""
    text = (text or "").strip()
    if not text or len(text) > 2000:
        return False, "The response must be between 1 and 2000 characters."
    dispute = get_dispute(merchant_id, order_id)
    if dispute is None or dispute["status"] != "open":
        return False, "No open dispute for this order."
    now = datetime.now(timezone.utc)
    changes = {"edited_response": text}
    if approve:
        changes.update({
            "status": "submitted_simulated",
            "merchant_approved": True,
            "approved_at": now,
            "submitted_at": now,
            "final_response": text,
        })
    result = get_db().disputes.update_one(
        {"_id": dispute["_id"], "status": "open"}, {"$set": changes}
    )
    if result.matched_count != 1:
        return False, "Could not save."
    return True, ("Approved and submitted (SIMULATED, nothing was sent to PayPal)."
                  if approve else "Draft saved.")

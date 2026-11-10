import secrets
from datetime import datetime, timezone

from app.db import get_db
from app.services.order_service import get_order


def settle_simulated(merchant_id, order_id):
    """Record a SIMULATED PYUSD settlement. Returns (ok, message)."""
    order = get_order(merchant_id, order_id)
    if order is None:
        return False, "Order not found."
    if order["status"] != "paid":
        return False, "Only paid orders can be settled."
    if order.get("settlement"):
        return False, "This order was already settled (simulated)."
    if get_db().disputes.find_one({"order_id": order["_id"], "status": "open"}):
        return False, "Resolve the open dispute before settlement."

    cents = order["amount_cents"]
    result = get_db().orders.update_one(
        {
            "_id": order["_id"],
            "merchant_id": order["merchant_id"],
            "status": "paid",
            "settlement": {"$exists": False},
        },
        {"$set": {"settlement": {
            "mode": "simulation",
            "asset": "PYUSD",
            "amount": f"{cents // 100}.{cents % 100:02d}",
            "reference": "SIM-" + secrets.token_hex(4).upper(),
            "created_at": datetime.now(timezone.utc),
            "note": "Simulated. No PYUSD was transferred and no wallet was used.",
        }}},
    )
    if result.matched_count != 1:
        return False, "Could not record the settlement."
    return True, "Simulated PYUSD settlement recorded (no real transfer)."

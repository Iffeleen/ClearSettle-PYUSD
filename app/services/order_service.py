from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from app.db import get_db


def create_order(merchant_id, buyer_name, buyer_email, description, amount_cents):
    order = {
        "merchant_id": ObjectId(merchant_id),
        "buyer_name": buyer_name,
        "buyer_email": buyer_email,
        "description": description,
        "currency": "USD",
        "amount_cents": amount_cents,
        "status": "pending",
        "paypal_order_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = get_db().orders.insert_one(order)
    return result.inserted_id


def list_orders(merchant_id):
    cursor = get_db().orders.find({"merchant_id": ObjectId(merchant_id)}).sort("created_at", -1)
    return list(cursor)


def get_order(merchant_id, order_id):
    try:
        return get_db().orders.find_one(
            {"_id": ObjectId(order_id), "merchant_id": ObjectId(merchant_id)}
        )
    except InvalidId:
        return None

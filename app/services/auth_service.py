from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import get_db


def create_merchant(email, password):
    email = email.strip().lower()
    db = get_db()
    if db.merchants.find_one({"email": email}):
        return None
    merchant = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.now(timezone.utc),
    }
    result = db.merchants.insert_one(merchant)
    return result.inserted_id


def authenticate_merchant(email, password):
    email = email.strip().lower()
    merchant = get_db().merchants.find_one({"email": email})
    if merchant is None:
        return None
    if not check_password_hash(merchant["password_hash"], password):
        return None
    return merchant


def get_merchant(merchant_id):
    try:
        return get_db().merchants.find_one({"_id": ObjectId(merchant_id)})
    except InvalidId:
        return None

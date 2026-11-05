from datetime import datetime, timezone
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

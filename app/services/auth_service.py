import re
import secrets
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import get_db
from app.utils.choices import COUNTRIES, BUSINESS_TYPES

PROFILE_FIELDS = ("name", "phone", "country", "business_type", "business_name")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{6,19}$")


def validate_profile(profile):
    """Return an error message for the first bad field, or None if all fine."""
    if not 2 <= len(profile.get("name", "")) <= 100:
        return "Please enter your full name (2 to 100 characters)."
    if not _PHONE_RE.match(profile.get("phone", "")):
        return "Please enter a valid phone number, for example +8801XXXXXXXXX."
    if profile.get("country") not in COUNTRIES:
        return "Please choose a country from the list."
    if profile.get("business_type") not in BUSINESS_TYPES:
        return "Please choose a business type from the list."
    if not 2 <= len(profile.get("business_name", "")) <= 100:
        return "Please enter your business name (2 to 100 characters)."
    return None


def create_merchant(email, password, profile=None, username=None):
    email = email.strip().lower()
    db = get_db()
    if db.merchants.find_one({"email": email}):
        return None
    merchant = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "business_id": _new_business_id(),
        "created_at": datetime.now(timezone.utc),
    }
    for field in PROFILE_FIELDS:
        merchant[field] = (profile or {}).get(field, "")
    if username:
        merchant["username"] = username.strip().lower()
    result = db.merchants.insert_one(merchant)
    return result.inserted_id


def authenticate_merchant(email, password):
    email = email.strip().lower()
    # "email" here is whatever the person typed: an email or a username.
    # Usernames cannot contain "@", so the two are easy to tell apart.
    key = "email" if "@" in email else "username"
    merchant = get_db().merchants.find_one({key: email})
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


def _new_business_id():
    db = get_db()
    while True:
        candidate = "CS-" + secrets.token_hex(4).upper()
        if not db.merchants.find_one({"business_id": candidate}):
            return candidate


def ensure_business_id(merchant):
    """Give older accounts a business ID the first time we need it."""
    if merchant.get("business_id"):
        return merchant
    new_id = _new_business_id()
    get_db().merchants.update_one(
        {"_id": merchant["_id"], "business_id": {"$exists": False}},
        {"$set": {"business_id": new_id}},
    )
    return get_merchant(merchant["_id"])


_USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9_.]{2,29}$")


def validate_username(username):
    """Return an error message, or None if the username is acceptable."""
    if not _USERNAME_RE.match(username.strip().lower()):
        return ("Username must be 3 to 30 characters: letters, numbers, dots or "
                "underscores, starting with a letter or number.")
    return None


def username_taken(username, except_id=None):
    """True if another account already uses this username."""
    query = {"username": username.strip().lower()}
    if except_id is not None:
        query["_id"] = {"$ne": except_id}
    return get_db().merchants.find_one(query) is not None

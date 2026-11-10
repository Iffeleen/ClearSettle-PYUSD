import hmac
import secrets
from flask import session, request


def get_token():
    """Return this session's CSRF token, creating it if needed."""
    return session.setdefault("csrf_token", secrets.token_urlsafe(32))


def is_valid():
    """True if the token submitted in the form matches the session's token."""
    submitted = request.form.get("csrf_token", "")
    stored = session.get("csrf_token", "")
    if not submitted or not stored:
        return False
    return hmac.compare_digest(submitted.encode(), stored.encode())

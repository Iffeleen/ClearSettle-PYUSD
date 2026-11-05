from flask import Blueprint, jsonify
from app import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return "ClearSettle is running"


@main_bp.route("/health")
def health():
    try:
        db.ping_db()
        return jsonify({"flask": "ok", "mongodb": "ok"})
    except Exception as e:
        return jsonify({"flask": "ok", "mongodb": "error", "detail": str(e)}), 500

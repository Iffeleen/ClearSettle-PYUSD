from flask import Blueprint, jsonify, redirect, url_for, session
from app import db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    if "merchant_id" in session:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@main_bp.route("/health")
def health():
    try:
        db.ping_db()
        return jsonify({"flask": "ok", "mongodb": "ok"})
    except Exception as e:
        return jsonify({"flask": "ok", "mongodb": "error", "detail": str(e)}), 500

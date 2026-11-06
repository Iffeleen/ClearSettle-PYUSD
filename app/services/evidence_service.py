import secrets
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.utils import secure_filename

from app.db import get_db
from app.services.order_service import get_order
from app.utils.hashing import sha256_of_file
from app.utils.uploads import ALLOWED_TYPES, detect_image_type

UPLOAD_ROOT = Path(__file__).resolve().parent.parent.parent / "uploads"
EVIDENCE_TYPES = ("packing_photo", "shipping_label", "delivery_proof")


def save_evidence(merchant_id, order_id, evidence_type, file_storage):
    """Save one evidence image. Returns (evidence_id, error_message)."""
    if evidence_type not in EVIDENCE_TYPES:
        return None, "Invalid evidence type."

    order = get_order(merchant_id, order_id)
    if order is None:
        return None, "Order not found."

    if file_storage is None or not file_storage.filename:
        return None, "No file selected."

    header = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    kind = detect_image_type(header)
    if kind is None:
        return None, "Only JPEG and PNG images are allowed."

    folder = UPLOAD_ROOT / str(order["_id"])
    folder.mkdir(parents=True, exist_ok=True)

    stored_name = secrets.token_hex(16) + ALLOWED_TYPES[kind]
    path = folder / stored_name
    file_storage.save(path)

    doc = {
        "order_id": order["_id"],
        "merchant_id": order["merchant_id"],
        "evidence_type": evidence_type,
        "original_filename": secure_filename(file_storage.filename),
        "stored_name": stored_name,
        "file_type": kind,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_of_file(path),
        "uploaded_at": datetime.now(timezone.utc),
    }
    result = get_db().evidence.insert_one(doc)
    return result.inserted_id, None


def list_evidence(merchant_id, order_id):
    """Return all evidence records for an order the merchant owns."""
    order = get_order(merchant_id, order_id)
    if order is None:
        return []
    cursor = get_db().evidence.find({"order_id": order["_id"]}).sort("uploaded_at", 1)
    return list(cursor)


def readiness(evidence_list):
    """Return (missing_types, label). Label is READY, PARTIAL or INSUFFICIENT."""
    have = {e["evidence_type"] for e in evidence_list}
    missing = [t for t in EVIDENCE_TYPES if t not in have]
    if not missing:
        label = "READY"
    elif len(missing) == len(EVIDENCE_TYPES):
        label = "INSUFFICIENT"
    else:
        label = "PARTIAL"
    return missing, label

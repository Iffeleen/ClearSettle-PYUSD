import shutil

from app.db import get_db
from app.services.evidence_service import UPLOAD_ROOT
from app.services.order_service import get_order


def delete_order(merchant_id, order_id):
    """Permanently delete an order the merchant owns, with its evidence
    records, uploaded evidence files and disputes. Returns True if deleted."""
    order = get_order(merchant_id, order_id)  # also checks ownership
    if order is None:
        return False
    oid = order["_id"]
    db = get_db()
    db.orders.delete_one({"_id": oid, "merchant_id": order["merchant_id"]})
    db.evidence.delete_many({"order_id": oid})
    db.disputes.delete_many({"order_id": oid})

    # Remove the uploaded files, but only the folder named after this order.
    folder = (UPLOAD_ROOT / str(oid)).resolve()
    if folder.parent == UPLOAD_ROOT.resolve() and folder.is_dir():
        shutil.rmtree(folder, ignore_errors=True)
    return True

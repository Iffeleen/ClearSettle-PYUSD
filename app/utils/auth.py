from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "merchant_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped_view

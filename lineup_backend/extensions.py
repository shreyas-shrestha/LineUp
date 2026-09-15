"""Flask extensions shared across blueprints (initialised in the app factory)."""

from __future__ import annotations

from typing import Callable

from flask import current_app, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def limiter_key() -> str:
    """Rate-limit signed-in users by uid, everyone else by client IP."""
    from lineup_backend.middleware.auth import current_user

    user = current_user()
    if user and user.get("uid"):
        return f"user:{user['uid']}"
    return f"ip:{get_remote_address()}"


limiter = Limiter(key_func=limiter_key)


@limiter.request_filter
def _skip_cors_preflight() -> bool:
    return request.method == "OPTIONS"


def rate(group: str) -> Callable[[], str]:
    """Return a callable Flask-Limiter can evaluate per request from app config."""

    def _limit() -> str:
        return current_app.config["LINEUP_RATE_LIMITS"][group]

    _limit.__name__ = f"rate_{group}"
    return _limit

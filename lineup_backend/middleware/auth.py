"""Request authentication: ``Authorization: Bearer <token>`` -> ``g.user``.

Verification is lazy and cached per request so the rate limiter's key
function, ``optional_auth`` and ``require_auth`` share one lookup. Decorators:

* ``require_auth``            401 without a valid token; sets ``g.user``.
* ``require_role("barber")``  ...and 403 unless the user has that role
                              (a user with no role yet gets 403 ``onboarding_required``).
* ``optional_auth``           public reads that personalise when a token is present.

Ownership helpers raise 403 when the token's uid does not match the resource.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import current_app, g, request

from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.services.auth import AuthError

_RESOLVED = "_lineup_auth_resolved"


def bearer_token() -> Optional[str]:
    header = request.headers.get("Authorization", "")
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
        return parts[1]
    return None


def _resolve() -> None:
    """Verify the bearer token once per request; store the outcome on ``g``."""
    if getattr(g, _RESOLVED, False):
        return
    setattr(g, _RESOLVED, True)
    g.user = None
    g.principal = None
    g.auth_error = None
    token = bearer_token()
    if not token:
        return
    svc = current_app.extensions["lineup"]
    try:
        principal = svc.auth.verify(token)
        user, _created = svc.auth.get_or_create_user(principal)
    except AuthError as exc:
        g.auth_error = exc
        return
    g.principal = principal
    g.user = user


def current_user() -> Optional[Dict[str, Any]]:
    """The signed-in user's document or None. Never raises (used by the limiter)."""
    try:
        _resolve()
    except Exception:  # noqa: BLE001 - key functions must not fail the request
        return None
    return getattr(g, "user", None)


def _raise_auth_error(exc: AuthError) -> None:
    raise ApiError(exc.message, exc.status, code=exc.code)


def authenticate(required: bool = True) -> Optional[Dict[str, Any]]:
    """Resolve the caller. With ``required`` a missing/invalid token raises 401
    (503 when auth is not configured). A bad token is rejected even when optional."""
    _resolve()
    error: Optional[AuthError] = getattr(g, "auth_error", None)
    if error is not None:
        _raise_auth_error(error)
    user = getattr(g, "user", None)
    if user is None and required:
        svc = current_app.extensions["lineup"]
        if not svc.auth.enabled:
            raise ApiError("Authentication is not configured on this server", 503, code="auth_not_configured")
        raise ApiError("Sign in to continue", 401, code="unauthorized")
    return user


def require_auth(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        authenticate(required=True)
        return view(*args, **kwargs)

    return wrapper


def optional_auth(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        authenticate(required=False)
        return view(*args, **kwargs)

    return wrapper


def require_role(*roles: str) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any):
            user = authenticate(required=True)
            role = (user or {}).get("role")
            if not role:
                raise ApiError("Finish onboarding to continue", 403, code="onboarding_required")
            if role not in roles:
                raise ApiError(f"This action requires the {' or '.join(roles)} role", 403, code="forbidden", required_role=list(roles))
            return view(*args, **kwargs)

        return wrapper

    return decorator


def assert_owner(resource_owner_uid: Optional[str], message: str = "You can only manage your own data") -> Dict[str, Any]:
    """403 unless the signed-in user is ``resource_owner_uid``. Returns the user."""
    user = authenticate(required=True)
    assert user is not None
    if not resource_owner_uid or user["uid"] != str(resource_owner_uid):
        raise ApiError(message, 403, code="forbidden")
    return user


def require_pro(feature: str) -> Dict[str, Any]:
    """402 ``pro_required`` unless the signed-in user is on the Pro plan."""
    from lineup_backend.services.billing import ProRequired

    user = authenticate(required=True)
    assert user is not None
    if user.get("plan") != "pro":
        raise ProRequired(feature)
    return user

"""Identity: who am I, onboarding (pick a role once), developer sign-in."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import clean_text, get_json_body, now_iso
from lineup_backend.middleware.auth import require_auth
from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.services.auth import Principal, dev_uid_for
from lineup_backend.services.availability import DEFAULT_SERVICES, default_availability
from lineup_backend.services.users import ROLES, entitlements, public_user

bp = Blueprint("auth", __name__, url_prefix="/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _barber_profile(user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if user.get("role") != "barber":
        return None
    return services().store.barber_profiles.get(user["uid"])


def _me_payload(user: Dict[str, Any], **extra: Any) -> Dict[str, Any]:
    payload = {
        "user": public_user(user),
        "entitlements": entitlements(user),
        "barber": _barber_profile(user),
        "auth": {"mode": services().auth.mode},
    }
    payload.update(extra)
    return payload


@bp.get("/me")
@limiter.limit(rate("read"))
@require_auth
def me():
    return jsonify(_me_payload(g.user))


@bp.post("/dev-login")
@limiter.limit(rate("auth"))
def dev_login():
    """Local sign-in without Firebase. 404 outside development/testing."""
    svc = services()
    if not svc.auth.dev_login_enabled:
        raise ApiError("Not found", 404, message="The requested resource does not exist")
    data = get_json_body()
    email = clean_text(data.get("email"), max_length=120).lower()
    if not EMAIL_RE.match(email):
        raise ApiError("A valid email is required", 400)
    name = clean_text(data.get("name"), default=email.split("@")[0], max_length=80)

    existing = svc.auth.find_by_email(email)
    uid = existing["uid"] if existing else dev_uid_for(email)
    user, created = svc.auth.get_or_create_user(Principal(uid=uid, email=email, name=name, provider="dev"))
    token, expires = svc.auth.issue_dev_token(uid, email, user["name"])
    payload = _me_payload(user, token=token, expiresAt=datetime.fromtimestamp(expires, tz=timezone.utc).isoformat(), created=created)
    return jsonify(payload)


@bp.post("/onboarding")
@limiter.limit(rate("auth"))
@require_auth
def onboarding():
    """Pick a role once. Barbers get a shop profile (id = uid), default hours and services."""
    svc = services()
    user = g.user
    data = get_json_body()
    role = clean_text(data.get("role"), max_length=20).lower()
    if role not in ROLES:
        raise ApiError("role must be 'client' or 'barber'", 400)
    if role == "barber" and svc.config.consumer_only:
        raise ApiError("barber_signups_closed", 403, message="Barber accounts are not open yet")
    if user.get("role"):
        raise ApiError("already_onboarded", 409, role=user["role"], message="Your role is already set")

    display_name = clean_text(data.get("name"), default=user.get("name", ""), max_length=80)
    shop_name = clean_text(data.get("shopName"), default=f"{display_name}'s shop", max_length=120)

    def mutate(current: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not current or current.get("role"):
            return None
        patch: Dict[str, Any] = {"role": role, "onboardedAt": now_iso(), "name": display_name}
        if role == "barber":
            patch["barberProfileId"] = current["uid"]
        return patch

    updated = svc.store.users.modify(user["uid"], mutate)
    if not updated or updated.get("role") != role:
        raise ApiError("already_onboarded", 409, role=(updated or {}).get("role"), message="Your role is already set")

    if role == "barber":
        uid = user["uid"]
        profile = svc.store.barber_profiles.upsert(
            uid,
            {
                "ownerUid": uid,
                "name": shop_name,
                "phone": clean_text(data.get("phone"), max_length=40),
                "address": clean_text(data.get("address"), max_length=200),
                "bio": clean_text(data.get("bio"), max_length=500),
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            },
        )
        if not svc.store.barber_services.list(barberId=uid):
            for service in DEFAULT_SERVICES:
                svc.store.barber_services.create({**service, "barberId": uid, "createdAt": now_iso(), "default": True})
        if svc.store.barber_availability.get(uid) is None:
            svc.store.barber_availability.upsert(uid, {**default_availability(uid), "updatedAt": now_iso()})
        g.user = updated
        return jsonify({**_me_payload(updated), "barber": profile})

    g.user = updated
    return jsonify(_me_payload(updated))

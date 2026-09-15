"""User documents (``users`` collection, id = uid) and entitlement rules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from lineup_backend.pricing import CREDIT_COSTS, FREE_PORTFOLIO_LIMIT, FREE_SIGNUP_CREDITS, PRO_FEATURES

ROLES = ("client", "barber")
PLANS = ("free", "pro")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_user_doc(
    uid: str,
    email: Optional[str],
    name: Optional[str],
    photo_url: Optional[str] = None,
    role: Optional[str] = None,
    credits: int = FREE_SIGNUP_CREDITS,
    plan: str = "free",
    provider: str = "firebase",
) -> Dict[str, Any]:
    now = _now()
    return {
        "uid": uid,
        "email": (email or "").strip().lower() or None,
        "name": (name or "").strip() or (email or "").split("@")[0] or "Member",
        "photoUrl": photo_url or None,
        "role": role if role in ROLES else None,
        "provider": provider,
        "createdAt": now,
        "onboardedAt": now if role in ROLES else None,
        "credits": int(credits),
        "plan": plan if plan in PLANS else "free",
        "planUpdatedAt": now,
        "stripeCustomerId": None,
        "stripeSubscriptionId": None,
        "barberProfileId": uid if role == "barber" else None,
    }


def is_pro(user: Optional[Dict[str, Any]]) -> bool:
    return bool(user) and user.get("plan") == "pro"


def entitlements(user: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """What the caller may do right now; the frontend renders locks from this."""
    pro = is_pro(user)
    credits = int((user or {}).get("credits", 0) or 0)
    return {
        "plan": (user or {}).get("plan", "free"),
        "pro": pro,
        "credits": credits,
        "credit_costs": dict(CREDIT_COSTS),
        "features": {
            "portfolio_limit": None if pro else FREE_PORTFOLIO_LIMIT,
            **{feature: pro for feature in PRO_FEATURES if feature != "portfolio"},
        },
    }


def public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """The user as returned to its owner. Stripe ids stay server-side."""
    return {
        "uid": user.get("uid") or user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "photoUrl": user.get("photoUrl"),
        "role": user.get("role"),
        "plan": user.get("plan", "free"),
        "credits": int(user.get("credits", 0) or 0),
        "createdAt": user.get("createdAt"),
        "onboardedAt": user.get("onboardedAt"),
        "barberProfileId": user.get("barberProfileId"),
        "provider": user.get("provider", "firebase"),
        "billing": {
            "customer": bool(user.get("stripeCustomerId")),
            "subscription": bool(user.get("stripeSubscriptionId")),
        },
    }

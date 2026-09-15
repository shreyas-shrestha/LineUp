"""Single source of truth for what things cost.

Credits are the unit clients spend on paid third-party calls (Gemini analysis,
Replicate try-on, Google Places search). Barbers pay a flat monthly Pro plan.
Stripe price ids come from the environment (``STRIPE_PRICE_<PACKID>``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Credits charged per metered action. Search is free when served from cache.
CREDIT_COSTS: Dict[str, int] = {"analysis": 1, "tryon": 3, "barber_search": 1}

# Credits every new account starts with.
FREE_SIGNUP_CREDITS = 3

# One-time credit packs (Stripe Checkout in ``payment`` mode).
CREDIT_PACKS: List[Dict[str, Any]] = [
    {"id": "starter", "name": "Starter", "credits": 10, "price_cents": 499},
    {"id": "plus", "name": "Plus", "credits": 30, "price_cents": 999, "highlight": True},
    {"id": "studio", "name": "Studio", "credits": 100, "price_cents": 2499},
]

# Barber Pro subscription (Stripe Checkout in ``subscription`` mode).
BARBER_PRO: Dict[str, Any] = {
    "id": "barber_pro",
    "name": "Barber Pro",
    "price_cents": 1900,
    "interval": "month",
    "features": [
        "Unlimited portfolio photos",
        "Prepaid packages for regulars",
        "Client notes and visit history",
        "Revenue and peak-time analytics",
    ],
}

# Features locked behind Barber Pro and the free-tier limit where one applies.
FREE_PORTFOLIO_LIMIT = 6
PRO_FEATURES = ("portfolio", "packages", "clients", "client_history", "client_notes", "analytics")

# What each action roughly costs us at the provider, in USD, for margin reporting.
ESTIMATED_PROVIDER_COST_USD: Dict[str, float] = {"analysis": 0.002, "tryon": 0.045, "barber_search": 0.049}

CURRENCY = "usd"


def pack_by_id(pack_id: Optional[str]) -> Optional[Dict[str, Any]]:
    return next((pack for pack in CREDIT_PACKS if pack["id"] == pack_id), None)


def credit_cost(action: str) -> int:
    return int(CREDIT_COSTS.get(action, 0))


def provider_cost(action: str) -> float:
    return float(ESTIMATED_PROVIDER_COST_USD.get(action, 0.0))


def pricing_payload(price_ids: Optional[Dict[str, Optional[str]]] = None, stripe_configured: bool = False) -> Dict[str, Any]:
    """Public ``GET /billing/pricing`` body. Never includes Stripe secrets."""
    price_ids = price_ids or {}
    packs = []
    for pack in CREDIT_PACKS:
        packs.append({**pack, "currency": CURRENCY, "purchasable": stripe_configured and bool(price_ids.get(pack["id"]))})
    pro = {**BARBER_PRO, "currency": CURRENCY, "purchasable": stripe_configured and bool(price_ids.get("barber_pro"))}
    return {
        "currency": CURRENCY,
        "credit_costs": dict(CREDIT_COSTS),
        "free_signup_credits": FREE_SIGNUP_CREDITS,
        "credit_packs": packs,
        "barber_pro": pro,
        "free_portfolio_limit": FREE_PORTFOLIO_LIMIT,
        "pro_features": list(PRO_FEATURES),
        "stripe_configured": stripe_configured,
    }

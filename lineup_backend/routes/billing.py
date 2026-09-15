"""Credits, plans, Stripe Checkout / portal / webhooks, developer grants."""

from __future__ import annotations

from functools import wraps
from typing import Any, Dict

from flask import Blueprint, g, jsonify, request

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import clean_text, get_json_body, now_iso, to_int
from lineup_backend.middleware.auth import require_auth, require_role
from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.pricing import pack_by_id, pricing_payload
from lineup_backend.services.stripe_events import apply_stripe_event
from lineup_backend.services.stripe_gateway import StripeError, StripeNotConfigured, StripeSignatureError
from lineup_backend.services.users import entitlements, is_pro

bp = Blueprint("billing", __name__, url_prefix="/billing")


def _frontend_base() -> str:
    return services().config.frontend_url.rstrip("/")


def _stripe_or_503():
    svc = services()
    if not svc.stripe.available:
        raise ApiError("stripe_not_configured", 503, message="Payments are not set up on this server yet")
    return svc


@bp.get("/pricing")
@limiter.limit(rate("health"))
def pricing():
    svc = services()
    return jsonify(pricing_payload(svc.stripe.price_ids, svc.stripe.available))


@bp.get("/me")
@limiter.limit(rate("read"))
@require_auth
def billing_me():
    svc = services()
    user = g.user
    return jsonify(
        {
            "credits": int(user.get("credits", 0) or 0),
            "plan": user.get("plan", "free"),
            "pro": is_pro(user),
            "entitlements": entitlements(user),
            "usage": svc.ledger.summary(user["uid"]),
            "stripe": {
                "configured": svc.stripe.available,
                "customer": bool(user.get("stripeCustomerId")),
                "subscription": bool(user.get("stripeSubscriptionId")),
            },
            "dev": {"grant": svc.auth.dev_login_enabled, "activatePro": svc.auth.dev_login_enabled},
        }
    )


@bp.get("/usage")
@limiter.limit(rate("read"))
@require_auth
def usage():
    limit = to_int(request.args.get("limit"), 50, minimum=1)
    events = services().ledger.usage(g.user["uid"], limit)
    return jsonify({"events": events, "count": len(events), "credits": int(g.user.get("credits", 0) or 0)})


@bp.post("/checkout")
@limiter.limit(rate("billing"))
@require_auth
def checkout():
    svc = _stripe_or_503()
    user = g.user
    data = get_json_body()
    plan = clean_text(data.get("plan"), max_length=40)
    pack_id = clean_text(data.get("packId"), max_length=40)

    if plan == "barber_pro":
        if user.get("role") != "barber":
            raise ApiError("Barber Pro is for barber accounts", 403, code="forbidden")
        if is_pro(user):
            raise ApiError("already_pro", 409, message="You are already on Barber Pro")
        price_key, mode, metadata = "barber_pro", "subscription", {"plan": "barber_pro"}
    elif pack_id:
        pack = pack_by_id(pack_id)
        if not pack:
            raise ApiError("unknown_pack", 400, message=f"No credit pack named {pack_id!r}")
        price_key, mode, metadata = pack_id, "payment", {"packId": pack_id, "credits": str(pack["credits"])}
    elif plan:
        raise ApiError("unknown_plan", 400, message=f"No plan named {plan!r}")
    else:
        raise ApiError("Send {packId} or {plan: 'barber_pro'}", 400)

    price_id = svc.stripe.price_id(price_key)
    if not price_id:
        raise ApiError("price_not_configured", 503, item=price_key, message="This item has no Stripe price configured")

    try:
        customer_id = svc.stripe.ensure_customer(user)
        if customer_id != user.get("stripeCustomerId"):
            svc.store.users.update(user["uid"], {"stripeCustomerId": customer_id})
        base = _frontend_base()
        session = svc.stripe.create_checkout(
            mode=mode,
            price_id=price_id,
            uid=user["uid"],
            customer_id=customer_id,
            success_url=f"{base}/#/account?checkout=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base}/#/account?checkout=cancel",
            metadata=metadata,
        )
    except StripeNotConfigured:
        raise ApiError("stripe_not_configured", 503, message="Payments are not set up on this server yet") from None
    except StripeError as exc:
        raise ApiError("stripe_error", 502, message=str(exc)) from None
    return jsonify({"url": session["url"], "sessionId": session["id"], "mode": mode})


@bp.post("/portal")
@limiter.limit(rate("billing"))
@require_auth
def portal():
    svc = _stripe_or_503()
    customer_id = g.user.get("stripeCustomerId")
    if not customer_id:
        raise ApiError("no_billing_account", 400, message="Buy something first; then you can manage billing here")
    try:
        session = svc.stripe.create_portal(customer_id, f"{_frontend_base()}/#/account")
    except StripeError as exc:
        raise ApiError("stripe_error", 502, message=str(exc)) from None
    return jsonify({"url": session["url"]})


@bp.post("/webhook")
@limiter.limit(rate("webhook"))
def webhook():
    """Stripe -> us. Signature-verified; idempotent by event id."""
    svc = services()
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature")
    try:
        event = svc.stripe.parse_event(payload, signature)
    except StripeNotConfigured:
        raise ApiError("stripe_not_configured", 503, message="STRIPE_WEBHOOK_SECRET is not set") from None
    except StripeSignatureError as exc:
        raise ApiError("invalid_signature", 400, message=str(exc)) from None

    event_id = clean_text(event.get("id"), max_length=120)
    if not event_id:
        raise ApiError("invalid_event", 400, message="Event has no id")
    # Claim the id before doing any work: a Stripe retry or a second worker
    # delivering the same event must not both reach the ledger.
    claimed = svc.store.stripe_events.claim(event_id, {"type": event.get("type"), "receivedAt": now_iso(), "status": "processing"})
    if not claimed:
        return jsonify({"received": True, "duplicate": True, "id": event_id})

    try:
        result: Dict[str, Any] = apply_stripe_event(svc.store, svc.ledger, event)
    except Exception:
        # Release the claim so Stripe's retry can try again.
        svc.store.stripe_events.delete(event_id)
        raise
    svc.store.stripe_events.update(event_id, {"status": "done", "processedAt": now_iso(), "result": result})
    return jsonify({"received": True, "duplicate": False, "id": event_id, **result})


# -- developer helpers (404 in production) -----------------------------------


def dev_only_route(view: Any) -> Any:
    """404 the route in production, before any auth or role check runs.

    Ordered above ``require_auth``/``require_role`` so a production probe cannot
    tell a dev-only route from a path that never existed.
    """

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not services().auth.dev_login_enabled:
            raise ApiError("Not found", 404, message="The requested resource does not exist")
        return view(*args, **kwargs)

    return wrapper


@bp.post("/dev-grant")
@limiter.limit(rate("billing"))
@dev_only_route
@require_auth
def dev_grant():
    data = get_json_body(required=False)
    amount = to_int(data.get("credits", 10), 10, minimum=1)
    if amount > 1000:
        raise ApiError("credits must be between 1 and 1000", 400)
    event = services().ledger.grant(g.user["uid"], amount, "dev_grant")
    return jsonify({"success": True, "granted": amount, "credits": event["balance_after"], "event": event})


@bp.post("/dev-activate-pro")
@limiter.limit(rate("billing"))
@dev_only_route
@require_role("barber")
def dev_activate_pro():
    data = get_json_body(required=False)
    active = data.get("active", True)
    plan = "pro" if active not in (False, "false", 0, "0") else "free"
    user = services().ledger.set_plan(g.user["uid"], plan, subscription_id=("dev_sub" if plan == "pro" else None), reason="dev_toggle")
    return jsonify({"success": True, "plan": user["plan"], "entitlements": entitlements(user)})

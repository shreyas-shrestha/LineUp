"""Apply verified Stripe webhook events to users and the ledger."""

from __future__ import annotations

from typing import Any, Dict, Optional

from lineup_backend.pricing import pack_by_id
from lineup_backend.services.billing import Ledger
from lineup_backend.storage.base import Store

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def _metadata(obj: Dict[str, Any]) -> Dict[str, Any]:
    meta = obj.get("metadata")
    return meta if isinstance(meta, dict) else {}


def _uid_for(store: Store, *, subscription_id: Optional[str], customer_id: Optional[str], metadata: Dict[str, Any]) -> Optional[str]:
    if metadata.get("uid"):
        return str(metadata["uid"])
    if subscription_id:
        user = store.users.find_one(stripeSubscriptionId=subscription_id)
        if user:
            return user["uid"]
    if customer_id:
        user = store.users.find_one(stripeCustomerId=customer_id)
        if user:
            return user["uid"]
    return None


def apply_stripe_event(store: Store, ledger: Ledger, event: Dict[str, Any]) -> Dict[str, Any]:
    """Return ``{"handled": bool, "action": ..., ...}``; never raises for unknown shapes."""
    event_type = str(event.get("type") or "")
    obj = (event.get("data") or {}).get("object") or {}
    if not isinstance(obj, dict):
        return {"handled": False, "reason": "malformed"}
    metadata = _metadata(obj)

    if event_type == "checkout.session.completed":
        uid = obj.get("client_reference_id") or metadata.get("uid")
        if not uid:
            return {"handled": False, "reason": "no_uid"}
        uid = str(uid)
        if store.users.get(uid) is None:
            return {"handled": False, "reason": "unknown_user", "uid": uid}
        customer_id = obj.get("customer")
        if customer_id:
            store.users.update(uid, {"stripeCustomerId": str(customer_id)})
        # Stripe sends this event for unpaid sessions too (async payment methods,
        # `payment_status: "unpaid"`); only a settled one may grant anything.
        payment_status = obj.get("payment_status")
        if payment_status not in (None, "paid", "no_payment_required"):
            return {"handled": False, "reason": "not_paid", "uid": uid, "payment_status": payment_status}
        if obj.get("mode") == "subscription":
            subscription_id = obj.get("subscription")
            ledger.set_plan(uid, "pro", subscription_id=str(subscription_id) if subscription_id else None, customer_id=customer_id, reason="checkout")
            return {"handled": True, "action": "activate_pro", "uid": uid}
        pack = pack_by_id(metadata.get("packId"))
        credits = int(pack["credits"]) if pack else int(metadata.get("credits") or 0)
        if credits <= 0:
            return {"handled": False, "reason": "unknown_pack", "uid": uid}
        ledger.grant(
            uid,
            credits,
            "purchase",
            meta={"packId": metadata.get("packId"), "session": obj.get("id"), "amount_total": obj.get("amount_total"), "currency": obj.get("currency")},
        )
        return {"handled": True, "action": "grant_credits", "uid": uid, "credits": credits}

    if event_type == "invoice.paid":
        details = obj.get("subscription_details") or {}
        sub_meta = details.get("metadata") if isinstance(details, dict) else None
        subscription_id = obj.get("subscription")
        uid = _uid_for(store, subscription_id=subscription_id, customer_id=obj.get("customer"), metadata=sub_meta if isinstance(sub_meta, dict) else metadata)
        if not uid or store.users.get(uid) is None:
            return {"handled": False, "reason": "unknown_user"}
        ledger.set_plan(uid, "pro", subscription_id=str(subscription_id) if subscription_id else None, customer_id=obj.get("customer"), reason="invoice_paid")
        return {"handled": True, "action": "renew_pro", "uid": uid}

    if event_type in ("customer.subscription.deleted", "customer.subscription.updated"):
        subscription_id = obj.get("id")
        uid = _uid_for(store, subscription_id=subscription_id, customer_id=obj.get("customer"), metadata=metadata)
        if not uid or store.users.get(uid) is None:
            return {"handled": False, "reason": "unknown_user"}
        status = str(obj.get("status") or "")
        active = event_type == "customer.subscription.updated" and status in ACTIVE_SUBSCRIPTION_STATUSES
        if active:
            ledger.set_plan(uid, "pro", subscription_id=str(subscription_id), customer_id=obj.get("customer"), reason=f"subscription_{status}")
            return {"handled": True, "action": "activate_pro", "uid": uid, "status": status}
        ledger.set_plan(uid, "free", subscription_id=None, reason=f"subscription_{status or 'deleted'}")
        return {"handled": True, "action": "downgrade", "uid": uid, "status": status or "deleted"}

    return {"handled": False, "reason": "ignored", "type": event_type}

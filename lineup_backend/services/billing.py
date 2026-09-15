"""Credit ledger and the ``@metered`` decorator.

Every paid provider call is charged up front (atomically, so concurrent
requests cannot overspend), then refunded when the provider failed, the
response came from cache, or (in production) the response was a mock.
``usage_events`` is append-only: charges, refunds and grants are separate rows.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from flask import current_app, g

from lineup_backend.config import AppConfig
from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.pricing import credit_cost, provider_cost
from lineup_backend.storage.base import Store

logger = logging.getLogger(__name__)

META_KEYS = ("mock", "cached", "source", "reason", "mode", "location", "haircut", "real_data")


class InsufficientCredits(ApiError):
    def __init__(self, needed: int, credits: int, action: str) -> None:
        super().__init__("insufficient_credits", 402, needed=needed, credits=credits, action=action)


class DailyCapReached(ApiError):
    def __init__(self, action: str, limit: int, retry_after: int) -> None:
        super().__init__("daily_cap_reached", 429, action=action, limit=limit, retry_after=retry_after)


class ProRequired(ApiError):
    def __init__(self, feature: str) -> None:
        super().__init__("pro_required", 402, feature=feature)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seconds_until_utc_midnight() -> int:
    now = _now()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((tomorrow - now).total_seconds()))


class Ledger:
    def __init__(self, store: Store, config: AppConfig) -> None:
        self.store = store
        self.config = config

    # -- balances ----------------------------------------------------------

    def user(self, uid: str) -> Optional[Dict[str, Any]]:
        return self.store.users.get(uid)

    def balance(self, uid: str) -> int:
        user = self.user(uid)
        return int((user or {}).get("credits", 0) or 0)

    def _event(self, uid: str, kind: str, action: str, amount: int, delta: int, balance_after: int, **extra: Any) -> Dict[str, Any]:
        record = {
            "uid": uid,
            "kind": kind,
            "action": action,
            "credits": int(amount),
            "delta": int(delta),
            "balance_after": int(balance_after),
            "provider_cost_estimate": provider_cost(action) if kind == "charge" else 0.0,
            "ok": True,
            "ts": _now().isoformat(),
            # Denormalised so today_count() filters instead of scanning the
            # user's whole append-only history on every metered request.
            "day": _now().strftime("%Y-%m-%d"),
            "meta": extra.pop("meta", None) or {},
        }
        record.update(extra)
        return self.store.usage_events.create(record)

    # -- charges -----------------------------------------------------------

    def charge(self, uid: str, action: str, meta: Optional[Dict[str, Any]] = None, cost: Optional[int] = None) -> Dict[str, Any]:
        """Deduct the action's cost atomically; raise 402 when the balance is short."""
        amount = credit_cost(action) if cost is None else int(cost)
        if amount <= 0:
            return self._event(uid, "charge", action, 0, 0, self.balance(uid), meta=meta, free=True)

        def mutate(current: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            if current is None:
                raise InsufficientCredits(amount, 0, action)
            credits = int(current.get("credits", 0) or 0)
            if credits < amount:
                raise InsufficientCredits(amount, credits, action)
            return {"credits": credits - amount}

        user = self.store.users.modify(uid, mutate)
        return self._event(uid, "charge", action, amount, -amount, int(user["credits"]), meta=meta)

    def settle(self, event_id: str, meta: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Confirm a charge succeeded (attaches provider metadata)."""
        event = self.store.usage_events.get(event_id)
        if not event:
            return None
        merged = dict(event.get("meta") or {})
        merged.update(meta or {})
        return self.store.usage_events.update(event_id, {"ok": True, "meta": merged})

    def refund(self, event_id: str, reason: str) -> Optional[Dict[str, Any]]:
        """Give a charge back (provider failure, cache hit, mock).

        The charge is claimed atomically first, so two concurrent refunds of the
        same event cannot both credit the balance. A crash after the claim but
        before the balance write leaves the event in ``refunding``, which is
        visible in the usage feed rather than silently swallowed.
        """
        claimed = False

        def claim(current: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            nonlocal claimed
            if not current or current.get("kind") != "charge" or current.get("refunded") or current.get("refunding"):
                return None
            claimed = True
            return {"ok": False, "refunding": True, "refund_reason": reason}

        event = self.store.usage_events.modify(event_id, claim)
        if not claimed:
            return event
        amount = int((event or {}).get("credits", 0) or 0)
        if amount <= 0:
            return self.store.usage_events.update(event_id, {"refunding": False, "refunded": True})
        user = self.store.users.modify(event["uid"], lambda cur: {"credits": int((cur or {}).get("credits", 0) or 0) + amount})
        self.store.usage_events.update(event_id, {"refunding": False, "refunded": True})
        return self._event(event["uid"], "refund", event["action"], amount, amount, int(user["credits"]), ref=event_id, reason=reason)

    # -- grants ------------------------------------------------------------

    def grant(self, uid: str, credits: int, reason: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        amount = int(credits)
        if amount <= 0:
            raise ApiError("credits must be a positive integer", 400)

        def mutate(current: Optional[Dict[str, Any]]) -> Dict[str, Any]:
            if current is None:
                raise ApiError("User not found", 404)
            return {"credits": int(current.get("credits", 0) or 0) + amount}

        user = self.store.users.modify(uid, mutate)
        return self._event(uid, "grant", "grant", amount, amount, int(user["credits"]), reason=reason, meta=meta)

    def record_signup(self, uid: str, credits: int) -> Optional[Dict[str, Any]]:
        if credits <= 0:
            return None
        return self._event(uid, "grant", "grant", credits, credits, credits, reason="signup_bonus")

    def set_plan(self, uid: str, plan: str, subscription_id: Optional[str] = None, customer_id: Optional[str] = None, reason: str = "") -> Optional[Dict[str, Any]]:
        def mutate(current: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if current is None:
                return None
            patch: Dict[str, Any] = {"plan": plan, "planUpdatedAt": _now().isoformat()}
            if subscription_id is not None or plan == "free":
                patch["stripeSubscriptionId"] = subscription_id
            if customer_id:
                patch["stripeCustomerId"] = customer_id
            return patch

        user = self.store.users.modify(uid, mutate)
        if user is not None:
            self._event(uid, "plan", plan, 0, 0, int(user.get("credits", 0) or 0), reason=reason)
        return user

    # -- daily caps --------------------------------------------------------

    def today_count(self, uid: str, action: str) -> int:
        today = _now().strftime("%Y-%m-%d")
        events = self.store.usage_events.list(uid=uid, action=action, kind="charge", day=today)
        return sum(1 for e in events if e.get("ok"))

    def check_daily_cap(self, uid: str, action: str) -> None:
        limit = int(self.config.daily_caps.get(action, 0) or 0)
        if limit > 0 and self.today_count(uid, action) >= limit:
            raise DailyCapReached(action, limit, _seconds_until_utc_midnight())

    # -- reporting ---------------------------------------------------------

    def usage(self, uid: str, limit: int = 50) -> List[Dict[str, Any]]:
        events = self.store.usage_events.list(uid=uid)
        events.sort(key=lambda e: e.get("ts", ""), reverse=True)
        return events[: max(1, min(int(limit), 500))]

    def summary(self, uid: str) -> Dict[str, Any]:
        today = _now().strftime("%Y-%m-%d")
        events = self.store.usage_events.list(uid=uid)
        charges = [e for e in events if e.get("kind") == "charge" and e.get("ok")]
        today_by_action: Dict[str, int] = {}
        for event in charges:
            if str(event.get("ts", "")).startswith(today):
                today_by_action[event["action"]] = today_by_action.get(event["action"], 0) + 1
        caps = {action: int(limit) for action, limit in self.config.daily_caps.items()}
        return {
            "credits_spent_total": sum(int(e.get("credits", 0) or 0) for e in charges),
            "credits_purchased_total": sum(int(e.get("credits", 0) or 0) for e in events if e.get("kind") == "grant" and e.get("reason") == "purchase"),
            "actions_total": {action: sum(1 for e in charges if e.get("action") == action) for action in caps},
            "today": {action: today_by_action.get(action, 0) for action in caps},
            "daily_caps": caps,
            "provider_cost_estimate_usd": round(sum(float(e.get("provider_cost_estimate", 0) or 0) for e in charges), 4),
        }


# -- decorator ---------------------------------------------------------------


def _response_json(response: Any) -> Optional[Dict[str, Any]]:
    try:
        if getattr(response, "is_json", False):
            data = response.get_json(silent=True)
            return data if isinstance(data, dict) else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _annotate(response: Any, billing: Dict[str, Any]) -> Any:
    data = _response_json(response)
    if data is None:
        return response
    data["billing"] = billing
    response.set_data(current_app.json.dumps(data))
    return response


def metered(action: str, free_when: Optional[Callable[[], bool]] = None) -> Callable:
    """Charge ``action`` for the signed-in user around the wrapped view.

    ``free_when`` runs before charging: when it returns True (cache hit,
    provider not configured in production) nothing is charged. When the view
    raises, returns an error status, or returns a body marked ``cached`` (or
    ``mock`` while mock metering is off) the charge is refunded. Routes with
    optional auth are simply not metered for anonymous callers.
    """

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any):
            user = getattr(g, "user", None)
            if not user:
                return view(*args, **kwargs)
            uid = user["uid"]
            svc = current_app.extensions["lineup"]
            ledger: Ledger = svc.ledger
            if free_when is not None and free_when():
                response = view(*args, **kwargs)
                return _annotate(response, {"action": action, "charged": 0, "credits": ledger.balance(uid), "free": True})

            ledger.check_daily_cap(uid, action)
            event = ledger.charge(uid, action)
            try:
                response = view(*args, **kwargs)
            except Exception:
                ledger.refund(event["id"], "error")
                raise

            status = getattr(response, "status_code", 200)
            data = _response_json(response) or {}
            refund_reason: Optional[str] = None
            reason = str(data.get("reason") or "")
            if status >= 400:
                refund_reason = "error"
            elif data.get("cached"):
                refund_reason = "cached"
            elif reason.endswith("_error"):
                refund_reason = "provider_error"
            elif reason == "daily_quota_reached":
                refund_reason = "server_budget"
            elif data.get("mock") and not svc.config.charge_for_mock:
                refund_reason = "mock"

            meta = {key: data[key] for key in META_KEYS if key in data}
            if refund_reason:
                ledger.refund(event["id"], refund_reason)
                charged = 0
            else:
                ledger.settle(event["id"], meta)
                charged = int(event.get("credits", 0) or 0)
            billing = {"action": action, "charged": charged, "credits": ledger.balance(uid), "event_id": event["id"]}
            if refund_reason:
                billing["refunded"] = refund_reason
            return _annotate(response, billing)

        return wrapper

    return decorator

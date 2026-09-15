"""Stripe behind a four-method interface so tests can inject a fake.

``StripeGateway`` never imports ``stripe`` itself; ``RealStripeClient`` does,
and only when a secret key is configured.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)


class StripeError(Exception):
    """Any Stripe failure the route should report as 502."""


class StripeSignatureError(StripeError):
    """Webhook payload did not verify against STRIPE_WEBHOOK_SECRET."""


class StripeNotConfigured(StripeError):
    """No secret key / webhook secret / price id."""


class StripeClient(Protocol):
    def create_customer(self, email: Optional[str], name: Optional[str], metadata: Dict[str, str]) -> str: ...

    def create_checkout_session(self, params: Dict[str, Any]) -> Dict[str, Any]: ...

    def create_portal_session(self, customer_id: str, return_url: str) -> Dict[str, Any]: ...

    def construct_event(self, payload: bytes, signature: str, secret: str) -> Dict[str, Any]: ...


def _to_plain(obj: Any) -> Any:
    """Turn Stripe objects into plain dicts/lists so handlers never touch the SDK types.

    A ``StripeObject`` is not a ``dict`` (stripe>=8 removed that), and it raises
    on ``.get``, so every branch below has to run before the dict/list ones.
    The conversion helper moved between releases, hence the three names.
    """
    for name in ("to_dict_recursive", "_to_dict_recursive", "to_dict"):
        convert = getattr(obj, name, None)
        if callable(convert):
            # to_dict() is shallow on some releases; recurse over what comes back.
            return _to_plain(convert())
    if isinstance(obj, dict):
        return {key: _to_plain(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain(item) for item in obj]
    return obj


class RealStripeClient:
    def __init__(self, api_key: str) -> None:
        import stripe

        self._stripe = stripe
        self._api_key = api_key

    def _wrap(self, func: Any, **params: Any) -> Any:
        try:
            return _to_plain(func(api_key=self._api_key, **params))
        except Exception as exc:  # noqa: BLE001
            logger.error("Stripe call failed: %s: %s", type(exc).__name__, exc)
            raise StripeError(str(exc)) from exc

    def create_customer(self, email: Optional[str], name: Optional[str], metadata: Dict[str, str]) -> str:
        customer = self._wrap(self._stripe.Customer.create, email=email, name=name, metadata=metadata)
        return str(customer["id"])

    def create_checkout_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self._wrap(self._stripe.checkout.Session.create, **params)

    def create_portal_session(self, customer_id: str, return_url: str) -> Dict[str, Any]:
        return self._wrap(self._stripe.billing_portal.Session.create, customer=customer_id, return_url=return_url)

    def construct_event(self, payload: bytes, signature: str, secret: str) -> Dict[str, Any]:
        try:
            event = self._stripe.Webhook.construct_event(payload, signature, secret)
        except self._stripe.SignatureVerificationError as exc:
            raise StripeSignatureError(str(exc)) from exc
        except ValueError as exc:
            raise StripeSignatureError(f"Invalid payload: {exc}") from exc
        return _to_plain(event)


class StripeGateway:
    def __init__(
        self,
        secret_key: Optional[str],
        webhook_secret: Optional[str],
        price_ids: Dict[str, Optional[str]],
        client: Optional[StripeClient] = None,
    ) -> None:
        self.webhook_secret = webhook_secret
        self.price_ids = dict(price_ids)
        self._client: Optional[StripeClient] = client
        if client is None and secret_key:
            try:
                self._client = RealStripeClient(secret_key)
                logger.info("Stripe configured")
            except Exception as exc:  # noqa: BLE001
                logger.error("Stripe unavailable (%s); billing routes return 503", type(exc).__name__)
        elif client is None:
            logger.warning("STRIPE_SECRET_KEY not set: checkout/portal return 503 stripe_not_configured")

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def webhook_configured(self) -> bool:
        return self.available and bool(self.webhook_secret)

    def price_id(self, key: str) -> Optional[str]:
        return self.price_ids.get(key) or None

    def _require(self) -> StripeClient:
        if self._client is None:
            raise StripeNotConfigured("Stripe is not configured")
        return self._client

    def ensure_customer(self, user: Dict[str, Any]) -> str:
        existing = user.get("stripeCustomerId")
        if existing:
            return str(existing)
        return self._require().create_customer(user.get("email"), user.get("name"), {"uid": str(user.get("uid") or user.get("id"))})

    def create_checkout(
        self,
        *,
        mode: str,
        price_id: str,
        uid: str,
        customer_id: Optional[str],
        success_url: str,
        cancel_url: str,
        metadata: Dict[str, str],
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "mode": mode,
            "line_items": [{"price": price_id, "quantity": 1}],
            "client_reference_id": uid,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"uid": uid, **metadata},
            "allow_promotion_codes": True,
        }
        if customer_id:
            params["customer"] = customer_id
        if mode == "subscription":
            params["subscription_data"] = {"metadata": {"uid": uid, **metadata}}
        session = self._require().create_checkout_session(params)
        return {"id": session.get("id"), "url": session.get("url"), "mode": mode}

    def create_portal(self, customer_id: str, return_url: str) -> Dict[str, Any]:
        session = self._require().create_portal_session(customer_id, return_url)
        return {"url": session.get("url")}

    def parse_event(self, payload: bytes, signature: Optional[str]) -> Dict[str, Any]:
        if not self.webhook_configured or not self.webhook_secret:
            raise StripeNotConfigured("STRIPE_WEBHOOK_SECRET is not configured")
        if not signature:
            raise StripeSignatureError("Missing Stripe-Signature header")
        return self._require().construct_event(payload, signature, self.webhook_secret)

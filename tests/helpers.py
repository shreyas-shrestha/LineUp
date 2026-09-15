"""Test doubles and small utilities."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from PIL import Image


def tiny_image_bytes(fmt: str = "PNG", size=(8, 8)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (200, 100, 50)).save(buffer, format=fmt)
    return buffer.getvalue()


def tiny_image_b64(fmt: str = "PNG") -> str:
    return base64.b64encode(tiny_image_bytes(fmt)).decode("ascii")


def analyze_payload(image_b64: Optional[str] = None) -> Dict[str, Any]:
    return {
        "payload": {
            "contents": [
                {
                    "parts": [
                        {"text": "Analyze this person"},
                        {"inlineData": {"mimeType": "image/png", "data": image_b64 or tiny_image_b64()}},
                    ]
                }
            ]
        }
    }


class FakeResponse:
    def __init__(self, payload: Any = None, status: int = 200, headers: Optional[Dict[str, str]] = None, content: bytes = b""):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.content = content
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self) -> Any:
        return self._payload


class FakeGeminiModel:
    """Stands in for google.generativeai.GenerativeModel."""

    def __init__(self, text: Optional[str] = None, error: Optional[Exception] = None):
        self.text = text
        self.error = error
        self.calls: List[Any] = []

    def generate_content(self, parts, request_options=None):
        self.calls.append(parts)
        if self.error:
            raise self.error
        return SimpleNamespace(text=self.text)


GEMINI_ANALYSIS = {
    "analysis": {"faceShape": "square", "hairTexture": "curly", "hairColor": "black", "estimatedGender": "male", "estimatedAge": "30-35"},
    "recommendations": [
        {"styleName": "Textured Crop", "description": "Short and textured.", "reason": "Softens a square jaw."},
        {"styleName": "Curly Fade", "description": "Tight sides, curls on top.", "reason": "Shows off texture."},
    ],
}

PLACE_ID = "ChIJN1t_tDeuEmsRUsoyG83frY4"


def make_places_http(calls: List[str]):
    """A requests.get stand-in for geocode, nearby search and details."""

    def fake_get(url, params=None, **kwargs):
        calls.append(url)
        if "geocode" in url:
            return FakeResponse({"status": "OK", "results": [{"geometry": {"location": {"lat": 33.749, "lng": -84.388}}}]})
        if "nearbysearch" in url:
            return FakeResponse(
                {
                    "status": "OK",
                    "results": [
                        {
                            "place_id": PLACE_ID,
                            "name": "Fade Kings Barbershop",
                            "rating": 4.7,
                            "user_ratings_total": 210,
                            "price_level": 2,
                            "vicinity": "1 Peachtree St",
                            "geometry": {"location": {"lat": 33.75, "lng": -84.39}},
                            "photos": [{"photo_reference": "photo-ref-123"}],
                            "opening_hours": {"open_now": True},
                        },
                        {
                            "place_id": "ChIJrTLr-GyuEmsRBfy61i59si0",
                            "name": "Classic Cuts",
                            "rating": 4.2,
                            "user_ratings_total": 40,
                            "price_level": 1,
                            "vicinity": "2 Main St",
                            "geometry": {"location": {"lat": 33.76, "lng": -84.40}},
                        },
                    ],
                }
            )
        if "details" in url:
            return FakeResponse(
                {
                    "status": "OK",
                    "result": {
                        "name": "Fade Kings Barbershop",
                        "formatted_address": "1 Peachtree St, Atlanta, GA",
                        "formatted_phone_number": "(404) 555-0100",
                        "website": "https://fadekings.example.com",
                        "rating": 4.7,
                        "user_ratings_total": 210,
                        "opening_hours": {"weekday_text": ["Monday: 9AM-6PM"]},
                        "reviews": [
                            {"author_name": "Sam", "rating": 5, "text": "Best fade in town", "time": 1700000000, "relative_time_description": "a month ago"},
                        ],
                    },
                }
            )
        raise AssertionError(f"unexpected url {url}")

    return fake_get


# --- Stripe test double ------------------------------------------------------


class FakeStripeClient:
    """Implements the four methods StripeGateway needs; records every call."""

    def __init__(self, webhook_secret: str = "whsec_test") -> None:
        self.webhook_secret = webhook_secret
        self.customers: List[Dict[str, Any]] = []
        self.sessions: List[Dict[str, Any]] = []
        self.portals: List[Dict[str, Any]] = []
        self.fail_with: Optional[Exception] = None

    def _maybe_fail(self) -> None:
        if self.fail_with is not None:
            raise self.fail_with

    def create_customer(self, email, name, metadata):
        self._maybe_fail()
        customer_id = f"cus_test_{len(self.customers) + 1}"
        self.customers.append({"id": customer_id, "email": email, "name": name, "metadata": metadata})
        return customer_id

    def create_checkout_session(self, params):
        self._maybe_fail()
        session_id = f"cs_test_{len(self.sessions) + 1}"
        self.sessions.append(params)
        return {"id": session_id, "url": f"https://checkout.stripe.test/{session_id}", **params}

    def create_portal_session(self, customer_id, return_url):
        self._maybe_fail()
        self.portals.append({"customer": customer_id, "return_url": return_url})
        return {"url": f"https://billing.stripe.test/{customer_id}"}

    def construct_event(self, payload, signature, secret):
        from lineup_backend.services.stripe_gateway import StripeSignatureError

        if signature != f"sig:{secret}":
            raise StripeSignatureError("No signatures found matching the expected signature for payload")
        return json.loads(payload)


DEFAULT_PRICES = {"starter": "price_starter", "plus": "price_plus", "studio": "price_studio", "barber_pro": "price_pro"}


def configure_fake_stripe(svc, prices: Optional[Dict[str, Optional[str]]] = None, webhook_secret: str = "whsec_test") -> FakeStripeClient:
    fake = FakeStripeClient(webhook_secret)
    svc.stripe._client = fake
    svc.stripe.webhook_secret = webhook_secret
    svc.stripe.price_ids = dict(DEFAULT_PRICES if prices is None else prices)
    return fake


def stripe_event(event_id: str, event_type: str, obj: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": event_id, "object": "event", "type": event_type, "data": {"object": obj}}


def post_webhook(client, event: Dict[str, Any], signature: str = "sig:whsec_test"):
    return client.post("/billing/webhook", data=json.dumps(event), content_type="application/json", headers={"Stripe-Signature": signature})

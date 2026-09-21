"""Shared fixtures. Every app is built with no external keys, limits off and
mock data seeded, so tests never touch the network.

Auth: the app runs in ``dev`` auth mode, so tests sign in through
``POST /auth/dev-login`` and send ``Authorization: Bearer <jwt>``. Two seeded
identities exist: ``client@lineup.dev`` (uid ``client_1``, role client) and
``barber@lineup.dev`` (uid ``barber_1``, role barber, shop "Mike's Cuts").
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from lineup_backend import create_app

DEV_SECRET = "test-secret"
CLIENT_EMAIL = "client@lineup.dev"
BARBER_EMAIL = "barber@lineup.dev"

BASE_OVERRIDES = dict(
    env="testing",
    # The suite covers the whole two-sided app; tests/test_consumer_mode.py
    # builds the shipped consumer-only configuration explicitly.
    barber_side=True,
    # Production-mode tests still run on the in-memory store.
    allow_memory_store=True,
    log_level="WARNING",
    ratelimit_enabled=False,
    seed_mock_data=True,
    gemini_api_key=None,
    google_places_api_key=None,
    replicate_api_token=None,
    cloudinary_cloud_name=None,
    cloudinary_api_key=None,
    cloudinary_api_secret=None,
    firebase_credentials=None,
    firebase_web_config=None,
    dev_secret=DEV_SECRET,
    stripe_secret_key=None,
    stripe_webhook_secret=None,
    public_url="http://api.test",
    frontend_url="http://app.test",
    max_analysis_per_day_per_user=1000,
    max_tryon_per_day_per_user=1000,
    max_barber_search_per_day_per_user=1000,
)


def make_app(**overrides):
    return create_app(**{**BASE_OVERRIDES, **overrides})


class AuthedClient:
    """A Flask test client bound to one signed-in user (adds the bearer header)."""

    def __init__(self, client, token: str, user: Dict[str, Any]) -> None:
        self.client = client
        self.token = token
        self.user = user

    @property
    def uid(self) -> str:
        return self.user["uid"]

    def _kw(self, kw: Dict[str, Any]) -> Dict[str, Any]:
        headers = dict(kw.pop("headers", None) or {})
        headers.setdefault("Authorization", f"Bearer {self.token}")
        kw["headers"] = headers
        return kw

    def get(self, *args: Any, **kw: Any):
        return self.client.get(*args, **self._kw(kw))

    def post(self, *args: Any, **kw: Any):
        return self.client.post(*args, **self._kw(kw))

    def put(self, *args: Any, **kw: Any):
        return self.client.put(*args, **self._kw(kw))

    def delete(self, *args: Any, **kw: Any):
        return self.client.delete(*args, **self._kw(kw))

    def refresh(self) -> Dict[str, Any]:
        self.user = self.get("/auth/me").get_json()["user"]
        return self.user


def login(client, email: str, name: Optional[str] = None, role: Optional[str] = None, shop_name: Optional[str] = None) -> AuthedClient:
    """Dev-login (creating the user on first use) and optionally onboard with a role."""
    response = client.post("/auth/dev-login", json={"email": email, "name": name or email.split("@")[0]})
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    authed = AuthedClient(client, data["token"], data["user"])
    if role and not data["user"].get("role"):
        body: Dict[str, Any] = {"role": role}
        if shop_name:
            body["shopName"] = shop_name
        onboarded = authed.post("/auth/onboarding", json=body)
        assert onboarded.status_code == 200, onboarded.get_json()
        authed.user = onboarded.get_json()["user"]
    return authed


@pytest.fixture
def app():
    return make_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def svc(app):
    return app.extensions["lineup"]


@pytest.fixture
def as_client(client) -> AuthedClient:
    """Seeded client account (uid client_1, 3 free credits)."""
    return login(client, CLIENT_EMAIL)


@pytest.fixture
def as_barber(client) -> AuthedClient:
    """Seeded barber account (uid barber_1, free plan)."""
    return login(client, BARBER_EMAIL)


@pytest.fixture
def as_pro_barber(client, svc) -> AuthedClient:
    """Seeded barber upgraded to Pro."""
    authed = login(client, BARBER_EMAIL)
    svc.ledger.set_plan(authed.uid, "pro", subscription_id="sub_test", reason="test")
    authed.refresh()
    return authed


@pytest.fixture
def other_client(client) -> AuthedClient:
    """A second, freshly created client account."""
    return login(client, "other@lineup.dev", name="Riley Other", role="client")

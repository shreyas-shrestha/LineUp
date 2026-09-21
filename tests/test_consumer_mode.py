"""The shipped configuration: consumer-only (LINEUP_BARBER_SIDE unset) and a
production that refuses to run on the in-memory store."""

from __future__ import annotations

import pytest

from lineup_backend import create_app
from lineup_backend.config import AppConfig
from lineup_backend.services.users import new_user_doc
from lineup_backend.storage import PersistentStoreRequired, create_store
from tests.conftest import BASE_OVERRIDES, login, make_app
from tests.helpers import analyze_payload, configure_fake_stripe, tiny_image_b64


def consumer_app(**overrides):
    return make_app(barber_side=False, **overrides)


# --- configuration -------------------------------------------------------------


def test_consumer_only_is_the_default(monkeypatch):
    monkeypatch.delenv("LINEUP_BARBER_SIDE", raising=False)
    monkeypatch.delenv("LINEUP_ALLOW_MEMORY_STORE", raising=False)
    cfg = AppConfig.from_env()
    assert cfg.barber_side is False and cfg.consumer_only is True
    assert cfg.allow_memory_store is False and cfg.require_persistent_store is True
    monkeypatch.setenv("LINEUP_BARBER_SIDE", "true")
    assert AppConfig.from_env().barber_side is True


def test_config_and_index_report_the_mode():
    client = consumer_app().test_client()
    config = client.get("/config").get_json()
    assert config["consumerOnly"] is True and config["features"]["barberSide"] is False
    endpoints = client.get("/").get_json()["endpoints"]
    assert "barbers" in endpoints and "appointments" not in endpoints and "social" not in endpoints

    two_sided = make_app().test_client()
    assert two_sided.get("/config").get_json()["consumerOnly"] is False
    assert "appointments" in two_sided.get("/").get_json()["endpoints"]


# --- accounts: no onboarding step -----------------------------------------------


def test_new_accounts_are_clients_without_onboarding():
    client = consumer_app().test_client()
    fresh = login(client, "fresh@lineup.dev", name="Fresh")
    assert fresh.user["role"] == "client" and fresh.user["onboardedAt"]
    assert fresh.user["credits"] == 3
    # Metered routes work straight away.
    assert fresh.post("/analyze", json=analyze_payload()).status_code == 200


def test_accounts_created_before_the_cut_are_promoted_to_client():
    app = consumer_app()
    svc = app.extensions["lineup"]
    svc.store.users.create(new_user_doc("dev_legacy", "legacy@lineup.dev", "Legacy", provider="dev"), doc_id="dev_legacy")
    assert svc.store.users.get("dev_legacy")["role"] is None
    authed = login(app.test_client(), "legacy@lineup.dev")
    assert authed.user["role"] == "client" and authed.user["onboardedAt"]


def test_barber_signups_are_closed():
    client = consumer_app().test_client()
    authed = login(client, "wants-a-shop@lineup.dev")
    response = authed.post("/auth/onboarding", json={"role": "barber", "shopName": "Nope"})
    assert response.status_code == 403 and response.get_json()["error"] == "barber_signups_closed"
    # Already a client, so the client path is a no-op conflict rather than a change.
    assert authed.post("/auth/onboarding", json={"role": "client"}).status_code == 409
    assert authed.get("/auth/me").get_json()["user"]["role"] == "client"


# --- the barber side is not registered ------------------------------------------


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/appointments"),
        ("POST", "/appointments"),
        ("GET", "/social"),
        ("POST", "/social/1/like"),
        ("GET", "/portfolio"),
        ("GET", "/portfolio/barber_1"),
        ("GET", "/subscription-packages"),
        ("GET", "/client-subscriptions"),
        ("GET", "/users/me/following"),
        ("GET", "/barbers/barber_1/profile"),
        ("PUT", "/barbers/barber_1/availability"),
        ("GET", "/barbers/barber_1/available-slots?date=2030-01-07"),
        ("GET", "/barbers/barber_1/services"),
        ("GET", "/barbers/barber_1/clients"),
    ],
)
def test_barber_side_routes_do_not_exist(method, path):
    app = consumer_app()
    authed = login(app.test_client(), "client@lineup.dev")
    response = authed.client.open(path, method=method, headers={"Authorization": f"Bearer {authed.token}"}, json={})
    assert response.status_code == 404, (path, response.get_json())
    assert response.get_json() == {"error": "Not found", "message": "The requested resource does not exist"}


def test_review_reading_stays_but_posting_is_gone():
    client = consumer_app().test_client()
    data = client.get("/barbers/barber_1/reviews").get_json()
    assert data["total_reviews"] == 3 and data["source"] == "local"
    authed = login(client, "client@lineup.dev")
    assert authed.post("/barbers/barber_1/reviews", json={"rating": 5}).status_code == 405


def test_consumer_routes_still_work():
    app = consumer_app()
    client = app.test_client()
    assert client.get("/barbers?location=Atlanta").get_json()["barbers"]
    assert client.get("/ai-insights").status_code == 200
    authed = login(client, "client@lineup.dev")
    tryon = authed.post("/virtual-tryon", json={"userPhoto": tiny_image_b64(), "styleDescription": "fade"})
    assert tryon.status_code == 200 and tryon.get_json()["billing"]["charged"] == 3


# --- billing: packs only -------------------------------------------------------------


def test_pricing_has_no_barber_pro():
    app = consumer_app()
    configure_fake_stripe(app.extensions["lineup"])
    data = app.test_client().get("/billing/pricing").get_json()
    assert data["barber_pro"] is None
    assert [p["id"] for p in data["credit_packs"]] == ["starter", "plus", "studio"]
    assert all(p["purchasable"] for p in data["credit_packs"])


def test_checkout_sells_packs_but_not_pro():
    app = consumer_app()
    fake = configure_fake_stripe(app.extensions["lineup"])
    authed = login(app.test_client(), "client@lineup.dev")
    response = authed.post("/billing/checkout", json={"packId": "plus"})
    assert response.status_code == 200 and response.get_json()["mode"] == "payment"
    assert fake.sessions[0]["metadata"]["packId"] == "plus"
    response = authed.post("/billing/checkout", json={"plan": "barber_pro"})
    assert response.status_code == 400 and response.get_json()["error"] == "plan_not_available"
    assert len(fake.sessions) == 1
    assert authed.get("/billing/me").get_json()["dev"] == {"grant": True, "activatePro": False}
    assert authed.post("/billing/dev-activate-pro").status_code == 404
    # The seeded barber account still cannot reach the Pro toggle.
    barber = login(app.test_client(), "barber@lineup.dev")
    assert barber.post("/billing/dev-activate-pro").status_code == 404


# --- production needs persistence ---------------------------------------------------


def test_production_refuses_the_memory_store():
    with pytest.raises(PersistentStoreRequired, match="FIREBASE_CREDENTIALS"):
        create_store(AppConfig(env="production"))
    with pytest.raises(PersistentStoreRequired, match="Firestore initialisation failed"):
        create_store(AppConfig(env="production", firebase_credentials="not json"))
    assert create_store(AppConfig(env="production", allow_memory_store=True)).kind == "memory"
    assert create_store(AppConfig(env="development")).kind == "memory"
    assert create_store(AppConfig(env="testing", firebase_credentials="not json")).kind == "memory"


def test_create_app_fails_loudly_in_production_without_firestore():
    overrides = {**BASE_OVERRIDES, "env": "production", "allow_memory_store": False}
    with pytest.raises(PersistentStoreRequired):
        create_app(**overrides)

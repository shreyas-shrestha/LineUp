import time

import jwt

from lineup_backend.pricing import FREE_SIGNUP_CREDITS
from lineup_backend.services.auth import DEV_AUDIENCE, DEV_ISSUER, dev_uid_for
from tests.conftest import DEV_SECRET, login, make_app


def _dev_jwt(uid="someone", secret=DEV_SECRET, **claims):
    now = int(time.time())
    payload = {"sub": uid, "email": "x@y.z", "name": "X", "iat": now, "exp": now + 60, "iss": DEV_ISSUER, "aud": DEV_AUDIENCE}
    payload.update(claims)
    return jwt.encode(payload, secret, algorithm="HS256")


# --- dev login ---------------------------------------------------------------


def test_dev_login_creates_user_with_signup_credits(client):
    response = client.post("/auth/dev-login", json={"email": "New.Person@Example.com", "name": "New Person"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["token"] and data["expiresAt"] and data["created"] is True
    user = data["user"]
    assert user["uid"] == dev_uid_for("new.person@example.com") and user["email"] == "new.person@example.com"
    assert user["name"] == "New Person" and user["role"] is None and user["plan"] == "free"
    assert user["credits"] == FREE_SIGNUP_CREDITS and user["provider"] == "dev"
    assert data["entitlements"]["pro"] is False and data["entitlements"]["credits"] == 3
    assert data["auth"]["mode"] == "dev" and data["barber"] is None
    # same email -> same account, no new signup bonus
    again = client.post("/auth/dev-login", json={"email": "new.person@example.com"}).get_json()
    assert again["created"] is False and again["user"]["uid"] == user["uid"] and again["user"]["credits"] == 3


def test_dev_login_maps_seeded_accounts_by_email(client):
    data = client.post("/auth/dev-login", json={"email": "barber@lineup.dev"}).get_json()
    assert data["user"]["uid"] == "barber_1" and data["user"]["role"] == "barber"
    assert data["barber"]["name"] == "Mike's Cuts" and data["barber"]["id"] == "barber_1"


def test_dev_login_validation(client):
    assert client.post("/auth/dev-login", json={"email": "not-an-email"}).status_code == 400
    assert client.post("/auth/dev-login", json={}).status_code == 400
    assert client.post("/auth/dev-login", data="x", content_type="text/plain").status_code == 400


def test_dev_login_refused_in_production():
    app = make_app(env="production", seed_mock_data=True)
    client = app.test_client()
    response = client.post("/auth/dev-login", json={"email": "a@b.co"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found", "message": "The requested resource does not exist"}
    assert client.get("/config").get_json()["auth"] == {"mode": "disabled", "devLogin": False, "firebase": None}
    assert client.get("/health").get_json()["auth_mode"] == "disabled"
    # dev billing helpers are hidden too: 404 before any auth or role check, so a
    # production probe cannot tell them apart from a path that never existed.
    for path in ("/billing/dev-grant", "/billing/dev-activate-pro"):
        response = client.post(path, json={})
        assert response.status_code == 404, path
        assert response.get_json() == {"error": "Not found", "message": "The requested resource does not exist"}


def test_protected_routes_503_when_auth_not_configured_in_production():
    client = make_app(env="production", seed_mock_data=True).test_client()
    response = client.get("/auth/me")
    assert response.status_code == 503 and response.get_json()["code"] == "auth_not_configured"
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {_dev_jwt()}"})
    assert response.status_code == 503 and response.get_json()["error"] == "Authentication is not configured on this server"
    # public reads still work
    assert client.get("/social").status_code == 200


# --- tokens ------------------------------------------------------------------


def test_me_requires_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.get_json() == {"error": "Sign in to continue", "code": "unauthorized"}


def test_bad_tokens_are_401(client, as_client):
    assert as_client.get("/auth/me").status_code == 200
    junk = client.get("/auth/me", headers={"Authorization": "Bearer junk.token.here"})
    assert junk.status_code == 401 and junk.get_json()["code"] == "invalid_token"
    wrong_secret = client.get("/auth/me", headers={"Authorization": f"Bearer {_dev_jwt(secret='other')}"})
    assert wrong_secret.status_code == 401 and wrong_secret.get_json()["code"] == "invalid_token"
    expired = client.get("/auth/me", headers={"Authorization": f"Bearer {_dev_jwt(exp=int(time.time()) - 10)}"})
    assert expired.status_code == 401 and expired.get_json()["code"] == "token_expired"
    assert client.get("/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer"}).status_code == 401
    # A bad token is rejected even on optional-auth reads (the client must refresh / sign in again).
    assert client.get("/social", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_valid_dev_token_for_unknown_uid_creates_the_user(client):
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {_dev_jwt(uid='fresh_uid')}"})
    assert response.status_code == 200
    assert response.get_json()["user"]["uid"] == "fresh_uid" and response.get_json()["user"]["credits"] == 3


# --- Firebase mode -----------------------------------------------------------


def _firebase_app(web_config=None):
    app = make_app(firebase_web_config=web_config)
    svc = app.extensions["lineup"]

    class ExpiredIdTokenError(Exception):  # same class name as firebase_admin.auth's
        pass

    def verify(token):
        if token == "good":
            return {"uid": "fb_123", "email": "Fb@Example.com", "name": "Fire Base", "picture": "https://p.example/x.png", "email_verified": True}
        if token == "expired":
            raise ExpiredIdTokenError("Token expired")
        raise ValueError("InvalidIdTokenError")

    svc.auth._verify_id_token = verify
    svc.auth.mode = "firebase"
    return app


def test_firebase_mode_verifies_id_tokens_and_creates_user():
    app = _firebase_app(web_config='{"apiKey": "pub", "authDomain": "x.firebaseapp.com", "projectId": "x", "appId": "1:2:web:3", "secret": "no"}')
    client = app.test_client()
    assert client.get("/config").get_json()["auth"] == {
        "mode": "firebase",
        "devLogin": False,
        "firebase": {"apiKey": "pub", "authDomain": "x.firebaseapp.com", "projectId": "x", "appId": "1:2:web:3"},
    }
    response = client.get("/auth/me", headers={"Authorization": "Bearer good"})
    assert response.status_code == 200
    user = response.get_json()["user"]
    assert user["uid"] == "fb_123" and user["email"] == "fb@example.com" and user["name"] == "Fire Base"
    assert user["photoUrl"] == "https://p.example/x.png" and user["credits"] == 3 and user["provider"] == "firebase"
    events = app.extensions["lineup"].ledger.usage("fb_123")
    assert [(e["kind"], e["reason"]) for e in events] == [("grant", "signup_bonus")]

    assert client.get("/auth/me", headers={"Authorization": "Bearer bad"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer bad"}).get_json()["code"] == "invalid_token"
    assert client.get("/auth/me", headers={"Authorization": "Bearer expired"}).get_json()["code"] == "token_expired"
    # dev JWTs are not accepted and dev-login is hidden
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {_dev_jwt()}"}).status_code == 401
    assert client.post("/auth/dev-login", json={"email": "a@b.co"}).status_code == 404


# --- onboarding --------------------------------------------------------------


def test_onboarding_sets_role_once(client):
    fresh = login(client, "fresh@lineup.dev", name="Fresh")
    assert fresh.user["role"] is None
    # routes that need a role say so
    response = fresh.put("/barbers/anything/availability", json={})
    assert response.status_code == 403 and response.get_json()["code"] == "onboarding_required"
    assert fresh.post("/auth/onboarding", json={"role": "admin"}).status_code == 400

    response = fresh.post("/auth/onboarding", json={"role": "client"})
    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "client" and response.get_json()["user"]["onboardedAt"]
    again = fresh.post("/auth/onboarding", json={"role": "barber"})
    assert again.status_code == 409 and again.get_json()["error"] == "already_onboarded" and again.get_json()["role"] == "client"
    assert fresh.get("/auth/me").get_json()["user"]["role"] == "client"


def test_onboarding_barber_creates_shop(client, svc):
    barber = login(client, "shop@lineup.dev", name="Sam")
    response = barber.post("/auth/onboarding", json={"role": "barber", "shopName": "Sam's Fades", "phone": "555-0100"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["user"]["role"] == "barber" and data["user"]["barberProfileId"] == barber.uid
    assert data["barber"]["name"] == "Sam's Fades" and data["barber"]["id"] == barber.uid and data["barber"]["phone"] == "555-0100"
    assert data["entitlements"]["features"]["portfolio_limit"] == 6 and data["entitlements"]["features"]["packages"] is False
    assert svc.store.barber_profiles.get(barber.uid)["ownerUid"] == barber.uid
    assert len(svc.store.barber_services.list(barberId=barber.uid)) == 3
    assert svc.store.barber_availability.get(barber.uid) is not None
    assert barber.get("/auth/me").get_json()["barber"]["name"] == "Sam's Fades"


def test_onboarding_defaults_shop_name(client):
    barber = login(client, "noname@lineup.dev", name="Jo", role="barber")
    assert client.get(f"/barbers/{barber.uid}/profile").get_json()["profile"]["name"] == "Jo's shop"


# --- roles and ownership -----------------------------------------------------


def test_role_403s(as_client, as_barber):
    response = as_client.get("/appointments?type=barber")
    assert response.status_code == 403 and response.get_json()["code"] == "forbidden"
    response = as_client.post("/portfolio", json={"image": "x"})
    assert response.status_code == 403 and response.get_json()["required_role"] == ["barber"]
    response = as_client.post("/billing/dev-activate-pro")
    assert response.status_code == 403
    assert as_barber.post("/billing/dev-activate-pro").status_code == 200


def test_ownership_403s(as_barber):
    assert as_barber.put("/barbers/barber_2/availability", json={}).status_code == 403
    assert as_barber.post("/barbers/barber_2/services", json={"name": "x"}).status_code == 403
    assert as_barber.get("/barbers/barber_2/clients").status_code == 403
    assert as_barber.post("/portfolio/barber_2", json={"image": "x"}).status_code == 403
    assert as_barber.put("/barbers/barber_2/profile", json={"name": "x"}).status_code == 403


def test_public_reads_stay_public(client):
    for path in (
        "/health",
        "/config",
        "/billing/pricing",
        "/barbers?location=Atlanta",
        "/barbers/barber_1/reviews",
        "/barbers/barber_1/available-slots?date=2030-01-07",
        "/barbers/barber_1/services",
        "/barbers/barber_1/availability",
        "/barbers/barber_1/profile",
        "/social",
        "/social/1/comments",
        "/portfolio/barber_1",
        "/subscription-packages",
        "/ai-insights",
    ):
        assert client.get(path).status_code == 200, path

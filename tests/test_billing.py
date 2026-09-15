import json

import pytest

from lineup_backend.pricing import BARBER_PRO, CREDIT_COSTS, CREDIT_PACKS, FREE_SIGNUP_CREDITS
from lineup_backend.services.billing import DailyCapReached, InsufficientCredits, Ledger
from lineup_backend.services.stripe_gateway import StripeError
from lineup_backend.storage import MemoryStore
from tests.conftest import login, make_app
from tests.helpers import FakeGeminiModel, analyze_payload, configure_fake_stripe, post_webhook, stripe_event, tiny_image_b64

# --- pricing -----------------------------------------------------------------


def test_pricing_is_public_and_complete(client):
    data = client.get("/billing/pricing").get_json()
    assert data["credit_costs"] == CREDIT_COSTS == {"analysis": 1, "tryon": 3, "barber_search": 1}
    assert data["free_signup_credits"] == FREE_SIGNUP_CREDITS == 3
    assert [p["id"] for p in data["credit_packs"]] == ["starter", "plus", "studio"]
    assert [(p["credits"], p["price_cents"]) for p in data["credit_packs"]] == [(10, 499), (30, 999), (100, 2499)]
    assert data["barber_pro"]["price_cents"] == 1900 and data["barber_pro"]["interval"] == "month"
    assert data["barber_pro"]["features"] == BARBER_PRO["features"]
    assert data["stripe_configured"] is False and all(p["purchasable"] is False for p in data["credit_packs"])
    assert data["free_portfolio_limit"] == 6


def test_pricing_marks_purchasable_when_stripe_configured(client, svc):
    configure_fake_stripe(svc, prices={"starter": "price_1", "plus": None, "studio": None, "barber_pro": "price_pro"})
    data = client.get("/billing/pricing").get_json()
    assert data["stripe_configured"] is True
    assert {p["id"]: p["purchasable"] for p in data["credit_packs"]} == {"starter": True, "plus": False, "studio": False}
    assert data["barber_pro"]["purchasable"] is True
    assert "price_1" not in json.dumps(data) and "price_pro" not in json.dumps(data)  # Stripe price ids stay server-side


# --- ledger ------------------------------------------------------------------


def _ledger(credits=3, **overrides):
    from lineup_backend.config import AppConfig
    from lineup_backend.services.users import new_user_doc

    store = MemoryStore()
    store.users.create(new_user_doc("u1", "u@x.y", "U", credits=credits), doc_id="u1")
    return Ledger(store, AppConfig(env="testing", **overrides)), store


def test_ledger_charge_refund_grant_arithmetic():
    ledger, store = _ledger(credits=5)
    charge = ledger.charge("u1", "tryon", meta={"x": 1})
    assert charge["kind"] == "charge" and charge["credits"] == 3 and charge["delta"] == -3 and charge["balance_after"] == 2
    assert charge["ok"] is True and charge["provider_cost_estimate"] > 0 and charge["meta"] == {"x": 1}
    assert ledger.balance("u1") == 2

    settled = ledger.settle(charge["id"], {"source": "replicate"})
    assert settled["meta"] == {"x": 1, "source": "replicate"}

    refund = ledger.refund(charge["id"], "provider_error")
    assert refund["kind"] == "refund" and refund["delta"] == 3 and refund["balance_after"] == 5 and refund["ref"] == charge["id"]
    assert store.usage_events.get(charge["id"])["ok"] is False and store.usage_events.get(charge["id"])["refunded"] is True
    # refunding twice is a no-op
    assert ledger.refund(charge["id"], "again")["refunded"] is True and ledger.balance("u1") == 5

    grant = ledger.grant("u1", 10, "purchase", meta={"packId": "starter"})
    assert grant["kind"] == "grant" and grant["delta"] == 10 and grant["balance_after"] == 15 and grant["reason"] == "purchase"
    with pytest.raises(Exception):
        ledger.grant("u1", 0, "nothing")
    assert ledger.balance("u1") == 15
    summary = ledger.summary("u1")
    assert summary["credits_spent_total"] == 0 and summary["credits_purchased_total"] == 10  # refunded charge not counted


def test_ledger_insufficient_credits_shape():
    ledger, _ = _ledger(credits=2)
    with pytest.raises(InsufficientCredits) as info:
        ledger.charge("u1", "tryon")
    assert info.value.status == 402
    assert info.value.payload() == {"error": "insufficient_credits", "needed": 3, "credits": 2, "action": "tryon"}
    assert ledger.balance("u1") == 2
    with pytest.raises(InsufficientCredits) as info:
        ledger.charge("ghost", "analysis")
    assert info.value.payload()["credits"] == 0


def test_ledger_daily_cap():
    ledger, _ = _ledger(credits=100, max_analysis_per_day_per_user=2)
    ledger.charge("u1", "analysis")
    ledger.charge("u1", "analysis")
    assert ledger.today_count("u1", "analysis") == 2
    with pytest.raises(DailyCapReached) as info:
        ledger.check_daily_cap("u1", "analysis")
    body = info.value.payload()
    assert info.value.status == 429 and body["error"] == "daily_cap_reached" and body["limit"] == 2 and body["action"] == "analysis"
    assert 0 < body["retry_after"] <= 86400
    # refunded charges do not count
    third = ledger.charge("u1", "analysis")
    ledger.refund(third["id"], "error")
    assert ledger.today_count("u1", "analysis") == 2
    ledger.check_daily_cap("u1", "tryon")  # other actions unaffected


def test_ledger_free_actions_cost_nothing():
    ledger, _ = _ledger(credits=1)
    event = ledger.charge("u1", "unknown_action")
    assert event["credits"] == 0 and event["free"] is True and ledger.balance("u1") == 1


# --- metering through the API ------------------------------------------------


def test_analyze_402_after_credits_run_out(as_client):
    for expected in (2, 1, 0):
        data = as_client.post("/analyze", json=analyze_payload()).get_json()
        assert data["billing"]["credits"] == expected
    response = as_client.post("/analyze", json=analyze_payload())
    assert response.status_code == 402
    assert response.get_json() == {"error": "insufficient_credits", "needed": 1, "credits": 0, "action": "analysis"}
    tryon = as_client.post("/virtual-tryon", json={"userPhoto": tiny_image_b64(), "styleDescription": "bob"})
    assert tryon.status_code == 402
    assert tryon.get_json() == {"error": "insufficient_credits", "needed": 3, "credits": 0, "action": "tryon"}


def test_refund_on_provider_failure(as_client, svc):
    svc.gemini.model = FakeGeminiModel(error=RuntimeError("upstream down"))
    data = as_client.post("/analyze", json=analyze_payload()).get_json()
    assert data["reason"] == "gemini_error"
    assert data["billing"]["charged"] == 0 and data["billing"]["refunded"] == "provider_error" and data["billing"]["credits"] == 3
    events = as_client.get("/billing/usage").get_json()["events"]
    kinds = [(e["kind"], e["action"], e["ok"]) for e in events]
    assert kinds == [("refund", "analysis", True), ("charge", "analysis", False), ("grant", "grant", True)]
    assert events[1]["refund_reason"] == "provider_error"


def test_mock_responses_are_free_when_meter_mock_is_off():
    app = make_app(meter_mock=False)
    authed = login(app.test_client(), "client@lineup.dev")
    data = authed.post("/analyze", json=analyze_payload()).get_json()
    assert data["mock"] is True
    assert data["billing"] == {"action": "analysis", "charged": 0, "credits": 3, "free": True}
    assert authed.get("/billing/usage").get_json()["count"] == 1  # only the signup grant


def test_daily_cap_via_api():
    app = make_app(max_analysis_per_day_per_user=2)
    authed = login(app.test_client(), "client@lineup.dev")
    app.extensions["lineup"].ledger.grant(authed.uid, 10, "test")
    assert authed.post("/analyze", json=analyze_payload()).status_code == 200
    assert authed.post("/analyze", json=analyze_payload()).status_code == 200
    response = authed.post("/analyze", json=analyze_payload())
    assert response.status_code == 429
    body = response.get_json()
    assert body["error"] == "daily_cap_reached" and body["limit"] == 2 and body["action"] == "analysis" and body["retry_after"] > 0
    assert authed.get("/billing/me").get_json()["credits"] == 11  # the capped call cost nothing


def test_billing_me_and_usage(as_client):
    as_client.post("/analyze", json=analyze_payload())
    me = as_client.get("/billing/me").get_json()
    assert me["credits"] == 2 and me["plan"] == "free" and me["pro"] is False
    assert me["usage"]["today"] == {"analysis": 1, "tryon": 0, "barber_search": 0}
    assert me["usage"]["daily_caps"] == {"analysis": 1000, "tryon": 1000, "barber_search": 1000}
    assert me["usage"]["credits_spent_total"] == 1 and me["stripe"] == {"configured": False, "customer": False, "subscription": False}
    assert me["entitlements"]["credit_costs"]["tryon"] == 3
    usage = as_client.get("/billing/usage?limit=1").get_json()
    assert usage["count"] == 1 and usage["events"][0]["action"] == "analysis" and usage["credits"] == 2
    assert client_unauth(as_client).get("/billing/usage").status_code == 401


def client_unauth(authed):
    return authed.client


# --- dev helpers ---------------------------------------------------------------


def test_dev_grant(as_client, client):
    assert client.post("/billing/dev-grant", json={"credits": 5}).status_code == 401
    data = as_client.post("/billing/dev-grant", json={"credits": 5}).get_json()
    assert data["granted"] == 5 and data["credits"] == 8 and data["event"]["reason"] == "dev_grant"
    assert as_client.post("/billing/dev-grant").get_json()["granted"] == 10
    assert as_client.post("/billing/dev-grant", json={"credits": 5000}).status_code == 400
    assert as_client.post("/billing/dev-grant", json={"credits": -1}).get_json()["granted"] == 10  # invalid -> default


def test_dev_activate_pro_toggle(as_barber):
    data = as_barber.post("/billing/dev-activate-pro").get_json()
    assert data["plan"] == "pro" and data["entitlements"]["pro"] is True and data["entitlements"]["features"]["portfolio_limit"] is None
    assert as_barber.get("/billing/me").get_json()["stripe"]["subscription"] is True
    data = as_barber.post("/billing/dev-activate-pro", json={"active": False}).get_json()
    assert data["plan"] == "free"


# --- checkout / portal with a fake Stripe --------------------------------------


def test_checkout_503_without_stripe(as_client):
    response = as_client.post("/billing/checkout", json={"packId": "starter"})
    assert response.status_code == 503 and response.get_json()["error"] == "stripe_not_configured"
    assert as_client.post("/billing/portal").status_code == 503


def test_checkout_credit_pack_payment_mode(as_client, svc):
    fake = configure_fake_stripe(svc)
    response = as_client.post("/billing/checkout", json={"packId": "plus"})
    assert response.status_code == 200, response.get_json()
    data = response.get_json()
    assert data == {"url": "https://checkout.stripe.test/cs_test_1", "sessionId": "cs_test_1", "mode": "payment"}
    params = fake.sessions[0]
    assert params["mode"] == "payment" and params["client_reference_id"] == "client_1"
    assert params["line_items"] == [{"price": "price_plus", "quantity": 1}]
    assert params["metadata"] == {"uid": "client_1", "packId": "plus", "credits": "30"}
    assert params["success_url"] == "http://app.test/#/account?checkout=success&session_id={CHECKOUT_SESSION_ID}"
    assert params["cancel_url"] == "http://app.test/#/account?checkout=cancel"
    assert params["customer"] == "cus_test_1" and fake.customers[0]["email"] == "client@lineup.dev"
    assert svc.store.users.get("client_1")["stripeCustomerId"] == "cus_test_1"
    # second checkout reuses the customer
    as_client.post("/billing/checkout", json={"packId": "starter"})
    assert len(fake.customers) == 1 and fake.sessions[1]["customer"] == "cus_test_1"


def test_checkout_barber_pro_subscription_mode(as_barber, as_client, svc):
    fake = configure_fake_stripe(svc)
    assert as_client.post("/billing/checkout", json={"plan": "barber_pro"}).status_code == 403
    response = as_barber.post("/billing/checkout", json={"plan": "barber_pro"})
    assert response.status_code == 200
    assert response.get_json()["mode"] == "subscription"
    params = fake.sessions[0]
    assert params["mode"] == "subscription" and params["line_items"][0]["price"] == "price_pro"
    assert params["client_reference_id"] == "barber_1" and params["metadata"]["plan"] == "barber_pro"
    assert params["subscription_data"]["metadata"] == {"uid": "barber_1", "plan": "barber_pro"}
    svc.ledger.set_plan("barber_1", "pro", subscription_id="sub_1")
    assert as_barber.post("/billing/checkout", json={"plan": "barber_pro"}).status_code == 409


def test_checkout_validation_and_errors(as_client, svc):
    fake = configure_fake_stripe(svc, prices={"starter": None, "plus": "price_plus", "studio": None, "barber_pro": None})
    assert as_client.post("/billing/checkout", json={}).status_code == 400
    assert as_client.post("/billing/checkout", json={"packId": "mega"}).get_json()["error"] == "unknown_pack"
    assert as_client.post("/billing/checkout", json={"plan": "gold"}).get_json()["error"] == "unknown_plan"
    response = as_client.post("/billing/checkout", json={"packId": "starter"})
    assert response.status_code == 503 and response.get_json() == {"error": "price_not_configured", "item": "starter", "message": "This item has no Stripe price configured"}
    fake.fail_with = StripeError("card network down")
    response = as_client.post("/billing/checkout", json={"packId": "plus"})
    assert response.status_code == 502 and response.get_json()["error"] == "stripe_error"


def test_portal(as_client, svc):
    fake = configure_fake_stripe(svc)
    response = as_client.post("/billing/portal")
    assert response.status_code == 400 and response.get_json()["error"] == "no_billing_account"
    svc.store.users.update("client_1", {"stripeCustomerId": "cus_9"})
    response = as_client.post("/billing/portal")
    assert response.status_code == 200 and response.get_json() == {"url": "https://billing.stripe.test/cus_9"}
    assert fake.portals == [{"customer": "cus_9", "return_url": "http://app.test/#/account"}]


# --- webhooks ------------------------------------------------------------------


def test_webhook_503_when_not_configured(client):
    response = post_webhook(client, stripe_event("evt_1", "checkout.session.completed", {}))
    assert response.status_code == 503 and response.get_json()["error"] == "stripe_not_configured"


def test_webhook_bad_signature_400(client, svc):
    configure_fake_stripe(svc)
    event = stripe_event("evt_1", "checkout.session.completed", {"client_reference_id": "client_1", "mode": "payment", "metadata": {"packId": "starter"}})
    response = post_webhook(client, event, signature="sig:wrong")
    assert response.status_code == 400 and response.get_json()["error"] == "invalid_signature"
    response = client.post("/billing/webhook", data=json.dumps(event), content_type="application/json")
    assert response.status_code == 400
    assert svc.ledger.balance("client_1") == 3 and svc.store.stripe_events.count() == 0


def test_webhook_checkout_completed_grants_credits_idempotently(client, svc):
    configure_fake_stripe(svc)
    event = stripe_event(
        "evt_pack",
        "checkout.session.completed",
        {"id": "cs_1", "client_reference_id": "client_1", "customer": "cus_77", "mode": "payment", "amount_total": 999, "currency": "usd", "metadata": {"uid": "client_1", "packId": "plus"}},
    )
    response = post_webhook(client, event)
    assert response.status_code == 200
    assert response.get_json() == {"received": True, "duplicate": False, "id": "evt_pack", "handled": True, "action": "grant_credits", "uid": "client_1", "credits": 30}
    assert svc.ledger.balance("client_1") == 33
    assert svc.store.users.get("client_1")["stripeCustomerId"] == "cus_77"
    grant = svc.ledger.usage("client_1")[0]
    assert grant["reason"] == "purchase" and grant["meta"]["packId"] == "plus" and grant["meta"]["amount_total"] == 999
    # Stripe retries: same event id must not grant twice
    again = post_webhook(client, event)
    assert again.get_json() == {"received": True, "duplicate": True, "id": "evt_pack"}
    assert svc.ledger.balance("client_1") == 33
    assert svc.store.stripe_events.get("evt_pack")["type"] == "checkout.session.completed"


def test_webhook_checkout_subscription_activates_pro(client, svc):
    configure_fake_stripe(svc)
    event = stripe_event("evt_sub", "checkout.session.completed", {"client_reference_id": "barber_1", "customer": "cus_b", "subscription": "sub_b", "mode": "subscription"})
    assert post_webhook(client, event).get_json()["action"] == "activate_pro"
    user = svc.store.users.get("barber_1")
    assert user["plan"] == "pro" and user["stripeSubscriptionId"] == "sub_b" and user["stripeCustomerId"] == "cus_b"


def test_webhook_subscription_lifecycle(client, svc):
    configure_fake_stripe(svc)
    svc.ledger.set_plan("barber_1", "pro", subscription_id="sub_b", customer_id="cus_b")
    # renewal keeps pro
    svc.ledger.set_plan("barber_1", "free")
    paid = stripe_event("evt_inv", "invoice.paid", {"customer": "cus_b", "subscription": "sub_b"})
    assert post_webhook(client, paid).get_json()["action"] == "renew_pro"
    assert svc.store.users.get("barber_1")["plan"] == "pro" and svc.store.users.get("barber_1")["stripeSubscriptionId"] == "sub_b"
    # past due -> free, active again -> pro
    past_due = stripe_event("evt_upd1", "customer.subscription.updated", {"id": "sub_b", "customer": "cus_b", "status": "past_due"})
    assert post_webhook(client, past_due).get_json()["action"] == "downgrade"
    assert svc.store.users.get("barber_1")["plan"] == "free"
    active = stripe_event("evt_upd2", "customer.subscription.updated", {"id": "sub_b", "customer": "cus_b", "status": "active", "metadata": {"uid": "barber_1"}})
    assert post_webhook(client, active).get_json()["action"] == "activate_pro"
    assert svc.store.users.get("barber_1")["plan"] == "pro"
    # deletion -> free and subscription id cleared
    deleted = stripe_event("evt_del", "customer.subscription.deleted", {"id": "sub_b", "customer": "cus_b", "status": "canceled"})
    result = post_webhook(client, deleted).get_json()
    assert result["action"] == "downgrade" and result["status"] == "canceled"
    user = svc.store.users.get("barber_1")
    assert user["plan"] == "free" and user["stripeSubscriptionId"] is None
    assert [e["kind"] for e in svc.ledger.usage("barber_1")].count("plan") >= 5


def test_webhook_ignores_unknown_events_and_users(client, svc):
    configure_fake_stripe(svc)
    response = post_webhook(client, stripe_event("evt_x", "payment_intent.created", {}))
    assert response.get_json()["handled"] is False and response.get_json()["reason"] == "ignored"
    response = post_webhook(client, stripe_event("evt_y", "checkout.session.completed", {"client_reference_id": "nobody", "mode": "payment", "metadata": {"packId": "starter"}}))
    assert response.get_json()["handled"] is False and response.get_json()["reason"] == "unknown_user"
    response = post_webhook(client, stripe_event("evt_z", "checkout.session.completed", {"client_reference_id": "client_1", "mode": "payment", "metadata": {}}))
    assert response.get_json()["reason"] == "unknown_pack" and svc.ledger.balance("client_1") == 3
    response = post_webhook(client, stripe_event("evt_w", "invoice.paid", {"customer": "cus_unknown"}))
    assert response.get_json()["reason"] == "unknown_user"
    assert post_webhook(client, {"type": "checkout.session.completed", "data": {"object": {}}}).status_code == 400
    assert svc.store.stripe_events.count() == 4


def test_real_stripe_client_maps_signature_errors():
    from lineup_backend.services.stripe_gateway import RealStripeClient, StripeSignatureError

    real = RealStripeClient("sk_test_x")
    with pytest.raises(StripeSignatureError):
        real.construct_event(b'{"id": "evt"}', "t=1,v1=bad", "whsec_x")


def test_to_plain_converts_real_stripe_objects():
    """Regression: stripe>=8 StripeObjects are not dicts and raise on .get()."""
    from stripe import StripeObject

    from lineup_backend.services.stripe_gateway import _to_plain

    obj = StripeObject.construct_from(
        {"id": "cs_1", "payment_status": "paid", "metadata": {"packId": "starter"}, "lines": [{"amount": 1}]},
        "sk_test",
    )
    plain = _to_plain(obj)
    assert isinstance(plain, dict) and plain.get("payment_status") == "paid"
    assert isinstance(plain["metadata"], dict) and plain["metadata"].get("packId") == "starter"
    assert isinstance(plain["lines"][0], dict) and plain["lines"][0].get("amount") == 1


def test_webhook_ignores_unpaid_checkout_sessions(client, svc):
    configure_fake_stripe(svc)
    unpaid = stripe_event(
        "evt_unpaid",
        "checkout.session.completed",
        {"client_reference_id": "client_1", "mode": "payment", "payment_status": "unpaid", "metadata": {"packId": "starter"}},
    )
    body = post_webhook(client, unpaid).get_json()
    assert body["handled"] is False and body["reason"] == "not_paid"
    assert svc.ledger.balance("client_1") == 3


def test_webhook_claims_the_event_before_granting(client, svc):
    """A retry of the same event id must not credit twice, even mid-flight."""
    configure_fake_stripe(svc)
    event = stripe_event(
        "evt_race",
        "checkout.session.completed",
        {"client_reference_id": "client_1", "mode": "payment", "payment_status": "paid", "metadata": {"packId": "starter"}},
    )
    first = post_webhook(client, event).get_json()
    assert first["duplicate"] is False and first["action"] == "grant_credits"
    granted = svc.ledger.balance("client_1")
    second = post_webhook(client, event).get_json()
    assert second["duplicate"] is True
    assert svc.ledger.balance("client_1") == granted
    assert svc.store.stripe_events.get("evt_race")["status"] == "done"


def test_webhook_releases_the_claim_when_handling_blows_up(client, svc, monkeypatch):
    configure_fake_stripe(svc)
    import lineup_backend.routes.billing as billing_routes

    def boom(*args, **kwargs):
        raise RuntimeError("handler exploded")

    monkeypatch.setattr(billing_routes, "apply_stripe_event", boom)
    event = stripe_event("evt_boom", "checkout.session.completed", {"client_reference_id": "client_1", "mode": "payment"})
    assert post_webhook(client, event).status_code == 500
    # Claim released, so Stripe's retry gets a real attempt rather than a false duplicate.
    assert svc.store.stripe_events.get("evt_boom") is None


def test_subscription_checkout_without_a_subscription_id_stores_none(client, svc):
    configure_fake_stripe(svc)
    event = stripe_event("evt_sub_none", "checkout.session.completed", {"client_reference_id": "barber_1", "mode": "subscription", "payment_status": "paid"})
    assert post_webhook(client, event).get_json()["action"] == "activate_pro"
    assert svc.store.users.get("barber_1")["stripeSubscriptionId"] is None


def test_refund_is_claimed_once_and_credits_the_balance(svc):
    ledger = svc.ledger
    before = ledger.balance("client_1")
    charge = ledger.charge("client_1", "analysis")
    assert ledger.balance("client_1") == before - charge["credits"]
    ledger.refund(charge["id"], "provider_error")
    assert ledger.balance("client_1") == before
    # A second refund of the same charge is a no-op.
    ledger.refund(charge["id"], "provider_error")
    assert ledger.balance("client_1") == before
    event = svc.store.usage_events.get(charge["id"])
    assert event["refunded"] is True and event["refunding"] is False


def test_daily_cap_counts_only_today(svc):
    ledger = svc.ledger
    charge = ledger.charge("client_1", "analysis")
    assert ledger.today_count("client_1", "analysis") == 1
    # Events are stamped with the UTC day so the count is a filter, not a scan.
    assert svc.store.usage_events.get(charge["id"])["day"]
    svc.store.usage_events.update(charge["id"], {"day": "2000-01-01"})
    assert ledger.today_count("client_1", "analysis") == 0

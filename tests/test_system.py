import json

from tests.conftest import login, make_app
from tests.helpers import analyze_payload, tiny_image_b64


def test_index_lists_endpoints(client):
    data = client.get("/").get_json()
    assert data["status"] == "running"
    assert "/health" in data["endpoints"]["health"]
    assert "/auth/me" in data["endpoints"]["auth"]


def test_health_reports_integrations_and_counts(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["storage"] == "memory"
    assert data["integrations"] == {
        "gemini": False,
        "google_places": False,
        "replicate": False,
        "cloudinary": False,
        "firebase_storage": False,
        "firestore": False,
        "firebase_auth": False,
        "stripe": False,
    }
    assert data["auth_mode"] == "dev"
    assert data["gemini_configured"] is False
    assert data["data_counts"]["social_posts"] == 2
    assert data["data_counts"]["appointments"] == 1


def test_config_exposes_flags_only(client):
    data = client.get("/config").get_json()
    assert data["hasGeminiApi"] is False
    assert data["hasStripe"] is False
    assert data["features"]["virtualTryOn"] is False
    assert data["rateLimits"]["gemini_api_remaining"] == 50
    assert data["auth"] == {"mode": "dev", "devLogin": True, "firebase": None}
    assert data["billing"]["stripe"] is False and data["billing"]["pricingUrl"] == "/billing/pricing"
    assert not any("key" in k.lower() and isinstance(v, str) for k, v in data.items())


def test_404_is_json(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found", "message": "The requested resource does not exist"}


def test_405_is_json(client):
    response = client.delete("/health")
    assert response.status_code == 405
    data = response.get_json()
    assert data["error"] == "Method not allowed"
    assert "GET" in data["allowed"]


def test_500_is_json_and_does_not_leak():
    app = make_app()

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret detail")

    response = app.test_client().get("/boom")
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] == "Internal server error"
    assert "secret" not in json.dumps(data)


def test_413_for_oversized_body():
    app = make_app(max_content_length=1024)
    authed = login(app.test_client(), "client@lineup.dev")
    body = json.dumps({"image": "A" * 4096})
    response = authed.post("/analyze", data=body, content_type="application/json")
    assert response.status_code == 413
    data = response.get_json()
    assert data["error"] == "Payload too large"
    assert data["max_bytes"] == 1024


def test_429_shape_when_rate_limited():
    app = make_app(ratelimit_enabled=True, rate_limits={**make_app().config["LINEUP_RATE_LIMITS"], "ai": "2 per hour"})
    authed = login(app.test_client(), "client@lineup.dev")
    payload = analyze_payload(tiny_image_b64())
    assert authed.post("/analyze", json=payload).status_code == 200
    assert authed.post("/analyze", json=payload).status_code == 200
    response = authed.post("/analyze", json=payload)
    assert response.status_code == 429
    data = response.get_json()
    assert data["error"] == "Rate limit exceeded"
    assert "retry_after" in data
    assert response.headers.get("Retry-After")


def test_rate_limits_are_per_user_when_signed_in():
    app = make_app(ratelimit_enabled=True, rate_limits={**make_app().config["LINEUP_RATE_LIMITS"], "ai": "1 per hour"})
    client = app.test_client()
    first = login(client, "client@lineup.dev")
    second = login(client, "second@lineup.dev")
    payload = analyze_payload(tiny_image_b64())
    assert first.post("/analyze", json=payload).status_code == 200
    assert first.post("/analyze", json=payload).status_code == 429
    # Same IP, different user: not blocked by the first user's window.
    assert second.post("/analyze", json=payload).status_code == 200


def test_cors_allows_any_localhost_port(client):
    response = client.get("/health", headers={"Origin": "http://localhost:8000"})
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:8000"
    response = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert response.headers.get("Access-Control-Allow-Origin") == "http://127.0.0.1:5173"


def test_cors_rejects_unknown_origin(client):
    response = client.get("/health", headers={"Origin": "https://evil.example.com"})
    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_cors_preflight_allows_authorization_header(client):
    response = client.options(
        "/appointments",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
    )
    assert response.status_code == 200
    assert "POST" in response.headers.get("Access-Control-Allow-Methods", "")
    assert "authorization" in response.headers.get("Access-Control-Allow-Headers", "").lower()
    assert response.headers.get("Access-Control-Allow-Origin") == "http://localhost:8000"


def test_metrics_and_cache_endpoints(client, as_client):
    client.get("/barbers?location=Atlanta")
    metrics = client.get("/metrics").get_json()
    assert "summary" in metrics and "cache_summary" in metrics
    assert metrics["endpoints"]["barbers"]["request_count"] >= 1
    stats = client.get("/cache-stats").get_json()
    assert stats["cache_size"] == 0
    # dev auth mode without LINEUP_ADMIN_TOKEN: ops endpoints are open (see tests/test_ops_access.py for the gate)
    cleared = client.post("/clear-cache").get_json()
    assert cleared["success"] is True

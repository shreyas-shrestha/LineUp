"""Operational endpoints (/metrics, /cache-stats, /clear-cache) are gated by
LINEUP_ADMIN_TOKEN; without it they exist only in dev auth mode."""

from __future__ import annotations

from tests.conftest import login, make_app

OPS = ("/metrics", "/cache-stats")


def test_ops_open_in_dev_mode_without_admin_token(client, as_client):
    for path in OPS:
        assert client.get(path).status_code == 200
    assert client.post("/clear-cache").get_json()["success"] is True
    assert as_client.post("/clear-cache").status_code == 200


def test_ops_hidden_in_production_without_admin_token():
    app = make_app(env="production", seed_mock_data=False)
    client = app.test_client()
    for path in OPS:
        response = client.get(path)
        assert response.status_code == 404
        assert response.get_json()["error"] == "Not found"
    assert client.post("/clear-cache").status_code == 404


def test_ops_require_matching_admin_token_when_configured():
    app = make_app(admin_token="ops-secret")
    client = app.test_client()
    # even in dev mode a configured token is enforced
    assert client.get("/metrics").status_code == 404
    assert client.get("/metrics", headers={"X-Admin-Token": "wrong"}).status_code == 404
    assert client.get("/metrics", headers={"X-Admin-Token": "ops-secret"}).status_code == 200
    assert client.get("/cache-stats", headers={"Authorization": "Bearer ops-secret"}).status_code == 200
    assert client.post("/clear-cache", headers={"X-Admin-Token": "ops-secret"}).get_json()["success"] is True
    # a signed-in user's bearer token is not an admin token
    user = login(client, "someone@example.com", role="client")
    assert user.get("/metrics").status_code == 404


def test_admin_token_is_redacted_from_config_dump():
    app = make_app(admin_token="ops-secret")
    dumped = app.config["LINEUP_CONFIG"].redacted()
    assert dumped["admin_token"] == "***"

"""Barber Pro gates: every locked feature answers 402 {"error": "pro_required", "feature": ...}."""

from lineup_backend.pricing import FREE_PORTFOLIO_LIMIT


def _pro_required(response, feature):
    assert response.status_code == 402, response.get_json()
    assert response.get_json() == {"error": "pro_required", "feature": feature}


def test_portfolio_seventh_photo_needs_pro(as_barber, client, svc):
    # one seeded work + five more reach the free limit of six
    for index in range(FREE_PORTFOLIO_LIMIT - 1):
        response = as_barber.post("/portfolio/barber_1", json={"image": f"https://img.example/{index}.jpg"})
        assert response.status_code == 201
    assert response.get_json()["remaining_free"] == 0
    assert len(client.get("/portfolio/barber_1").get_json()["portfolio"]) == 6
    _pro_required(as_barber.post("/portfolio/barber_1", json={"image": "https://img.example/7.jpg"}), "portfolio")
    _pro_required(as_barber.post("/portfolio", json={"image": "https://img.example/7.jpg"}), "portfolio")
    assert len(client.get("/portfolio/barber_1").get_json()["portfolio"]) == 6

    assert as_barber.post("/billing/dev-activate-pro").get_json()["plan"] == "pro"
    response = as_barber.post("/portfolio/barber_1", json={"image": "https://img.example/7.jpg"})
    assert response.status_code == 201 and response.get_json()["count"] == 7 and response.get_json()["remaining_free"] is None


def test_packages_need_pro(as_barber):
    body = {"title": "Monthly", "price": "$99", "numCuts": 4, "durationMonths": 1}
    _pro_required(as_barber.post("/subscription-packages", json=body), "packages")
    as_barber.post("/billing/dev-activate-pro")
    assert as_barber.post("/subscription-packages", json=body).status_code == 201


def test_client_tools_need_pro(as_barber):
    _pro_required(as_barber.get("/barbers/barber_1/clients"), "clients")
    _pro_required(as_barber.get("/barbers/barber_1/clients/client_1/history"), "client_history")
    _pro_required(as_barber.get("/barbers/barber_1/clients/client_1/notes"), "client_notes")
    _pro_required(as_barber.post("/barbers/barber_1/clients/client_1/notes", json={"note": "x"}), "client_notes")
    as_barber.post("/billing/dev-activate-pro")
    assert as_barber.get("/barbers/barber_1/clients").status_code == 200
    assert as_barber.get("/barbers/barber_1/clients/client_1/history").get_json()["totalVisits"] == 1
    assert as_barber.post("/barbers/barber_1/clients/client_1/notes", json={"note": "x"}).status_code == 201


def test_ownership_is_checked_before_the_pro_gate(as_barber, as_client):
    assert as_barber.get("/barbers/barber_2/clients").status_code == 403
    assert as_client.get("/barbers/barber_1/clients").status_code == 403


def test_entitlements_follow_plan(as_barber):
    free = as_barber.get("/auth/me").get_json()["entitlements"]
    assert free["pro"] is False and free["features"]["portfolio_limit"] == 6
    assert {k: v for k, v in free["features"].items() if k != "portfolio_limit"} == {
        "packages": False,
        "clients": False,
        "client_history": False,
        "client_notes": False,
        "analytics": False,
    }
    as_barber.post("/billing/dev-activate-pro")
    pro = as_barber.get("/auth/me").get_json()["entitlements"]
    assert pro["pro"] is True and pro["features"]["portfolio_limit"] is None and pro["features"]["analytics"] is True

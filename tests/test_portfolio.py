def test_portfolio_all_and_by_barber(client):
    assert client.get("/portfolio").get_json()["portfolio"][0]["styleName"] == "Modern Fade"
    assert client.get("/portfolio/barber_1").get_json()["portfolio"][0]["barberId"] == "barber_1"
    assert client.get("/portfolio/nobody").get_json() == {"portfolio": []}


def test_portfolio_create_owner_only(client, as_client, as_barber):
    body = {"styleName": "Taper", "image": "https://img.example/t.jpg", "description": "Low taper"}
    assert client.post("/portfolio/barber_1", json=body).status_code == 401
    assert as_client.post("/portfolio/barber_1", json=body).status_code == 403
    assert as_barber.post("/portfolio/barber_7", json=body).status_code == 403

    response = as_barber.post("/portfolio/barber_1", json=body)
    assert response.status_code == 201
    data = response.get_json()
    work = data["work"]
    assert work["barberId"] == "barber_1" and work["likes"] == 0 and work["date"]
    assert data["count"] == 2 and data["remaining_free"] == 4  # one seeded work + this one, limit 6
    assert client.get("/portfolio/barber_1").get_json()["portfolio"][0]["id"] == work["id"]
    # owner comes from the token when the path has no id (body barberId is ignored)
    work = as_barber.post("/portfolio", json={"barberId": "barber_8", "image": "https://img.example/x.jpg"}).get_json()["work"]
    assert work["barberId"] == "barber_1"
    assert as_barber.post("/portfolio", json={"styleName": "no image"}).status_code == 400


def test_portfolio_delete(client, as_barber, as_client):
    work = as_barber.post("/portfolio/barber_1", json={"image": "https://img.example/x.jpg"}).get_json()["work"]
    assert as_client.delete(f"/portfolio/barber_1/{work['id']}").status_code == 403
    assert as_barber.delete("/portfolio/barber_1/nope").status_code == 404
    assert as_barber.delete(f"/portfolio/barber_1/{work['id']}").get_json() == {"success": True}
    assert all(w["id"] != work["id"] for w in client.get("/portfolio/barber_1").get_json()["portfolio"])


def test_subscription_packages(client, as_client, as_pro_barber):
    assert client.get("/subscription-packages?barber_id=barber_1").get_json() == {"packages": []}
    payload = {"barberId": "spoofed", "barberName": "Mike", "title": "Monthly Fade", "price": "$99", "numCuts": "4", "durationMonths": 1, "discount": "20%"}
    assert client.post("/subscription-packages", json=payload).status_code == 401
    assert as_client.post("/subscription-packages", json=payload).status_code == 403
    response = as_pro_barber.post("/subscription-packages", json=payload)
    assert response.status_code == 201
    package = response.get_json()["package"]
    assert package["numCuts"] == 4 and package["title"] == "Monthly Fade" and package["barberId"] == "barber_1"
    assert client.get("/subscription-packages?barber_id=barber_1").get_json()["packages"][0]["id"] == package["id"]
    assert client.get("/subscription-packages?barber_id=other").get_json()["packages"] == []
    assert len(client.get("/subscription-packages").get_json()["packages"]) == 1
    assert as_pro_barber.post("/subscription-packages", json={"price": "$1"}).status_code == 400
    assert as_pro_barber.delete("/subscription-packages/nope").status_code == 404
    assert as_pro_barber.delete(f"/subscription-packages/{package['id']}").get_json() == {"success": True}
    assert client.get("/subscription-packages").get_json() == {"packages": []}


def test_client_subscriptions(client, as_client, as_pro_barber, other_client):
    package = as_pro_barber.post("/subscription-packages", json={"barberName": "Mike", "title": "Monthly", "price": "$99", "numCuts": 4, "durationMonths": 2}).get_json()["package"]
    assert client.post("/client-subscriptions", json={"packageId": package["id"]}).status_code == 401
    response = as_client.post("/client-subscriptions", json={"packageId": package["id"], "clientId": "spoofed"})
    assert response.status_code == 201
    sub = response.get_json()["subscription"]
    assert sub["clientId"] == "client_1" and sub["clientName"] == "Alex Johnson"
    assert sub["status"] == "active" and sub["remainingCuts"] == 4 and sub["barberName"] == "Mike" and sub["packageTitle"] == "Monthly"
    assert sub["barberId"] == "barber_1"
    assert sub["expiryDate"] > sub["purchaseDate"]
    assert as_client.get("/client-subscriptions").get_json()["subscriptions"][0]["id"] == sub["id"]
    assert other_client.get("/client-subscriptions").get_json() == {"subscriptions": []}
    assert as_client.post("/client-subscriptions", json={}).status_code == 400
    assert as_client.post("/client-subscriptions", json={"packageId": "ghost"}).status_code == 404


def test_portfolio_rejects_non_image_values(as_barber):
    from tests.helpers import tiny_image_b64

    png = tiny_image_b64()
    for bad in ("x.jpg", "javascript:alert(1)", "data:text/html,<script>", "not base64 at all", "https://x.example/a b"):
        response = as_barber.post("/portfolio/barber_1", json={"image": bad})
        assert response.status_code == 400, bad
    ok = as_barber.post("/portfolio/barber_1", json={"image": f"data:image/png;base64,{png}", "styleName": "Fade"})
    assert ok.status_code == 201
    assert ok.get_json()["work"]["image"] == f"data:image/png;base64,{png}"

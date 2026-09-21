from tests.conftest import login
from tests.helpers import PLACE_ID, FakeResponse, make_places_http


def test_barbers_mock_without_places_key(client):
    data = client.get("/barbers?location=Atlanta,%20GA").get_json()
    assert data["mock"] is True and data["real_data"] is False
    assert data["reason"] == "places_not_configured"
    assert data["location"] == "Atlanta, GA"
    # Sample shops are ranked like real ones (by rating without styles): the
    # two 4.9s lead, ties keep their order.
    assert [b["id"] for b in data["barbers"]] == ["barber_1", "barber_3", "barber_2"]
    assert data["barbers"][0]["name"] == "Elite Cuts Atlanta"
    assert "billing" not in data  # anonymous: nothing metered


def test_barbers_real_data_then_cache(as_client, client, svc):
    calls = []
    svc.places.api_key = "test-key"
    svc.places._http_get = make_places_http(calls)

    data = as_client.get("/barbers?location=Atlanta&styles=Modern%20Fade").get_json()
    assert data["real_data"] is True and data["mock"] is False and data["cached"] is False
    assert data["ranked_by_style"] is True and data["total_found"] == 2
    assert data["billing"]["charged"] == 1 and data["billing"]["credits"] == 2
    top = data["barbers"][0]
    assert top["id"] == PLACE_ID and top["name"] == "Fade Kings Barbershop"
    assert top["photo"] == "http://api.test/places/photo?ref=photo-ref-123&maxwidth=400"
    assert "key=" not in top["photo"]
    assert top["reviews"][0]["username"] == "Sam" and top["reviews"][0]["date"] == "2023-11-14"
    assert "Fade Specialist" in top["specialties"]
    # Google reported price_level 2 and no reviewer quoted a price: show the
    # tier, never an invented dollar figure.
    assert top["price_tier"] == "$$" and top["avgCost"] is None and top["price_source"] == "google"
    second = data["barbers"][1]
    assert second["price_tier"] == "$" and second["avgCost"] is None
    # The ranker explains itself: name + review keyword + rating.
    assert top["match"]["level"] in ("strong", "good", "some")
    assert top["match"]["top_style"] == "Modern Fade"
    assert "The name says fade" in top["match"]["reasons"]
    assert "1 review mentions modern fade" in top["match"]["reasons"]
    assert "Rated 4.7 by 210 people" in top["match"]["reasons"]
    assert len(calls) == 4  # geocode + nearby + 2 details
    assert svc.places_quota.used == 4  # the budget counts Google calls, not searches

    cached = as_client.get("/barbers?location=atlanta").get_json()
    assert cached["cached"] is True and cached["real_data"] is True
    assert cached["billing"] == {"action": "barber_search", "charged": 0, "credits": 2, "free": True}
    assert len(calls) == 4
    assert client.get("/cache-stats").get_json()["cache_size"] == 1

    # Anonymous callers get cached results but never trigger a Google call.
    anon = client.get("/barbers?location=Atlanta").get_json()
    assert anon["cached"] is True and anon["real_data"] is True
    anon_miss = client.get("/barbers?location=Boston").get_json()
    assert anon_miss["mock"] is True and anon_miss["reason"] == "sign_in_required"
    assert len(calls) == 4


def test_barbers_error_falls_back_to_mock_and_refunds(as_client, svc):
    svc.places.api_key = "test-key"

    def broken(url, params=None, **kwargs):
        raise ConnectionError("dns failure")

    svc.places._http_get = broken
    data = as_client.get("/barbers?location=Nowhere").get_json()
    assert data["mock"] is True and data["reason"] == "places_error"
    assert "dns failure" in data["error"]
    assert data["billing"]["charged"] == 0 and data["billing"]["refunded"] == "provider_error"
    assert svc.ledger.balance(as_client.uid) == 3


def test_barbers_quota_exhausted(as_client, svc):
    svc.places.api_key = "test-key"
    svc.places_quota.used = svc.places_quota.limit
    data = as_client.get("/barbers?location=Atlanta").get_json()
    assert data["mock"] is True and data["reason"] == "daily_quota_reached"
    assert data["billing"]["charged"] == 0


def test_barbers_search_402_when_out_of_credits(as_client, svc):
    svc.places.api_key = "test-key"
    svc.places._http_get = make_places_http([])
    svc.store.users.update(as_client.uid, {"credits": 0})
    response = as_client.get("/barbers?location=Atlanta")
    assert response.status_code == 402
    assert response.get_json() == {"error": "insufficient_credits", "needed": 1, "credits": 0, "action": "barber_search"}


def test_place_photo_redirects_without_leaking_key(client, svc):
    svc.places.api_key = "test-key"
    seen = {}

    def fake_get(url, params=None, **kwargs):
        seen.update(params)
        assert kwargs.get("allow_redirects") is False
        return FakeResponse(status=302, headers={"Location": "https://lh3.googleusercontent.com/photo"})

    svc.places._http_get = fake_get
    response = client.get("/places/photo?ref=abc&maxwidth=300")
    assert response.status_code == 302
    assert response.headers["Location"] == "https://lh3.googleusercontent.com/photo"
    assert seen["key"] == "test-key" and seen["maxwidth"] == 300
    assert client.get("/places/photo").status_code == 400


def test_place_photo_404_without_key(client):
    assert client.get("/places/photo?ref=abc").status_code == 404


def test_profile_public_read_and_owner_update(client, as_barber, as_client):
    profile = client.get("/barbers/barber_1/profile").get_json()["profile"]
    assert profile["name"] == "Mike's Cuts" and profile["id"] == "barber_1"
    assert "ownerUid" not in profile
    assert client.get("/barbers/nobody/profile").status_code == 404

    assert client.put("/barbers/barber_1/profile", json={"name": "x"}).status_code == 401
    assert as_client.put("/barbers/barber_1/profile", json={"name": "x"}).status_code == 403
    assert as_barber.put("/barbers/other/profile", json={"name": "x"}).status_code == 403
    response = as_barber.put("/barbers/barber_1/profile", json={"name": "Mike's Cuts & Co", "phone": "555"})
    assert response.status_code == 200
    assert response.get_json()["profile"]["name"] == "Mike's Cuts & Co"
    assert client.get("/barbers/barber_1/profile").get_json()["profile"]["phone"] == "555"
    assert as_barber.put("/barbers/barber_1/profile", json={"name": ""}).status_code == 400


def test_reviews_local_get_and_post(client, as_client):
    data = client.get("/barbers/barber_1/reviews").get_json()
    assert data["source"] == "local" and data["total_reviews"] == 3
    assert data["average_rating"] == 4.7

    assert client.post("/barbers/barber_1/reviews", json={"rating": 3}).status_code == 401
    response = as_client.post("/barbers/barber_1/reviews", json={"username": "spoofed", "rating": 3, "text": "Fine"})
    assert response.status_code == 201
    review = response.get_json()["review"]
    assert review["barberId"] == "barber_1" and review["rating"] == 3 and review["id"]
    assert review["username"] == "Alex Johnson" and review["uid"] == "client_1"  # author comes from the token

    data = client.get("/barbers/barber_1/reviews").get_json()
    assert data["total_reviews"] == 4 and data["reviews"][0]["username"] == "Alex Johnson"


def test_reviews_invalid_rating(as_client):
    response = as_client.post("/barbers/barber_1/reviews", json={"rating": 9})
    assert response.status_code == 400
    assert "rating" in response.get_json()["error"]


def test_reviews_from_google_for_place_ids(client, svc):
    svc.places.api_key = "test-key"
    svc.places._http_get = make_places_http([])
    data = client.get(f"/barbers/{PLACE_ID}/reviews").get_json()
    assert data["source"] == "google" and data["total_reviews"] == 210
    assert data["reviews"][0]["text"] == "Best fade in town"
    # non-place ids still use local reviews
    assert client.get("/barbers/barber_2/reviews").get_json()["source"] == "local"


def test_availability_default_and_owner_update(client, as_barber, as_client):
    data = client.get("/barbers/b9/availability").get_json()["availability"]
    assert data["workingHours"]["sunday"]["enabled"] is False
    assert data["serviceDuration"] == 30

    hours = {"monday": {"enabled": True, "start": "10:00", "end": "14:00"}, "sunday": {"enabled": False, "start": "09:00", "end": "17:00"}}
    body = {"workingHours": hours, "serviceDuration": 45, "bufferTime": 0, "blockedDates": ["2030-01-02", "bad"]}
    assert client.put("/barbers/barber_1/availability", json=body).status_code == 401
    assert as_client.put("/barbers/barber_1/availability", json=body).status_code == 403
    assert as_barber.put("/barbers/barber_2/availability", json=body).status_code == 403
    response = as_barber.put("/barbers/barber_1/availability", json=body)
    assert response.status_code == 200
    saved = response.get_json()["availability"]
    assert saved["serviceDuration"] == 45 and saved["blockedDates"] == ["2030-01-02"]
    assert client.get("/barbers/barber_1/availability").get_json()["availability"]["workingHours"]["monday"]["end"] == "14:00"


def test_availability_rejects_bad_hours(as_barber):
    response = as_barber.put("/barbers/barber_1/availability", json={"workingHours": {"monday": {"enabled": True, "start": "18:00", "end": "09:00"}}})
    assert response.status_code == 400
    assert "monday" in response.get_json()["error"]


def test_availability_ignores_inverted_times_on_a_closed_day(as_barber):
    """A day the barber unticked keeps whatever times the form last held."""
    hours = {"sunday": {"enabled": False, "start": "18:00", "end": "09:00"}, "monday": {"enabled": True, "start": "09:00", "end": "17:00"}}
    response = as_barber.put("/barbers/barber_1/availability", json={"workingHours": hours})
    assert response.status_code == 200
    assert response.get_json()["availability"]["workingHours"]["sunday"]["enabled"] is False
    # A closed day still generates no slots.
    slots = as_barber.get("/barbers/barber_1/available-slots?date=2030-01-06").get_json()["slots"]  # a Sunday
    assert slots == []


def test_available_slots(client, as_barber, as_client):
    hours = {"monday": {"enabled": True, "start": "09:00", "end": "11:00"}, "sunday": {"enabled": False, "start": "09:00", "end": "17:00"}}
    as_barber.put("/barbers/barber_1/availability", json={"workingHours": hours, "serviceDuration": 30, "bufferTime": 0})
    # 2030-01-07 is a Monday
    as_client.post("/appointments", json={"barberId": "barber_1", "date": "2030-01-07", "time": "09:30"})
    data = client.get("/barbers/barber_1/available-slots?date=2030-01-07").get_json()
    assert data["slots"] == ["09:00", "10:00", "10:30"]
    assert data["workingHours"]["start"] == "09:00"
    assert client.get("/barbers/barber_1/available-slots?date=2030-01-06").get_json()["slots"] == []  # Sunday


def test_available_slots_requires_valid_date(client):
    assert client.get("/barbers/b1/available-slots").status_code == 400
    assert client.get("/barbers/b1/available-slots?date=tomorrow").status_code == 400


def test_services_unknown_barber_gets_unsaved_defaults(client, svc):
    data = client.get("/barbers/ChIJN1t_tDeuEmsRUsoyG83frY4/services").get_json()
    assert data["registered"] is False
    assert [s["name"] for s in data["services"]] == ["Haircut", "Beard Trim", "Haircut + Beard"]
    assert all(s["default"] is True and s["id"].startswith("default-") for s in data["services"])
    assert svc.store.barber_services.list(barberId="ChIJN1t_tDeuEmsRUsoyG83frY4") == []  # nothing persisted


def test_services_registered_barber_crud(client, as_barber, as_client):
    data = client.get("/barbers/barber_1/services").get_json()
    assert data["registered"] is True
    assert [s["name"] for s in data["services"]] == ["Haircut", "Beard Trim", "Haircut + Beard"]
    assert all(s["barberId"] == "barber_1" for s in data["services"])

    assert client.post("/barbers/barber_1/services", json={"name": "x"}).status_code == 401
    assert as_client.post("/barbers/barber_1/services", json={"name": "x"}).status_code == 403
    assert as_barber.post("/barbers/barber_2/services", json={"name": "x"}).status_code == 403

    response = as_barber.post("/barbers/barber_1/services", json={"name": "Hot Towel Shave", "price": "25", "duration": 20})
    assert response.status_code == 201
    created = response.get_json()["service"]
    assert created["price"] == 25.0 and created["duration"] == 20 and created["category"] == "General"

    response = as_barber.put(f"/barbers/barber_1/services?service_id={created['id']}", json={"price": 30})
    assert response.get_json()["service"]["price"] == 30.0 and response.get_json()["service"]["name"] == "Hot Towel Shave"

    assert as_barber.delete(f"/barbers/barber_1/services?service_id={created['id']}").get_json() == {"success": True}
    assert len(client.get("/barbers/barber_1/services").get_json()["services"]) == 3
    assert as_barber.delete("/barbers/barber_1/services?service_id=nope").status_code == 404
    assert as_barber.delete("/barbers/barber_1/services").status_code == 400
    assert as_barber.post("/barbers/barber_1/services", json={"price": 1}).status_code == 400


def test_onboarded_barber_has_services_and_hours(client):
    barber = login(client, "new-barber@lineup.dev", name="Dee", role="barber", shop_name="Dee's Chair")
    assert client.get(f"/barbers/{barber.uid}/profile").get_json()["profile"]["name"] == "Dee's Chair"
    services = client.get(f"/barbers/{barber.uid}/services").get_json()
    assert services["registered"] is True and len(services["services"]) == 3
    assert not services["services"][0]["id"].startswith("default-")
    assert client.get(f"/barbers/{barber.uid}/availability").get_json()["availability"]["barberId"] == barber.uid


def test_clients_and_history(as_pro_barber, as_client):
    as_client.post("/appointments", json={"barberId": "barber_1", "date": "2030-02-01", "time": "10:00", "price": 40})
    clients = as_pro_barber.get("/barbers/barber_1/clients").get_json()["clients"]
    assert len(clients) == 1
    alex = clients[0]
    assert alex["clientId"] == "client_1" and alex["totalVisits"] == 2 and alex["totalSpent"] == 105.0
    assert alex["lastVisit"]

    history = as_pro_barber.get("/barbers/barber_1/clients/client_1/history").get_json()
    assert history["totalVisits"] == 2 and history["appointments"][0]["date"] == "2030-02-01"
    assert as_pro_barber.get("/barbers/barber_1/clients/ghost/history").get_json()["totalVisits"] == 0
    assert as_pro_barber.get("/barbers/barber_2/clients").status_code == 403


def test_client_notes(as_pro_barber):
    assert as_pro_barber.get("/barbers/barber_1/clients/c1/notes").get_json() == {"notes": []}
    response = as_pro_barber.post("/barbers/barber_1/clients/c1/notes", json={"note": "Prefers scissors", "type": "client_preference"})
    assert response.status_code == 201
    note = response.get_json()["note"]
    assert note["type"] == "client_preference"
    response = as_pro_barber.put("/barbers/barber_1/clients/c1/notes", json={"id": note["id"], "note": "Prefers clippers"})
    assert response.get_json()["note"]["note"] == "Prefers clippers"
    notes = as_pro_barber.get("/barbers/barber_1/clients/c1/notes").get_json()["notes"]
    assert len(notes) == 1 and notes[0]["note"] == "Prefers clippers"
    assert as_pro_barber.post("/barbers/barber_1/clients/c1/notes", json={}).status_code == 400
    assert as_pro_barber.put("/barbers/barber_1/clients/c1/notes", json={"id": "x", "note": "y"}).status_code == 404


def test_matcher_review_cache_is_bounded():
    from lineup_backend.services.barber_matcher import BarberMatcher

    matcher = BarberMatcher(generate_text=lambda prompt: '{"overall_match_score": 0.5, "matches": []}')
    matcher.MAX_CACHE_ENTRIES = 5
    for index in range(20):
        matcher.analyze_barber_reviews(f"Shop {index}", [{"text": "Great fades here"}], ["fade"])
    assert len(matcher._cache) <= 5  # noqa: SLF001 - asserting the bound


def test_places_errors_never_leak_the_api_key(client, svc, monkeypatch):
    """A requests error message carries the full URL, key and all."""
    from lineup_backend.services.places import _redact

    key = "AIza-secret-places-key"
    message = f"HTTPSConnectionPool: /maps/api/geocode/json?address=30308&key={key} failed"
    assert key not in _redact(message, key)
    assert "<redacted>" in _redact(message, key)
    assert _redact(message, None) == message


# --- prices and the ranking rationale -------------------------------------------------


def test_prices_come_from_reviews_or_google_never_invented():
    from lineup_backend.services.places import estimate_price_from_reviews, price_tier

    assert estimate_price_from_reviews([]) is None
    assert estimate_price_from_reviews([{"text": "Great cut, friendly staff"}]) is None
    assert estimate_price_from_reviews([{"text": "$30 for a skin fade, worth it"}]) == 30
    # median of what people quote; tips and out-of-range numbers are ignored
    reviews = [{"text": "Paid $ 40"}, {"text": "$35 plus a $5 tip"}, {"text": "$60 with beard"}, {"text": "$2000 for a suit next door"}]
    assert estimate_price_from_reviews(reviews) == 40
    assert price_tier(2) == "$$" and price_tier("3") == "$$$" and price_tier(None) is None and price_tier("x") is None


def test_sample_shops_have_distinct_prices_and_reasons(client):
    data = client.get("/barbers?location=Austin,%20TX&styles=Textured%20Crop,Modern%20Fade").get_json()
    shops = data["barbers"]
    assert len({b["avgCost"] for b in shops}) == 3 and all(b["price_source"] == "sample" for b in shops)
    assert all(b["match"]["reasons"] for b in shops)
    assert shops[0]["match"]["level"] is not None
    # Without styles the list is by rating and only the rating is claimed.
    plain = client.get("/barbers?location=Austin,%20TX").get_json()["barbers"]
    assert all(b["match"]["level"] is None and b["match"]["score"] is None for b in plain)
    assert plain[0]["match"]["reasons"] == ["Rated 4.9 by 127 people"]


def test_describe_match_uses_gemini_evidence_first():
    from lineup_backend.services.barber_matcher import BarberMatcher

    barber = {"name": "Corner Shop", "rating": 4.9, "user_ratings_total": 300, "reviews": [{"text": "lovely taper"}]}
    analysis = {"overall_match_score": 0.8, "matches": [{"style": "Taper Fade", "confidence": 0.9, "evidence": "three reviews praise their tapers"}]}
    match = BarberMatcher.describe_match(barber, ["Taper Fade", "Buzz Cut"], analysis, 0.7)
    assert match["level"] == "strong" and match["top_style"] == "Taper Fade" and match["score"] == 0.7
    assert match["reasons"][0] == "Taper Fade: three reviews praise their tapers"
    assert len(match["reasons"]) <= 3
    # No evidence for the need: say so, rather than a generic rating line.
    nothing = BarberMatcher.describe_match({"name": "Shop", "rating": 3.9, "user_ratings_total": 4}, ["Quiff"], {}, 0.0)
    assert nothing == {
        "score": 0.0,
        "level": None,
        "top_style": None,
        "reasons": ["No reviews mention quiff yet, so this one is ranked on its rating"],
        "evidence": False,
    }
    assert match["evidence"] is True


def test_hair_texture_is_part_of_the_need(client):
    from lineup_backend.services.barber_matcher import BarberMatcher, describe_need

    data = client.get("/barbers?location=Austin,%20TX&styles=Modern%20Fade&hair=curly").get_json()
    assert data["ranked_by_style"] is True
    assert data["ranked_for"] == {"styles": ["Modern Fade"], "hair": "curly", "summary": "A barber who does modern fade on curly hair"}
    top = data["barbers"][0]
    assert top["name"] == "Austin Style Studio" and top["match"]["level"] == "good" and top["match"]["evidence"] is True
    assert "1 review mentions curly hair" in top["match"]["reasons"]
    assert "2 reviews mention modern fade" in top["match"]["reasons"]
    # A shop with nothing for this need says so first; the rating comes after.
    miss = next(b for b in data["barbers"] if b["name"] == "The Austin Barber")
    assert miss["match"]["evidence"] is False
    assert miss["match"]["reasons"][0] == "No reviews mention modern fade yet, so this one is ranked on its rating"
    # Hair alone is enough to rank for.
    only_hair = client.get("/barbers?location=Austin,%20TX&hair=curly").get_json()
    assert only_hair["ranked_for"]["summary"] == "A barber who does your recommended cuts on curly hair"
    assert only_hair["barbers"][0]["name"] == "Austin Style Studio"
    # Google is asked for the texture too.
    assert BarberMatcher().build_search_keywords(["Modern Fade"], "curly").startswith("barber barbershop mens haircut curly hair")
    assert describe_need([], None) == "" and describe_need(["Quiff", "Buzz", "Crop"], None) == "A barber who does quiff or buzz"
    # A plain search (no analysis) is not "for you" and says nothing about a need.
    plain = client.get("/barbers?location=Austin,%20TX").get_json()
    assert plain["ranked_by_style"] is False and plain["ranked_for"] is None

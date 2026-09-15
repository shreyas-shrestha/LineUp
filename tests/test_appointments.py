import pytest

NEW = {"barberId": "barber_1", "barberName": "Mike", "clientId": "spoofed", "clientName": "Zoe", "date": "2030-03-01", "time": "13:00", "service": "Haircut", "price": "$30"}


def _create(authed, **extra):
    response = authed.post("/appointments", json={**NEW, **extra})
    assert response.status_code == 201, response.get_json()
    return response.get_json()["appointment"]


def test_requires_sign_in(client):
    assert client.get("/appointments").status_code == 401
    assert client.post("/appointments", json=NEW).status_code == 401


def test_create_and_list_uses_token_identity(as_client, as_barber, other_client):
    appointment = _create(as_client)
    assert appointment["status"] == "pending" and appointment["id"]
    assert appointment["clientId"] == "client_1"  # from the token, not the body
    assert appointment["clientName"] == "Zoe"  # display name may be given per booking
    barber_view = as_barber.get("/appointments?type=barber").get_json()["appointments"]
    assert [a["id"] for a in barber_view] == ["apt_seed_1", appointment["id"]]
    client_view = as_client.get("/appointments?type=client").get_json()["appointments"]
    assert [a["id"] for a in client_view] == ["apt_seed_1", appointment["id"]]
    # user_id in the query string is ignored: another client never sees these
    assert other_client.get("/appointments?type=client&user_id=client_1").get_json() == {"appointments": []}
    # a client account cannot list barber bookings
    assert as_client.get("/appointments?type=barber").status_code == 403


def test_create_fills_barber_name_from_profile(as_client):
    appointment = _create(as_client, barberName=None)
    assert appointment["barberName"] == "Mike's Cuts"


@pytest.mark.parametrize(
    "payload,fragment",
    [
        ({"date": "2030-03-01", "time": "13:00"}, "barberId"),
        ({"barberId": "b1", "date": "March 1", "time": "13:00"}, "YYYY-MM-DD"),
        ({"barberId": "b1", "date": "2030-03-01", "time": "1pm"}, "HH:MM"),
    ],
)
def test_create_validation(as_client, payload, fragment):
    response = as_client.post("/appointments", json=payload)
    assert response.status_code == 400
    assert fragment in response.get_json()["error"]
    assert as_client.post("/appointments", data="x", content_type="text/plain").status_code == 400


def test_update_status_barber_only(as_client, as_barber):
    appointment = _create(as_client)
    assert as_client.put(f"/appointments/{appointment['id']}/status", json={"status": "completed"}).status_code == 403
    data = as_barber.put(f"/appointments/{appointment['id']}/status", json={"status": "completed"}).get_json()
    assert data["success"] is True and data["appointment"]["status"] == "completed"
    assert data["appointment"]["statusUpdatedAt"]
    assert as_barber.put(f"/appointments/{appointment['id']}/status", json={"status": "bogus"}).status_code == 400


def test_accept_only_by_owning_barber(client, as_client, as_barber):
    appointment = _create(as_client)
    assert client.post(f"/appointments/{appointment['id']}/accept").status_code == 401
    assert as_client.post(f"/appointments/{appointment['id']}/accept").status_code == 403
    other_barber = __import__("tests.conftest", fromlist=["login"]).login(client, "other-barber@lineup.dev", role="barber")
    assert other_barber.post(f"/appointments/{appointment['id']}/accept").status_code == 403
    data = as_barber.post(f"/appointments/{appointment['id']}/accept").get_json()
    assert data["success"] is True and data["appointment"]["status"] == "confirmed"


def test_reject(as_client, as_barber):
    appointment = _create(as_client)
    data = as_barber.post(f"/appointments/{appointment['id']}/reject", json={"reason": "Fully booked"}).get_json()
    assert data["appointment"]["status"] == "rejected"
    assert data["appointment"]["rejectionReason"] == "Fully booked"
    data = as_barber.post(f"/appointments/{_create(as_client, time='14:00')['id']}/reject").get_json()
    assert data["appointment"]["rejectionReason"] == "No reason provided"


def test_reschedule_by_barber_and_client(as_client, as_barber, other_client):
    appointment = _create(as_client)
    data = as_barber.post(f"/appointments/{appointment['id']}/reschedule", json={"date": "2030-03-02", "time": "15:30"}).get_json()
    updated = data["appointment"]
    assert updated["status"] == "rescheduled" and updated["date"] == "2030-03-02" and updated["time"] == "15:30"
    assert updated["rescheduleHistory"][0]["oldDate"] == "2030-03-01"
    assert updated["rescheduleHistory"][0]["reason"] == "Rescheduled by barber" and updated["rescheduleHistory"][0]["by"] == "barber"
    # the client who booked may reschedule too; a stranger may not
    data = as_client.post(f"/appointments/{appointment['id']}/reschedule", json={"date": "2030-03-03", "time": "10:00"}).get_json()
    assert data["appointment"]["rescheduleHistory"][1]["by"] == "client"
    assert other_client.post(f"/appointments/{appointment['id']}/reschedule", json={"date": "2030-03-04", "time": "10:00"}).status_code == 403
    response = as_barber.post(f"/appointments/{appointment['id']}/reschedule", json={"date": "2030-03-02"})
    assert response.status_code == 400 and response.get_json()["error"] == "Date and time required"


def test_cancel_by_client_or_barber(as_client, as_barber, other_client):
    appointment = _create(as_client)
    assert other_client.post(f"/appointments/{appointment['id']}/cancel").status_code == 403
    data = as_client.post(f"/appointments/{appointment['id']}/cancel", json={"reason": "Sick"}).get_json()
    assert data["appointment"]["status"] == "cancelled" and data["appointment"]["cancellationReason"] == "Sick"
    assert data["appointment"]["cancelledBy"] == "client"
    second = _create(as_client, time="16:00")
    data = as_barber.post(f"/appointments/{second['id']}/cancel").get_json()
    assert data["appointment"]["cancellationReason"] == "Cancelled by barber"


def test_notes_barber_only(as_client, as_barber):
    appointment = _create(as_client)
    assert as_client.post(f"/appointments/{appointment['id']}/notes", json={"note": "x"}).status_code == 403
    data = as_barber.post(f"/appointments/{appointment['id']}/notes", json={"note": "Bring reference photo", "type": "general"}).get_json()
    assert data["success"] is True
    assert data["appointment"]["barberNotes"][0]["note"] == "Bring reference photo"
    data = as_barber.put(f"/appointments/{appointment['id']}/notes", json={"note": "Second"}).get_json()
    assert len(data["appointment"]["barberNotes"]) == 2
    assert as_barber.post(f"/appointments/{appointment['id']}/notes", json={}).status_code == 400


@pytest.mark.parametrize("action", ["accept", "reject", "cancel", "notes"])
def test_actions_404_for_unknown_appointment(as_barber, action):
    response = as_barber.post(f"/appointments/missing/{action}", json={"note": "x"})
    assert response.status_code == 404
    assert response.get_json()["error"] == "Appointment not found"


def test_create_rejects_past_date(as_client):
    from datetime import datetime, timedelta, timezone

    two_days_ago = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
    response = as_client.post("/appointments", json={**NEW, "date": two_days_ago})
    assert response.status_code == 400
    assert "passed" in response.get_json()["error"]
    # Yesterday (UTC) is still accepted so clients behind UTC can book "today".
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    assert as_client.post("/appointments", json={**NEW, "date": yesterday}).status_code == 201


def test_create_rejects_double_booking(as_client, other_client):
    first = _create(as_client)
    clash = other_client.post("/appointments", json=NEW)
    assert clash.status_code == 409
    assert "no longer available" in clash.get_json()["error"]
    # A different time, barber, or a cancelled original frees the slot.
    assert as_client.post("/appointments", json={**NEW, "time": "14:00"}).status_code == 201
    assert as_client.post("/appointments", json={**NEW, "barberId": "b2"}).status_code == 201
    as_client.post(f"/appointments/{first['id']}/cancel", json={"reason": "x"})
    assert other_client.post("/appointments", json=NEW).status_code == 201


def test_reschedule_rejects_taken_slot_and_past_date(as_client, as_barber, other_client):
    first = _create(as_client)
    second = _create(other_client, time="15:00")
    clash = as_barber.post(f"/appointments/{second['id']}/reschedule", json={"date": "2030-03-01", "time": "13:00"})
    assert clash.status_code == 409
    # Rescheduling onto its own current slot is not a clash.
    assert as_barber.post(f"/appointments/{first['id']}/reschedule", json={"date": "2030-03-01", "time": "13:00"}).status_code == 200
    past = as_barber.post(f"/appointments/{first['id']}/reschedule", json={"date": "2020-01-01", "time": "13:00"})
    assert past.status_code == 400


def test_barber_list_needs_onboarding_before_role(client):
    from tests.conftest import login

    fresh = login(client, "no-role@example.com")
    response = fresh.get("/appointments?type=barber")
    assert response.status_code == 403
    assert response.get_json()["code"] == "onboarding_required"

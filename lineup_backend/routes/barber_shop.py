"""Barber shop management: profile, review posting, availability, services,
clients. Registered only when ``LINEUP_BARBER_SIDE`` is on.

Public reads: profile, availability, slots, services. Writes derive the
barber id from the token: the URL id must match. Client list, history and
notes are Barber Pro features.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import Blueprint, g, jsonify, request

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import (
    clean_text,
    get_json_body,
    is_valid_date,
    json_response,
    new_id,
    now_iso,
    to_int,
    to_number,
    today_str,
)
from lineup_backend.middleware.auth import assert_owner, require_auth, require_pro, require_role
from lineup_backend.middleware.error_handler import ApiError
from lineup_backend.services.availability import (
    DEFAULT_SERVICES,
    default_availability,
    generate_slots,
    validate_working_hours,
)

bp = Blueprint("barber_shop", __name__)

ACTIVE_STATUSES_EXCLUDED = {"cancelled", "rejected"}


def _own_barber(barber_id: str) -> Dict[str, Any]:
    """The signed-in barber, who must be ``barber_id``."""
    return assert_owner(barber_id, "You can only manage your own shop")


def _profile_or_none(barber_id: str) -> Optional[Dict[str, Any]]:
    return services().store.barber_profiles.get(barber_id)


def _public_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    return {key: profile.get(key) for key in ("id", "name", "phone", "address", "bio", "createdAt", "updatedAt")}


# -- profile -----------------------------------------------------------------


@bp.route("/barbers/<barber_id>/profile", methods=["GET", "PUT"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["PUT"])
def profile(barber_id: str):
    collection = services().store.barber_profiles
    if request.method == "GET":
        existing = collection.get(barber_id)
        if not existing:
            raise ApiError("Barber not found", 404)
        return jsonify({"profile": _public_profile(existing)})

    require_role("barber")(lambda: None)()
    _own_barber(barber_id)
    data = get_json_body()
    existing = collection.get(barber_id) or {"ownerUid": barber_id, "createdAt": now_iso()}
    if "name" in data and not clean_text(data.get("name")):
        raise ApiError("name is required", 400)
    name = clean_text(data.get("name"), default=existing.get("name", ""), max_length=120)
    if not name:
        raise ApiError("name is required", 400)
    saved = collection.upsert(
        barber_id,
        {
            **existing,
            "ownerUid": barber_id,
            "name": name,
            "phone": clean_text(data.get("phone"), default=existing.get("phone", ""), max_length=40),
            "address": clean_text(data.get("address"), default=existing.get("address", ""), max_length=200),
            "bio": clean_text(data.get("bio"), default=existing.get("bio", ""), max_length=500),
            "updatedAt": now_iso(),
        },
    )
    return jsonify({"success": True, "profile": _public_profile(saved)})


# -- reviews (posting; reading is public in routes/barbers.py) ---------------


@bp.post("/barbers/<barber_id>/reviews")
@limiter.limit(rate("write"))
def post_review(barber_id: str):
    svc = services()
    user = require_auth(lambda: g.user)()
    data = get_json_body()
    rating = to_int(data.get("rating", 5), default=-1)
    if rating < 1 or rating > 5:
        raise ApiError("rating must be an integer from 1 to 5", 400)
    review = svc.store.barber_reviews.create(
        {
            "barberId": barber_id,
            "username": clean_text(user.get("name"), default="anonymous", max_length=80),
            "uid": user["uid"],
            "rating": rating,
            "text": clean_text(data.get("text"), max_length=2000),
            "date": today_str(),
            "timestamp": now_iso(),
        }
    )
    return json_response({"success": True, "review": review}, 201)


# -- availability ------------------------------------------------------------


def _availability_for(barber_id: str) -> Dict[str, Any]:
    return services().store.barber_availability.get(barber_id) or default_availability(barber_id)


@bp.route("/barbers/<barber_id>/availability", methods=["GET", "PUT"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["PUT"])
def availability(barber_id: str):
    if request.method == "GET":
        return jsonify({"availability": _availability_for(barber_id)})

    require_role("barber")(lambda: None)()
    _own_barber(barber_id)
    data = get_json_body()
    working_hours = data.get("workingHours") or default_availability(barber_id)["workingHours"]
    error = validate_working_hours(working_hours)
    if error:
        raise ApiError(error, 400)
    record = {
        "barberId": barber_id,
        "workingHours": working_hours,
        "breakTimes": data.get("breakTimes") if isinstance(data.get("breakTimes"), list) else [],
        "blockedDates": [d for d in data.get("blockedDates", []) if is_valid_date(d)] if isinstance(data.get("blockedDates"), list) else [],
        "serviceDuration": to_int(data.get("serviceDuration"), 30, minimum=5),
        "bufferTime": to_int(data.get("bufferTime"), 15, minimum=0),
        "timezone": clean_text(data.get("timezone"), default="America/New_York", max_length=64),
        "updatedAt": now_iso(),
    }
    saved = services().store.barber_availability.upsert(barber_id, record)
    return jsonify({"success": True, "availability": saved})


@bp.get("/barbers/<barber_id>/available-slots")
@limiter.limit(rate("read"))
def available_slots(barber_id: str):
    date = request.args.get("date", "").strip()
    if not date:
        raise ApiError("Date parameter required", 400)
    if not is_valid_date(date):
        raise ApiError("date must be YYYY-MM-DD", 400)
    svc = services()
    booked = [
        apt.get("time")
        for apt in svc.store.appointments.list(barberId=barber_id)
        if apt.get("date") == date and apt.get("status") not in ACTIVE_STATUSES_EXCLUDED
    ]
    slots, day_hours = generate_slots(_availability_for(barber_id), date, booked)
    return jsonify({"slots": slots, "date": date, "workingHours": day_hours})


# -- services & pricing ------------------------------------------------------


def _service_payload(barber_id: str, data: Dict[str, Any], existing: Dict[str, Any] | None = None) -> Dict[str, Any]:
    base = dict(existing or {})
    base.update(
        {
            "barberId": barber_id,
            "name": clean_text(data.get("name"), default=base.get("name", ""), max_length=120),
            "price": to_number(data.get("price"), default=to_number(base.get("price"), 0)),
            "duration": to_int(data.get("duration"), default=int(base.get("duration", 30) or 30), minimum=5),
            "category": clean_text(data.get("category"), default=base.get("category", "General"), max_length=60),
            "description": clean_text(data.get("description"), default=base.get("description", ""), max_length=500),
        }
    )
    return base


def _unsaved_default_services(barber_id: str) -> List[Dict[str, Any]]:
    """Typical rates for shops that have not registered (Google places, sample data). Never persisted."""
    return [
        {**service, "id": f"default-{index}", "barberId": barber_id, "default": True}
        for index, service in enumerate(DEFAULT_SERVICES, start=1)
    ]


@bp.route("/barbers/<barber_id>/services", methods=["GET", "POST", "PUT", "DELETE"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["POST", "PUT", "DELETE"])
def barber_services(barber_id: str):
    collection = services().store.barber_services

    if request.method == "GET":
        items = collection.list(barberId=barber_id)
        registered = _profile_or_none(barber_id) is not None
        if not items and not registered:
            return jsonify({"services": _unsaved_default_services(barber_id), "registered": False})
        items.sort(key=lambda s: s.get("createdAt", ""))
        return jsonify({"services": items, "registered": registered})

    require_role("barber")(lambda: None)()
    _own_barber(barber_id)

    if request.method == "POST":
        data = get_json_body()
        if not clean_text(data.get("name")):
            raise ApiError("Service name is required", 400)
        service = collection.create({**_service_payload(barber_id, data), "createdAt": now_iso()})
        return json_response({"success": True, "service": service}, 201)

    service_id = clean_text(request.args.get("service_id") or (request.get_json(silent=True) or {}).get("id"))
    if not service_id:
        raise ApiError("service_id required", 400)
    existing = collection.get(service_id)
    if not existing or existing.get("barberId") != barber_id:
        raise ApiError("Service not found", 404)

    if request.method == "PUT":
        data = get_json_body()
        updated = collection.update(service_id, {**_service_payload(barber_id, data, existing), "updatedAt": now_iso(), "default": False})
        return jsonify({"success": True, "service": updated})

    collection.delete(service_id)
    return jsonify({"success": True})


# -- clients (Barber Pro) ----------------------------------------------------


@bp.get("/barbers/<barber_id>/clients")
@limiter.limit(rate("read"))
@require_role("barber")
def clients(barber_id: str):
    _own_barber(barber_id)
    require_pro("clients")
    grouped: Dict[str, Dict[str, Any]] = {}
    for apt in services().store.appointments.list(barberId=barber_id):
        client_id = apt.get("clientId")
        if not client_id:
            continue
        entry = grouped.setdefault(
            client_id,
            {"clientId": client_id, "clientName": apt.get("clientName", "Unknown"), "totalVisits": 0, "lastVisit": None, "totalSpent": 0, "appointments": []},
        )
        entry["totalVisits"] += 1
        entry["appointments"].append(apt)
        entry["totalSpent"] += to_number(apt.get("price"), 0)

    result: List[Dict[str, Any]] = list(grouped.values())
    for entry in result:
        entry["appointments"].sort(key=lambda a: a.get("timestamp", ""), reverse=True)
        entry["lastVisit"] = entry["appointments"][0].get("date")
    result.sort(key=lambda c: c.get("lastVisit") or "", reverse=True)
    return jsonify({"clients": result})


@bp.get("/barbers/<barber_id>/clients/<client_id>/history")
@limiter.limit(rate("read"))
@require_role("barber")
def client_history(barber_id: str, client_id: str):
    _own_barber(barber_id)
    require_pro("client_history")
    items = [a for a in services().store.appointments.list(barberId=barber_id) if a.get("clientId") == client_id]
    items.sort(key=lambda a: f"{a.get('date', '')} {a.get('time', '')}", reverse=True)
    return jsonify({"clientId": client_id, "appointments": items, "totalVisits": len(items)})


@bp.route("/barbers/<barber_id>/clients/<client_id>/notes", methods=["GET", "POST", "PUT"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["POST", "PUT"])
@require_role("barber")
def client_notes(barber_id: str, client_id: str):
    _own_barber(barber_id)
    require_pro("client_notes")
    collection = services().store.client_notes
    doc_id = f"{barber_id}_{client_id}"
    doc = collection.get(doc_id) or {"barberId": barber_id, "clientId": client_id, "notes": []}
    notes: List[Dict[str, Any]] = list(doc.get("notes", []))

    if request.method == "GET":
        return jsonify({"notes": notes})

    data = get_json_body()
    text = clean_text(data.get("note"), max_length=2000)
    if not text:
        raise ApiError("note is required", 400)
    note_type = clean_text(data.get("type"), default="general", max_length=40)

    if request.method == "PUT":
        note_id = clean_text(data.get("id"))
        target = next((n for n in notes if n.get("id") == note_id), None)
        if not target:
            raise ApiError("Note not found", 404)
        target.update({"note": text, "type": note_type, "updatedAt": now_iso()})
        collection.upsert(doc_id, {"barberId": barber_id, "clientId": client_id, "notes": notes})
        return jsonify({"success": True, "note": target})

    note = {"id": new_id(), "note": text, "type": note_type, "createdAt": now_iso()}
    notes.append(note)
    collection.upsert(doc_id, {"barberId": barber_id, "clientId": client_id, "notes": notes})
    return json_response({"success": True, "note": note}, 201)

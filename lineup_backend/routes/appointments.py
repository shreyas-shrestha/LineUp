"""Bookings: create/list plus actions (accept, reject, reschedule, cancel, notes).

Identity comes from the token: a booking's ``clientId`` is the caller's uid,
``type=barber`` lists the caller's own shop. Barber-only actions check that
the appointment belongs to the caller; clients may reschedule or cancel their
own bookings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from flask import Blueprint, g, jsonify, request

from lineup_backend.context import services
from lineup_backend.extensions import limiter, rate
from lineup_backend.http import clean_text, get_json_body, is_valid_date, is_valid_time, json_response, now_iso
from lineup_backend.middleware.auth import require_auth
from lineup_backend.middleware.error_handler import ApiError

bp = Blueprint("appointments", __name__)

STATUSES = {"pending", "confirmed", "rejected", "rescheduled", "cancelled", "completed"}
CLOSED_STATUSES = {"cancelled", "rejected"}


def _reject_past_date(date: str) -> None:
    """Reject dates before yesterday (UTC), which is safe for every client time zone."""
    earliest = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    if date < earliest:
        raise ApiError("That date has passed. Pick today or a later date.", 400)


def _reject_double_booking(barber_id: str, date: str, time: str, ignore_id: Optional[str] = None) -> None:
    for other in services().store.appointments.list(barberId=barber_id, date=date, time=time):
        if other.get("id") != ignore_id and other.get("status") not in CLOSED_STATUSES:
            raise ApiError("That time is no longer available. Pick another slot.", 409)


def _appointment_or_404(appointment_id: str) -> Dict[str, Any]:
    appointment = services().store.appointments.get(appointment_id)
    if not appointment:
        raise ApiError("Appointment not found", 404)
    return appointment


def _actor_role(appointment: Dict[str, Any]) -> str:
    """'barber' when the caller owns the shop, 'client' when they made the booking."""
    uid = g.user["uid"]
    if appointment.get("barberId") == uid and g.user.get("role") == "barber":
        return "barber"
    if appointment.get("clientId") == uid:
        return "client"
    raise ApiError("This booking is not yours", 403, code="forbidden")


def _load(appointment_id: str, allow_client: bool = False) -> Dict[str, Any]:
    appointment = _appointment_or_404(appointment_id)
    role = _actor_role(appointment)
    if role == "client" and not allow_client:
        raise ApiError("Only the barber can do that", 403, code="forbidden")
    appointment["_actor"] = role
    return appointment


def _apply(appointment_id: str, patch: Dict[str, Any]):
    patch.setdefault("statusUpdatedAt", now_iso())
    updated = services().store.appointments.update(appointment_id, patch)
    return jsonify({"success": True, "appointment": updated})


@bp.route("/appointments", methods=["GET", "POST"])
@limiter.limit(rate("read"), methods=["GET"])
@limiter.limit(rate("write"), methods=["POST"])
@require_auth
def appointments():
    collection = services().store.appointments
    user = g.user
    if request.method == "GET":
        user_type = request.args.get("type", "client")
        if user_type == "barber":
            if not user.get("role"):
                raise ApiError("Finish onboarding to continue", 403, code="onboarding_required")
            if user.get("role") != "barber":
                raise ApiError("Barber bookings are only available to barber accounts", 403, code="forbidden")
            items = collection.list(barberId=user["uid"])
        else:
            items = collection.list(clientId=user["uid"])
        items.sort(key=lambda a: f"{a.get('date', '')} {a.get('time', '')}")
        return jsonify({"appointments": items})

    data = get_json_body()
    barber_id = clean_text(data.get("barberId"), max_length=120)
    date, time = data.get("date"), data.get("time")
    if not barber_id or not date or not time:
        raise ApiError("barberId, date and time are required", 400)
    if not is_valid_date(date):
        raise ApiError("date must be YYYY-MM-DD", 400)
    if not is_valid_time(time):
        raise ApiError("time must be HH:MM", 400)
    _reject_past_date(date)
    _reject_double_booking(barber_id, date, time)

    barber_profile = services().store.barber_profiles.get(barber_id) or {}
    appointment = collection.create(
        {
            "clientName": clean_text(data.get("clientName"), default=user.get("name") or "Client", max_length=120),
            "clientId": user["uid"],
            "barberName": clean_text(data.get("barberName"), default=barber_profile.get("name", "Unknown Barber"), max_length=160),
            "barberId": barber_id,
            "date": date,
            "time": time,
            "service": clean_text(data.get("service"), max_length=120),
            "price": clean_text(data.get("price"), default="$0", max_length=20),
            "status": "pending",
            "notes": clean_text(data.get("notes"), max_length=1000),
            "timestamp": now_iso(),
        }
    )
    return json_response({"success": True, "appointment": appointment}, 201)


@bp.put("/appointments/<appointment_id>/status")
@limiter.limit(rate("write"))
@require_auth
def update_status(appointment_id: str):
    data = get_json_body()
    status = clean_text(data.get("status")).lower()
    if status not in STATUSES:
        raise ApiError(f"status must be one of: {', '.join(sorted(STATUSES))}", 400)
    _load(appointment_id)
    return _apply(appointment_id, {"status": status})


@bp.post("/appointments/<appointment_id>/accept")
@limiter.limit(rate("write"))
@require_auth
def accept(appointment_id: str):
    _load(appointment_id)
    return _apply(appointment_id, {"status": "confirmed"})


@bp.post("/appointments/<appointment_id>/reject")
@limiter.limit(rate("write"))
@require_auth
def reject(appointment_id: str):
    _load(appointment_id)
    data = get_json_body(required=False)
    reason = clean_text(data.get("reason"), default="No reason provided", max_length=500)
    return _apply(appointment_id, {"status": "rejected", "rejectionReason": reason})


@bp.post("/appointments/<appointment_id>/reschedule")
@limiter.limit(rate("write"))
@require_auth
def reschedule(appointment_id: str):
    data = get_json_body()
    new_date, new_time = data.get("date"), data.get("time")
    if not new_date or not new_time:
        raise ApiError("Date and time required", 400)
    if not is_valid_date(new_date) or not is_valid_time(new_time):
        raise ApiError("date must be YYYY-MM-DD and time must be HH:MM", 400)
    appointment = _load(appointment_id, allow_client=True)
    _reject_past_date(new_date)
    _reject_double_booking(appointment.get("barberId", ""), new_date, new_time, ignore_id=appointment_id)
    history = list(appointment.get("rescheduleHistory", []))
    history.append(
        {
            "oldDate": appointment.get("date"),
            "oldTime": appointment.get("time"),
            "newDate": new_date,
            "newTime": new_time,
            "reason": clean_text(data.get("reason"), default=f"Rescheduled by {appointment['_actor']}", max_length=500),
            "by": appointment["_actor"],
            "rescheduledAt": now_iso(),
        }
    )
    return _apply(appointment_id, {"date": new_date, "time": new_time, "status": "rescheduled", "rescheduleHistory": history})


@bp.post("/appointments/<appointment_id>/cancel")
@limiter.limit(rate("write"))
@require_auth
def cancel(appointment_id: str):
    appointment = _load(appointment_id, allow_client=True)
    data = get_json_body(required=False)
    reason = clean_text(data.get("reason"), default=f"Cancelled by {appointment['_actor']}", max_length=500)
    return _apply(appointment_id, {"status": "cancelled", "cancellationReason": reason, "cancelledBy": appointment["_actor"]})


@bp.route("/appointments/<appointment_id>/notes", methods=["POST", "PUT"])
@limiter.limit(rate("write"))
@require_auth
def notes(appointment_id: str):
    data = get_json_body()
    text = clean_text(data.get("note"), max_length=2000)
    if not text:
        raise ApiError("note is required", 400)
    appointment = _load(appointment_id)
    barber_notes = list(appointment.get("barberNotes", []))
    barber_notes.append({"note": text, "type": clean_text(data.get("type"), default="general", max_length=40), "createdAt": now_iso()})
    updated = services().store.appointments.update(appointment_id, {"barberNotes": barber_notes})
    return jsonify({"success": True, "appointment": updated})

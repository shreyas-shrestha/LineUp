"""Working hours defaults, default services and time-slot generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DEFAULT_WORKING_HOURS: Dict[str, Dict[str, Any]] = {
    "monday": {"enabled": True, "start": "09:00", "end": "18:00"},
    "tuesday": {"enabled": True, "start": "09:00", "end": "18:00"},
    "wednesday": {"enabled": True, "start": "09:00", "end": "18:00"},
    "thursday": {"enabled": True, "start": "09:00", "end": "18:00"},
    "friday": {"enabled": True, "start": "09:00", "end": "18:00"},
    "saturday": {"enabled": True, "start": "09:00", "end": "17:00"},
    "sunday": {"enabled": False, "start": "09:00", "end": "17:00"},
}

DEFAULT_SERVICES: List[Dict[str, Any]] = [
    {"name": "Haircut", "price": 30, "duration": 30, "category": "Hair", "description": ""},
    {"name": "Beard Trim", "price": 15, "duration": 15, "category": "Beard", "description": ""},
    {"name": "Haircut + Beard", "price": 40, "duration": 45, "category": "Package", "description": ""},
]


def default_availability(barber_id: str) -> Dict[str, Any]:
    return {
        "barberId": barber_id,
        "workingHours": {day: dict(hours) for day, hours in DEFAULT_WORKING_HOURS.items()},
        "breakTimes": [],
        "blockedDates": [],
        "serviceDuration": 30,
        "bufferTime": 15,
        "timezone": "America/New_York",
    }


def _to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def validate_working_hours(hours: Any) -> Optional[str]:
    """Return an error message or None when the structure is valid."""
    if not isinstance(hours, dict):
        return "workingHours must be an object keyed by weekday"
    from lineup_backend.http import is_valid_time

    for day, spec in hours.items():
        if day not in DAYS:
            return f"Unknown day: {day}"
        if not isinstance(spec, dict):
            return f"{day} must be an object with enabled/start/end"
        if not is_valid_time(spec.get("start", "09:00")) or not is_valid_time(spec.get("end", "18:00")):
            return f"{day} start/end must be HH:MM"
        # A closed day keeps whatever times were last in the form; only an open
        # day has to make sense, and only an open day generates slots.
        if not spec.get("enabled"):
            continue
        if _to_minutes(spec.get("start", "09:00")) >= _to_minutes(spec.get("end", "18:00")):
            return f"{day} start must be before end"
    return None


def _overlaps(start: int, end: int, other_start: int, other_end: int) -> bool:
    return start < other_end and other_start < end


def generate_slots(availability: Dict[str, Any], date_str: str, booked_times: Iterable[str]) -> Tuple[List[str], Dict[str, Any]]:
    """Return (slots as HH:MM, the day's working-hours spec)."""
    day_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A").lower()
    day_hours = availability.get("workingHours", {}).get(day_name) or {"enabled": False}
    if not day_hours.get("enabled") or date_str in (availability.get("blockedDates") or []):
        return [], day_hours

    duration = max(5, int(availability.get("serviceDuration") or 30))
    buffer = max(0, int(availability.get("bufferTime") or 0))
    start = _to_minutes(day_hours.get("start", "09:00"))
    end = _to_minutes(day_hours.get("end", "18:00"))

    blocked: List[Tuple[int, int]] = []
    for brk in availability.get("breakTimes") or []:
        try:
            blocked.append((_to_minutes(brk["start"]), _to_minutes(brk["end"])))
        except (KeyError, TypeError, ValueError):
            continue
    for booked in booked_times:
        try:
            booked_start = _to_minutes(booked)
        except (AttributeError, ValueError):
            continue
        blocked.append((booked_start, booked_start + duration))

    slots: List[str] = []
    cursor = start
    while cursor + duration <= end:
        if not any(_overlaps(cursor, cursor + duration, b_start, b_end) for b_start, b_end in blocked):
            slots.append(_to_hhmm(cursor))
        cursor += duration + buffer
    return slots, day_hours

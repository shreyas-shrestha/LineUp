"""Validation schemas for appointment-related requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import (
    BaseSchema,
    ValidationError,
    sanitize_string,
    validate_date,
    validate_length,
    validate_required,
    validate_time,
)


@dataclass
class AppointmentCreate(BaseSchema):
    """Schema for creating a new appointment."""

    barber_id: str
    barber_name: str
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    service: str
    price: str
    client_name: str = "Anonymous Client"
    client_id: str = "current_user"
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppointmentCreate":
        """Create and validate appointment from request data."""
        errors: Dict[str, str] = {}

        # Required fields
        barber_id = data.get("barberId", "")
        barber_name = data.get("barberName", "")
        date_str = data.get("date", "")
        time_str = data.get("time", "")
        service = data.get("service", "")
        price = data.get("price", "")

        # Validate required fields
        if not barber_id:
            errors["barberId"] = "Barber ID is required"
        if not barber_name:
            errors["barberName"] = "Barber name is required"
        if not date_str:
            errors["date"] = "Date is required"
        if not time_str:
            errors["time"] = "Time is required"
        if not service:
            errors["service"] = "Service is required"
        if not price:
            errors["price"] = "Price is required"

        # Validate formats
        if date_str:
            try:
                validate_date(date_str)
                # Check date is not in the past
                appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if appointment_date < datetime.now().date():
                    errors["date"] = "Cannot book appointments in the past"
            except ValidationError as e:
                errors.update(e.errors)

        if time_str:
            try:
                validate_time(time_str)
            except ValidationError as e:
                errors.update(e.errors)

        if errors:
            raise ValidationError(errors)

        # Optional fields with sanitization
        client_name = sanitize_string(data.get("clientName", "Anonymous Client"), 100)
        client_id = sanitize_string(data.get("clientId", "current_user"), 100)
        notes = sanitize_string(data.get("notes", ""), 500)

        return cls(
            barber_id=barber_id,
            barber_name=barber_name,
            date=date_str,
            time=time_str,
            service=service,
            price=price,
            client_name=client_name,
            client_id=client_id,
            notes=notes,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "barberId": self.barber_id,
            "barberName": self.barber_name,
            "date": self.date,
            "time": self.time,
            "service": self.service,
            "price": self.price,
            "clientName": self.client_name,
            "clientId": self.client_id,
            "notes": self.notes,
            "status": "pending",
            "timestamp": datetime.now().isoformat(),
        }


@dataclass
class AppointmentUpdate(BaseSchema):
    """Schema for updating appointment status."""

    status: str
    reason: Optional[str] = None
    new_date: Optional[str] = None
    new_time: Optional[str] = None

    VALID_STATUSES = {"pending", "confirmed", "rejected", "cancelled", "completed", "rescheduled"}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppointmentUpdate":
        """Create and validate appointment update from request data."""
        errors: Dict[str, str] = {}

        status = data.get("status", "")
        if not status:
            errors["status"] = "Status is required"
        elif status not in cls.VALID_STATUSES:
            errors["status"] = f"Invalid status. Must be one of: {', '.join(cls.VALID_STATUSES)}"

        # For reschedule, require new date and time
        if status == "rescheduled":
            new_date = data.get("date") or data.get("new_date")
            new_time = data.get("time") or data.get("new_time")
            if not new_date:
                errors["date"] = "New date is required for rescheduling"
            if not new_time:
                errors["time"] = "New time is required for rescheduling"
            
            if new_date:
                try:
                    validate_date(new_date)
                except ValidationError as e:
                    errors.update(e.errors)
            
            if new_time:
                try:
                    validate_time(new_time)
                except ValidationError as e:
                    errors.update(e.errors)

        if errors:
            raise ValidationError(errors)

        return cls(
            status=status,
            reason=sanitize_string(data.get("reason", ""), 500),
            new_date=data.get("date") or data.get("new_date"),
            new_time=data.get("time") or data.get("new_time"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage update."""
        result = {
            "status": self.status,
            "statusUpdatedAt": datetime.now().isoformat(),
        }
        if self.reason:
            if self.status == "rejected":
                result["rejectionReason"] = self.reason
            elif self.status == "cancelled":
                result["cancellationReason"] = self.reason
        if self.new_date:
            result["date"] = self.new_date
        if self.new_time:
            result["time"] = self.new_time
        return result
